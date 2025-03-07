import pandas as pd
import os
import nibabel as nib
import numpy as np
import logging
from pathlib import Path
from brainles_preprocessing.modality import Modality, CenterModality
from brainles_preprocessing.normalization.percentile_normalizer import PercentileNormalizer
from brainles_preprocessing.preprocessor import Preprocessor

# Select the b1000 sequences and start skullstripping with brainles

# Paths
DATA_PATH = '/home/bule/berner_daten_analyse/data'
NII_TARGET_PATH = '/home/bule/berner_daten_analyse/data/nifti'
df = pd.read_csv(os.path.join(DATA_PATH, 'only_2_df.csv'))

# Configure logging
logging.basicConfig(
    filename=os.path.join(DATA_PATH, 'processing.log'), 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Starting B1000 extraction and skull stripping process.")

# The shape of the images should be 3
filter_index_pos = 3

dfnew = df.copy()
dfnew['sel_b1000'] = dfnew['Full_Path_Nifti']

logging.info("Extracting B1000 sequences from DWI images.")

for idx, path in df['Full_Path_Nifti'].items():
    try:
        dwi = nib.load(path)
        dwi_shape = dwi.get_fdata().shape

        if not len(dwi_shape) == filter_index_pos + 1:
            logging.warning(f"Image of patient {path} has shape {dwi_shape}, skipping.")
            continue

        b1000_sequence = dwi.get_fdata()[:, :, :, -1]
        new_nifti = nib.Nifti1Image(b1000_sequence, dwi.affine, dwi.header)
        nifti_folder_path, dwi_file_name = os.path.split(path)
        new_file_path = os.path.join(nifti_folder_path, "b1000-extracted-" + dwi_file_name)

        if os.path.exists(new_file_path):
            logging.info(f"File {new_file_path} already exists. Skipping.")
            continue

        nib.save(new_nifti, new_file_path)
        dfnew.loc[idx, 'sel_b1000'] = new_file_path
        logging.info(f"Saved B1000 sequence for {path} to {new_file_path}.")
    except Exception as e:
        logging.error(f"Error processing {path}: {e}")

# Create a new dictionary with patient IDs
logging.info("Creating dictionary of paths for skull stripping.")
dict_paths = {}
for index, row in dfnew.iterrows():
    patient_id = row['Patient_ID']
    if patient_id not in dict_paths:
        dict_paths[patient_id] = {}
    dict_paths[patient_id][row['Modality']] = row['sel_b1000']

# Skull stripping process
logging.info("Starting skull stripping process.")

for patid, mods in dict_paths.items():
    try:
        logging.info(f"Processing patient {patid}.")
        output_folder = Path(os.path.join(NII_TARGET_PATH, 'processed'))
        
        percentile_normalizer = PercentileNormalizer(
            lower_percentile=0.1,
            upper_percentile=99.9,
            lower_limit=0,
            upper_limit=1,
        )

        center = CenterModality(
            modality_name="anatomic",
            input_path=Path(mods['anatomic']),
            normalizer=percentile_normalizer,
            raw_skull_output_path=output_folder/f"{patid}/raw_skull_dir/anatomic_skull_raw.nii.gz",
            raw_bet_output_path=output_folder/f"{patid}/raw_bet_dir/anatomic_bet_raw.nii.gz",
            raw_defaced_output_path=output_folder/f"{patid}/raw_defaced_dir/anatomic_defaced_raw.nii.gz",
            normalized_skull_output_path=output_folder/f"{patid}/norm_skull_dir/anatomic_skull_normalized.nii.gz",
            normalized_bet_output_path=output_folder/f"{patid}/norm_bet_dir/anatomic_bet_normalized.nii.gz",
            normalized_defaced_output_path=output_folder/f"{patid}/norm_defaced_dir/anatomic_defaced_normalized.nii.gz",
            bet_mask_output_path=output_folder/f"{patid}/masks/anatomic_bet_mask.nii.gz",
            defacing_mask_output_path=output_folder/f"{patid}/masks/anatomic_defacing_mask.nii.gz",
        )

        moving_modalities = [
            Modality(
                modality_name="dwi",
                input_path=Path(mods['dwi']),
                normalizer=percentile_normalizer,
                raw_skull_output_path=output_folder/f"{patid}/raw_skull_dir/dwi_skull_raw.nii.gz",
                raw_bet_output_path=output_folder/f"{patid}/raw_bet_dir/dwi_bet_raw.nii.gz",
                raw_defaced_output_path=output_folder/f"{patid}/raw_defaced_dir/dwi_defaced_raw.nii.gz",
                normalized_skull_output_path=output_folder/f"{patid}/norm_skull_dir/dwi_skull_normalized.nii.gz",
                normalized_bet_output_path=output_folder/f"{patid}/norm_bet_dir/dwi_bet_normalized.nii.gz",
                normalized_defaced_output_path=output_folder/f"{patid}/norm_defaced_dir/dwi_defaced_normalized.nii.gz",
            )
        ]

        preprocessor = Preprocessor(
            center_modality=center,
            moving_modalities=moving_modalities,
        )
        preprocessor.run()
        logging.info(f"Successfully processed patient {patid}.")
    except Exception as e:
        logging.error(f"Error processing patient {patid}: {e}")

logging.info("Processing complete.")
