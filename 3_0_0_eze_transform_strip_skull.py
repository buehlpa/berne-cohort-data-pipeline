# %%
import json
import os
import sys
import shutil
import yaml
import logging
import datetime

from pprint import pprint
from subprocess import run, PIPE
from typing import Tuple

import nibabel as nib
import skimage
import skimage.transform

#from skull_strip.registration import register_images
from registration import register_images

# %% 
def get_file_list(folder_path:str) -> list:
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

# %%
def setup_environment(output_path:str, patient_id:str) -> None:
    setup_path = os.path.join(output_path, patient_id)
    if os.path.exists(setup_path):
        logging.debug(f"Path already exists, deleting {setup_path}")
        shutil.rmtree(setup_path)

    if not os.path.exists(setup_path):
        os.makedirs(setup_path)
        os.makedirs(os.path.join(setup_path, "tmp"))
        logging.debug(f"Created path {setup_path}")

    

def clean_up_environment():
    """Implement deletion of temp files etc."""
    pass

# %%
def preprocess_check_and_extract_b1000(valid_patients:list,
                                       patient_files:dict,
                                       SKULL_STRIPPED_PATH:str
                                       )->Tuple[list, dict]:
    logging.debug(f"Validating and correcting path to b1000 sequence.")
    logging.info(f"TODO: Move this preprocessing step to other place or expand skull-strip-paths.json")

    # We only accept scans with 4 dimensions (x, y, z, layers), we select the 4th element (index 3)
    filter_index_pos = 3

    # we only select the last layer if there are 2 exatcly 2 layers, most scans have 2 layers.
    filter_dimension_size = 2

    invalid_patients = []

    for patient_id in valid_patients:
        dwi = nib.load(patient_files.get(patient_id).get("dwi"))
        dwi_shape = dwi.get_fdata().shape
        
        if not len(dwi_shape) == filter_index_pos + 1:
            invalid_patients.append(patient_id)
            logging.warning(f"DWI of patient {patient_id} does not contain {filter_index_pos + 1} dimensions but has shape {dwi_shape}. Skipping this one.")
            continue

        if not dwi_shape[filter_index_pos] == filter_dimension_size:
            invalid_patients.append(patient_id)
            logging.debug(f"DWI of patient {patient_id} has shape {dwi_shape}. For now only considering patients with {filter_dimension_size} b-sequences.")
            continue

        # Take the last sequence and create a new nifti
        b1000_sequence = dwi.get_fdata()[:, :, :, -1]
        new_nifti = nib.Nifti1Image(b1000_sequence, dwi.affine, dwi.header)

        # save the nifti, prepend the potential b1000 sequence
        nifti_folder_path, dwi_file_name = os.path.split(patient_files.get(patient_id).get("dwi"))

        new_file_path = os.path.join(nifti_folder_path, "b1000-extracted-" + dwi_file_name)
        nib.save(new_nifti, new_file_path)
        logging.info(f"Extracted and saved b1000 sequence to {new_file_path}.")

        # change the new paths for the patients
        patient_files[patient_id]["old_dwi"] = patient_files.get(patient_id).get("dwi")
        patient_files[patient_id]["dwi"] = new_file_path

    valid_patients = [vp for vp in valid_patients if vp not in invalid_patients]

    return valid_patients, patient_files

# %%
def strip_flair_image(patient_id:str, 
                      patient_paths:dict, 
                      output_path:str,
                      gpu:bool = False,
                      save_mask:int = 1,
                      mode:str = "accurate"
                      ) -> None:
    logging.debug(f"Transforming the reference image (flair) for patient {patient_id}.")
    file_path, file_name = os.path.split(patient_paths.get("flair"))
    full_output_path = os.path.join(output_path, patient_id, file_name.replace(".nii.gz", ""))

    if gpu:
        command = f'hd-bet -i {patient_paths.get("flair")} -o {full_output_path} -s {save_mask} -mode {mode}'
        logging.debug(f"Converting flair with GPU for patient {patient_id}")
        logging.debug(command)
    else: 
        command = f'hd-bet -i {patient_paths.get("flair")} -o {full_output_path} -s {save_mask} -device cpu -mode {mode} -tta 0'
        logging.debug(f"Converting flair with CPU for patient {patient_id}")
        logging.debug(command)

    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    if result.stdout:
        logging.debug(result.stdout)
    if result.stderr:
        logging.error(result.stderr)
        
    os.rename(f"{full_output_path}.nii.gz", f"{full_output_path}_skull-stripped.nii.gz")

