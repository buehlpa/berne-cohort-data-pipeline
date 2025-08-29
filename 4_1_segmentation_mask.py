import pandas as pd
import subprocess
import os
import tempfile
import nibabel as nib
from nilearn.image import resample_to_img
import pandas as pd
import pathlib
import shutil



# for thsi file to run you need to install the docker image: 
# docker pull isleschallenge/deepisles



def ensure_3d_nifti(path, label="dwi", root_path=None):
    """
    Ensures a NIfTI is 3D. If 4D, extracts last volume and saves alongside the original in root_path.
    Returns a valid 3D path (original or new).
    """
    img = nib.load(path)
    data = img.get_fdata()
    
    if data.ndim == 4:
        print(f"{label.upper()} file {path} is 4D → extracting last volume")
        out_dir = os.path.join(root_path, "preprocessed")
        os.makedirs(out_dir, exist_ok=True)
        new_path = os.path.join(out_dir, f"{label}-b1000-3d-{os.path.basename(path)}")
        if not os.path.exists(new_path):
            b1000 = data[..., -1]  # last volume
            nib.save(nib.Nifti1Image(b1000, img.affine, img.header), new_path)
        return new_path
    return path


def ensure_same_space(adc_path, dwi_path, root_path=None):
    """
    Ensures ADC is resampled into the DWI space if shapes/affines differ.
    Saves result inside root_path/preprocessed.
    """
    adc_img = nib.load(adc_path)
    dwi_img = nib.load(dwi_path)

    if adc_img.shape != dwi_img.shape or not (adc_img.affine == dwi_img.affine).all():
        print("Resampling ADC to DWI space...")
        out_dir = os.path.join(root_path, "preprocessed")
        os.makedirs(out_dir, exist_ok=True)
        resampled_path = os.path.join(out_dir, f"adc-resampled-3d-{os.path.basename(adc_path)}")
        if not os.path.exists(resampled_path):
            adc_resampled = resample_to_img(adc_img, dwi_img, interpolation="continuous")
            nib.save(adc_resampled, resampled_path)
        return resampled_path
    return adc_path




adc_dwi_soop = pd.read_csv("/nasdata/archive/personal_project_archives/bule/berner_daten_analyse/data/merge_adc_dwi.csv")
root_path = "/home/bule/berner_daten_analyse/data/nifti"
results_root = "/home/bule/berner_daten_analyse/data/patient_results"
os.makedirs(results_root, exist_ok=True)


for idx, row in adc_dwi_soop.iterrows():
    adc_path = row["Full_Path_Nifti_adc"]
    dwi_path = row["Full_Path_Nifti_dwi"]
    patient_id = str(row.get("Patient_ID", f"patient_{idx}"))

    patient_results = os.path.join(results_root, patient_id)
    os.makedirs(patient_results, exist_ok=True)

    # expected output file
    lesion_mask = os.path.join(patient_results, "lesion_msk.nii.gz")
    if os.path.exists(lesion_mask):
        print(f"Skipping {patient_id}, results already exist.")
        continue

    adc_path_3d = ensure_3d_nifti(adc_path, "adc", root_path=root_path)
    dwi_path_3d = ensure_3d_nifti(dwi_path, "dwi", root_path=root_path)

    adc_path_3d = ensure_same_space(adc_path_3d, dwi_path_3d, root_path=root_path)

    adc_rel = os.path.relpath(adc_path_3d, root_path)
    dwi_rel = os.path.relpath(dwi_path_3d, root_path)

    print(f"Running patient {patient_id}...")
    print(f"  ADC (rel): {adc_rel}")
    print(f"  DWI (rel): {dwi_rel}")

    cmd = [
        "docker", "run", "--rm", "--gpus", "all",
        "-v", f"{root_path}:/app/data",
        "isleschallenge/deepisles",
        "--adc_file_name", adc_rel,
        "--dwi_file_name", dwi_rel
    ]
    subprocess.run(cmd)

    # --- Move results to patient folder ---
    container_results = os.path.join(root_path, "results")
    if not os.path.exists(container_results):
        print(f"No results found for {patient_id}, skipping move.")
        continue

    for f in os.listdir(container_results):
        dst = os.path.join(patient_results, f)
        if os.path.exists(dst):
            print(f"Result {dst} already exists, skipping move.")
            continue
        shutil.move(os.path.join(container_results, f), dst)

    print(f"Saved results for {patient_id} in {patient_results}")

    # --- CLEANUP ---
    # 1. Remove container result directory (now copied)
    if os.path.exists(container_results):
        shutil.rmtree(container_results, ignore_errors=True)

    # 2. Optionally remove preprocessed files for this patient to save space
    preproc_dir = os.path.join(root_path, "preprocessed")
    if os.path.exists(preproc_dir):
        for f in os.listdir(preproc_dir):
            if patient_id in f or f.startswith("adc-") or f.startswith("dwi-"):
                try:
                    os.remove(os.path.join(preproc_dir, f))
                except Exception as e:
                    print(f"Could not remove {f}: {e}")

print("Processing complete. Temporary files cleaned.")
