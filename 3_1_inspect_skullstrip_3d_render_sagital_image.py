import os
os.environ["CUDA_VISIBLE_DEVICES"] = "1"
import pandas as pd
from datetime import datetime
import pydicom
import matplotlib.image as mpimg
import csv
import re
import nibabel as nib
import numpy as np
import cv2
import matplotlib.pyplot as plt
import torch
import torch.nn.functional as F
from sklearn.impute import KNNImputer
from sklearn.model_selection import StratifiedKFold
import nibabel as nib
import numpy as np
import plotly.graph_objects as go
from skimage import measure
import imageio

from utils.dcm2niix import list_nifti_files_no_ex

# Source of RAW DICOMs
BERN_PATH='/nasdata/Berner_Daten/Other_Side_Bilddaten' 
# Project data path
DATA_PATH='/home/bule/berner_daten_analyse/data'

GIF_PATH='/home/bule/berner_daten_analyse/data/nifti/processed/valid_patient_gifs'

PROCESSED_PATH=os.path.join(DATA_PATH, 'nifti_third_try','processed')




columns = ["Patient_ID", "dwi_defaced_raw", "anatomic_defaced_raw", "dwi_skull_normalized", "anatomic_skull_normalized",
           "anatomic_defacing_mask", "anatomic_bet_mask", "dwi_defaced_normalized", "anatomic_defaced_normalized",
           "dwi_skull_raw", "anatomic_skull_raw", "dwi_bet_raw", "anatomic_bet_raw",
           "dwi_bet_normalized", "anatomic_bet_normalized"]

only_2_df=pd.read_csv(os.path.join(DATA_PATH, 'only2_third_try_df.csv'))
dwi_df=only_2_df[only_2_df['Modality']=='dwi'][['Patient_ID','Date']]

patient_dict = {}
for file_path in list_nifti_files_no_ex(PROCESSED_PATH):
    parts = file_path.split("/")
    try:
        patient_id = parts[7]  # Extract patient ID from the path
    except IndexError:
        continue
    # If patient ID is not in ict, initialize entry
    if patient_id not in patient_dict:
        patient_dict[patient_id] = {"Patient_ID": patient_id}
    # Determine corresponding column
    for col in columns[1:]:  # Skip "Patient_ID
        if col in file_path:
            patient_dict[patient_id][col] = file_path

all_processed_nifti = pd.DataFrame.from_dict(patient_dict, orient="index", columns=columns)
all_processed_nifti["Patient_ID"] = all_processed_nifti["Patient_ID"].apply(lambda x: int(x))
all_processed_nifti.sort_values('Patient_ID', inplace=True)
all_processed_nifti=all_processed_nifti.merge(dwi_df, on='Patient_ID', how='inner')
all_processed_nifti.rename(columns={'Date': 'Date_dwi'}, inplace=True)


# Sprite image
# selection based on sprite image by Pascal: 
sprite_selection_pascal= [3732118,8012130,11014350,11257776,11820560,12602795,12851493,12908444,12989339,13140710,13208390,14190753]
len(sprite_selection_pascal)

# TODO Selection based on selectin tool 
all_processed_nifti_filtered=all_processed_nifti[~all_processed_nifti['Patient_ID'].isin(sprite_selection_pascal)]
all_processed_nifti_filtered.head()





for row in all_processed_nifti_filtered.iterrows():
    nifti_file=row[1]['dwi_bet_normalized']
    gif_path=os.path.join(GIF_PATH, f"{row[1]['Patient_ID']}_3d_rotation.gif")
    
    if not os.path.exists(gif_path):
        # # Load NIfTI file
        # nifti_file = "/home/bule/berner_daten_analyse/data/nifti_third_try/processed/76813/norm_bet_dir/dwi_bet_normalized.nii.gz"
        img = nib.load(nifti_file)
        data = img.get_fdata()

        # Compute 3D mesh
        verts, faces, _, _ = measure.marching_cubes(data, level=np.percentile(data, 75))

        # Create a Plotly 3D mesh
        fig = go.Figure(
            data=[
                go.Mesh3d(
                    x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
                    i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
                    opacity=1.0,  # Transparency
                    color='gray'
                )
            ]
        )

        # Remove axes and set an initial zoomed-out view
        zoom_factor = 2  # Increase zoom-out effect
        fig.update_layout(
            scene=dict(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                zaxis=dict(visible=False),
                aspectmode="data",
                camera=dict(eye=dict(x=zoom_factor, y=zoom_factor, z=1.5))  # Default zoomed-out view
            )
        )

        # Generate images for full rotation around X, Y, and Z axes
        frames = []
        num_frames = 36  # 36 frames for smooth rotation

        # Rotation around X-axis
        for i in range(num_frames):
            angle = (360 / num_frames) * i
            fig.update_layout(scene_camera=dict(eye=dict(
                x=zoom_factor, 
                y=zoom_factor * np.cos(np.radians(angle)), 
                z=zoom_factor * np.sin(np.radians(angle))
            )))
            img_bytes = fig.to_image(format="png", scale=2)
            frames.append(imageio.imread(img_bytes))

        # Rotation around Y-axis
        for i in range(num_frames):
            angle = (360 / num_frames) * i
            fig.update_layout(scene_camera=dict(eye=dict(
                x=zoom_factor * np.cos(np.radians(angle)), 
                y=zoom_factor, 
                z=zoom_factor * np.sin(np.radians(angle))
            )))
            img_bytes = fig.to_image(format="png", scale=2)
            frames.append(imageio.imread(img_bytes))

        # Rotation around Z-axis
        for i in range(num_frames):
            angle = (360 / num_frames) * i
            fig.update_layout(scene_camera=dict(eye=dict(
                x=zoom_factor * np.cos(np.radians(angle)), 
                y=zoom_factor * np.sin(np.radians(angle)), 
                z=zoom_factor
            )))
            img_bytes = fig.to_image(format="png", scale=2)
            frames.append(imageio.imread(img_bytes))

        imageio.mimsave(gif_path, frames, duration=0.1, loop=0)  # `loop=0` makes it loop forever

        print(f"Saved GIF: {gif_path}")