# %% Define first pipeline step
def step_one_strip_flair(changed_files:dict,
                         valid_patients:list,
                         SKULL_STRIPPED_PATH:str,
                         gpu:bool,
                         )->Tuple[dict, dict]:
    
    # Loop over patients and create the stripped files from flair files.
    patients_with_exceptions = []
    for patient_id in valid_patients:
        try:
            logging.info(f"Stripping patient {patient_id}.")
            files_before_transformation = get_file_list(os.path.join(SKULL_STRIPPED_PATH, patient_id))

            strip_flair_image(patient_id=patient_id, 
                            patient_paths=patient_files.get(patient_id),
                            output_path=SKULL_STRIPPED_PATH,
                            gpu=gpu
                            )
            
            # Unfortunately we don't get a return for the newly created files so we have to scan the fs for them.
            files_after_transformation = get_file_list(os.path.join(SKULL_STRIPPED_PATH, patient_id))
            new_files = list(set(files_after_transformation) - set(files_before_transformation))
            new_mask_file = [f for f in new_files if "mask.nii.gz" in f]
            new_stripped_flair = [f for f in new_files if "skull-stripped.nii.gz" in f]
            assert len(new_mask_file) == 1, f"There is not exactly one new mask file: {new_files}"
            assert len(new_stripped_flair) == 1

            # Unpack the single-item-list and add to dict
            changed_files[patient_id] = {"mask": new_mask_file[0], 
                                        "stripped-flair": new_stripped_flair[0]} 
        
            logging.debug(f"New files created: {new_files}") 
        except Exception:
            logging.exception(f"Can not transform FLAIR for patient {patient_id}.")
            patients_with_exceptions.append(patient_id)
            
    valid_patients = [vp for vp in valid_patients if vp not in patients_with_exceptions]
        
    return changed_files, valid_patients


# %% Define second pipeline step
def step_two_image_registration(changed_files:dict,
                                valid_patients:list,
                                SKULL_STRIPPED_PATH:str,
                                ELASTIX_PATH:str,
                                )->Tuple[dict, dict]:
    
    patients_with_exceptions = []
    for patient_id in valid_patients:
        try:
            patient_output_path = os.path.join(SKULL_STRIPPED_PATH, patient_id)
            path_fixed_mask = os.path.join(patient_output_path, changed_files.get(patient_id).get("mask"))
            
            logging.debug(f"Call register_images for patient {patient_id}")
            register_images(path_moving_image=patient_files.get(patient_id).get("dwi"),
                            path_fixed_image=patient_files.get(patient_id).get("flair"),
                            path_fixed_mask=path_fixed_mask,
                            output_directory=patient_output_path,
                            ELASTIX_PATH=ELASTIX_PATH)
            
            dwi_mask_path = os.path.join(patient_output_path, "dwi_reg_mask.nii.gz")
            shutil.copy(os.path.join(patient_output_path, "tmp", "reg_mask.nii.gz"), 
                        dwi_mask_path)
            changed_files[patient_id]["dwi_mask_path"] = dwi_mask_path

            logging.debug(f"Registered to {dwi_mask_path}")
        except Exception:
            logging.exception(f"Can not register mask for patient {patient_id}.")
            patients_with_exceptions.append(patient_id)
            
    valid_patients = [vp for vp in valid_patients if vp not in patients_with_exceptions]

    return changed_files, valid_patients

# %% Define third pipeline step
def step_three_strip_adc_dwi(changed_files:dict,
                            valid_patients:list,
                            patient_files:dict,
                            SKULL_STRIPPED_PATH:str,
                            ELASTIX_PATH:str) -> None:
    
    patients_with_exceptions = []
    for patient_id in valid_patients:
        try:
            patient_output_path = os.path.join(SKULL_STRIPPED_PATH, patient_id)
            patient_registerd_mask = nib.load(changed_files.get(patient_id).get("dwi_mask_path")).get_fdata()
            logging.info(f"DWI-ADC skull-stripping for patient {patient_id}")

            for mri_modality in ["dwi", "adc"]:
                volume = nib.load(os.path.join(patient_output_path, patient_files.get(patient_id).get(mri_modality)))
                volume_fdata = volume.get_fdata() 
                volume_shape = volume_fdata.shape
                patient_registerd_mask_resized = skimage.transform.resize(patient_registerd_mask, volume_shape)
                volume_data = volume_fdata * patient_registerd_mask_resized

                skull_stripped_object = nib.Nifti1Image(volume_data, volume.affine, volume.header)
                mir_modality_output_path = os.path.join(
                    patient_output_path, 
                    patient_files.get(patient_id).get(mri_modality).replace(".nii.gz", "_skull-stripped.nii.gz")
                    )
                
                nib.save(skull_stripped_object, mir_modality_output_path)
                logging.info(f"Saved stripped object to: {mir_modality_output_path}")
        except Exception:
            logging.exception(f"Can not skull strip dwi and adc for patient {patient_id}.")
            patients_with_exceptions.append(patient_id)

    return None

