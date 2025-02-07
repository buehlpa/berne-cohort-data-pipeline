import nibabel as nib
import numpy as np
import vedo

# Load the NIfTI file
nifti_path = "/home/bule/berner_daten_analyse/data/nifti_third_try/processed/76813/norm_bet_dir/dwi_bet_normalized.nii.gz"
nifti_img = nib.load(nifti_path)

# Get the image data as a NumPy array
image_data = nifti_img.get_fdata()

# Crop to a smaller region (center 50% of the brain)
x_mid, y_mid, z_mid = np.array(image_data.shape) // 2
crop_size = 64  # Reduce this if still crashing

image_data = image_data[
    x_mid - crop_size:x_mid + crop_size,
    y_mid - crop_size:y_mid + crop_size,
    z_mid - crop_size:z_mid + crop_size,
]

# Normalize
image_data = (image_data - np.min(image_data)) / (np.max(image_data) - np.min(image_data))

# Extract isosurface
threshold = 0.3
volume = vedo.Volume(image_data)
brain_mesh = volume.isosurface(threshold)

# Show using vedo (works better in notebooks)
vedo.show(brain_mesh, axes=1, bg="black")
