import pandas as pd
import os
import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from brainles_preprocessing.modality import Modality, CenterModality
from brainles_preprocessing.normalization.percentile_normalizer import (
    PercentileNormalizer,
)
from brainles_preprocessing.preprocessor import Preprocessor


####### docker cont not needed

###################### ADJSUT THE FILES HERE
ANALYSIS_PATH='/home/bule/berner_daten_analyse/data'
NII_TARGET_PATH ='/home/bule/berner_daten_analyse/data/nifti_pascal_selection_try' #'/home/bule/berner_daten_analyse/data/nifti_second_try'
df=pd.read_csv(os.path.join(ANALYSIS_PATH, 'only2_pascal_selection_df.csv'))# each patietn has 2 nfitis




# pd.set_option('display.max_columns', None)

filter_index_pos = 3

# we only select the last layer if there are 2 exatcly 2 layers, most scans have 2 layers.
filter_dimension_size = 2

new_paths = []
count=0


#### extract b1000 sequence


for path in df['Full_Path_Nifti']:
    dwi = nib.load(path)
    dwi_shape = dwi.get_fdata().shape

    if not len(dwi_shape) == filter_index_pos + 1:
        print(f"image of patient {path} does not contain {filter_index_pos + 1} dimensions but has shape {dwi_shape}. Skipping this one.")
        continue

    # if not dwi_shape[filter_index_pos] == filter_dimension_size:
    #     print(f"image of patient {path} has shape {dwi_shape}. For now only considering patients with {filter_dimension_size} b-sequences.")
    #     continue

    # Take the last sequence and create a new nifti
    b1000_sequence = dwi.get_fdata()[:, :, :, -1]
    new_nifti = nib.Nifti1Image(b1000_sequence, dwi.affine, dwi.header)

    # save the nifti, prepend the potential b1000 sequence
    nifti_folder_path, dwi_file_name = os.path.split(path)

    new_file_path = os.path.join(nifti_folder_path, "b1000-extracted-" + dwi_file_name)
    nib.save(new_nifti, new_file_path)
    
    new_paths.append(new_file_path)


########## create new dataframe with the new paths
dfnew = df.copy()
dwi=dfnew[dfnew['Modality']=='dwi']
dwi['sel_b1000'] = new_paths
t1=dfnew[dfnew['Modality']=='t1']
t1['sel_b1000']=t1['Full_Path_Nifti']
dfnew=pd.concat([dwi,t1])
dfnew.head()

dict_paths = {}
for index, row in dfnew.iterrows():
    patient_id = row['Patient_ID']
    if patient_id not in dict_paths:
        dict_paths[patient_id] = {}
    dict_paths[patient_id][row['Modality']] = row['sel_b1000']
dict_paths



################# SKULLSTRIPPING 

count= 0
for patid, mods in dict_paths.items():
    
    # if int(patid) <=11250836: ######### <---------------------------------------------------------abortion crit
    #     continue
    
    output_folder = Path(os.path.join(NII_TARGET_PATH),'test')

    # specify a normalizer
    percentile_normalizer = PercentileNormalizer(
        lower_percentile=0.1,
        upper_percentile=99.9,
        lower_limit=0,
        upper_limit=1,
    )

    # define center and moving modalities
    center = CenterModality(
        modality_name="t1",
        input_path=Path(mods['t1']),
        normalizer=percentile_normalizer,
        # specify the output paths for the raw and normalized images of each step - here only for atlas registered and brain extraction
        raw_skull_output_path=output_folder/f"{patid}/raw_skull_dir/t1_skull_raw.nii.gz",
        raw_bet_output_path=output_folder/f"{patid}/raw_bet_dir/t1_bet_raw.nii.gz",
        raw_defaced_output_path=output_folder/f"{patid}/raw_defaced_dir/t1_defaced_raw.nii.gz",
        normalized_skull_output_path=output_folder/f"{patid}/norm_skull_dir/t1_skull_normalized.nii.gz",
        normalized_bet_output_path=output_folder/f"{patid}/norm_bet_dir/t1_bet_normalized.nii.gz",
        normalized_defaced_output_path=output_folder/f"{patid}/norm_defaced_dir/t1_defaced_normalized.nii.gz",
        # specify output paths for the brain extraction and defacing masks
        bet_mask_output_path=output_folder/f"{patid}/masks/t1_bet_mask.nii.gz",
        defacing_mask_output_path=output_folder/f"{patid}/masks/t1_defacing_mask.nii.gz",
    )


    moving_modalities = [
        Modality(
            modality_name="dwi",
            input_path=Path(mods['dwi']),
            normalizer=percentile_normalizer,
            # specify the output paths for the raw and normalized images of each step - here only for atlas registered and brain extraction
            raw_skull_output_path=output_folder/f"{patid}/raw_skull_dir/dwi_skull_raw.nii.gz",
            raw_bet_output_path=output_folder/f"{patid}/raw_bet_dir/dwi_bet_raw.nii.gz",
            raw_defaced_output_path=output_folder/f"{patid}/raw_defaced_dir/dwi_defaced_raw.nii.gz",
            normalized_skull_output_path=output_folder/f"{patid}/norm_skull_dir/dwi_skull_normalized.nii.gz",
            normalized_bet_output_path=output_folder/f"{patid}/norm_bet_dir/dwi_bet_normalized.nii.gz",
            normalized_defaced_output_path=output_folder/f"{patid}/norm_defaced_dir/dwi_defaced_normalized.nii.gz",
        )
    ]

    # instantiate and run the preprocessor using defaults for registration/ brain extraction/ defacing backends
    preprocessor = Preprocessor(
        center_modality=center,
        moving_modalities=moving_modalities,
    )

    preprocessor.run()
    
    # count+=1
    # if count == 3:
    #     break