# %%
if __name__ == "__main__":
    # %% load config
    with open("/home/bule/skull_strip_bestehend_copy_nordin/config.yml", "r") as config:
        project_config = yaml.safe_load(config)

    RAW_DATA_PATH = project_config.get("RAW_DATA_PATH")
    NIFIT_DATA_PATH = project_config.get("NIFTI_DATA_PATH")
    PROJECT_PATH = project_config.get("PROJECT_PATH")
    SKULL_STRIPPED_PATH = project_config.get("SKULL_STRIPPED_PATH")
    ELASTIX_PATH = project_config.get("ELASTIX_PATH")

    
    """logging.basicConfig(filename=f"{PROJECT_PATH}/transform.log",
                        filemode="a",
                        level=logging.INFO, #level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s'
                        )"""
    
    log = logging.getLogger("")
    log.setLevel(logging.DEBUG)
    format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(format)

    file_handler = logging.FileHandler(f"{PROJECT_PATH}/transform-single{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S.log')}.log")
    file_handler.setFormatter(format)

    log.addHandler(console_handler)
    log.addHandler(file_handler)



    # %% load all patients to be transformed
    with open(os.path.join(PROJECT_PATH, "skull-strip-paths.json"), "r") as f: # skull-strip-paths-single-sample.json
        patient_files = json.load(f)

    # Select only patients that have all three paths
    valid_patients = []
    for patient_id in patient_files.keys():
        if not patient_files[patient_id].get("dwi"):
            logging.debug(f"Patient {patient_id} does not have a dwi path.")
            continue
        if not patient_files[patient_id].get("adc"):
            logging.debug(f"Patient {patient_id} does not have a adc path.")
            continue
        if not patient_files[patient_id].get("flair"):
            logging.debug(f"Patient {patient_id} does not have a flair path.")
            continue
        logging.debug(f"Patient {patient_id} is valid.")
        valid_patients.append(patient_id)

    #valid_patients = valid_patients[:3] # TODO: Turn off filter

    logging.info(f"Loaded a total of {len(patient_files.keys())} patients but only kept {len(valid_patients)} because of complete paths for dwi, adc, and flair.")

    # For DWI: extract and select the b1000 sequence.
    valid_patients, patient_files = preprocess_check_and_extract_b1000(valid_patients=valid_patients,
                                                                       patient_files=patient_files,
                                                                       SKULL_STRIPPED_PATH=SKULL_STRIPPED_PATH)

    logging.info(f"Extracted b1000 sequence for {len(valid_patients)}. Discarded the rest.")


    #%% Setup
    for patient_id in valid_patients:
        setup_environment(output_path=SKULL_STRIPPED_PATH, patient_id=patient_id)

    #%% 1. Skull-strip the reference image (FLAIR) with HD-BET.
    # See new files that have been created
    changed_files = dict()

    changed_files, valid_patients = step_one_strip_flair(changed_files=changed_files,
                                        valid_patients=valid_patients,
                                        SKULL_STRIPPED_PATH=SKULL_STRIPPED_PATH,
                                        gpu=True)

    # %% 2. Loop over patients and create the image registration with the DWI image and mask created by step 1
    changed_files, valid_patients = step_two_image_registration(changed_files=changed_files,
                                                valid_patients=valid_patients,
                                                SKULL_STRIPPED_PATH=SKULL_STRIPPED_PATH,
                                                ELASTIX_PATH=ELASTIX_PATH)

    # %% 3. Skull-strip adc and dwi images.
    step_three_strip_adc_dwi(changed_files=changed_files,
                            valid_patients=valid_patients,
                            patient_files=patient_files,
                            SKULL_STRIPPED_PATH=SKULL_STRIPPED_PATH,
                            ELASTIX_PATH=ELASTIX_PATH)

    clean_up_environment()


    # %%
    # run all