
# def run_dcm2niix(source_dir, target_dir):
#     """
#     Run dcm2niix to convert all .dcm files in source_dir into a single NIfTI file in target_dir.
#     """
#     os.makedirs(target_dir, exist_ok=True)
#     cmd = f"dcm2niix -z y -o {target_dir} {source_dir}"
#     try:
#         subprocess.run(cmd, shell=True, check=True)
#         print(f"Converted: {source_dir} -> {target_dir}")
#     except subprocess.CalledProcessError as e:
#         print(f"Error converting {source_dir}: {e}")

# def process_directories(source_dirs, target_dirs):
#     """
#     Process all source and target directory pairs to ensure one NIfTI file per source directory.
#     """
#     if len(source_dirs) != len(target_dirs):
#         print("Error: Source and target directories lists must have the same length.")
#         return

#     for source_dir, target_dir in zip(source_dirs, target_dirs):
#         if os.path.exists(source_dir):
#             run_dcm2niix(source_dir, target_dir)
#         else:
#             print(f"Source directory does not exist: {source_dir}")
            
            
import os
import subprocess
import logging

def configure_logging(log_path):
    """
    Configure the logging module to write errors to the specified log file.
    """
    logging.basicConfig(
        filename=log_path,
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def run_dcm2niix(source_dir, target_dir):
    """
    Run dcm2niix to convert all .dcm files in source_dir into a single NIfTI file in target_dir,
    ensuring lossless conversion.
    """
    os.makedirs(target_dir, exist_ok=True)
    cmd = f"dcm2niix -z y -m n -s n -x n -o {target_dir} {source_dir}"
    try:
        subprocess.run(cmd, shell=True, check=True)
        print(f"Converted: {source_dir} -> {target_dir}")
    except subprocess.CalledProcessError as e:
        error_message = f"Error converting {source_dir}: {e}"
        print(error_message)
        logging.error(error_message)

def process_directories(source_dirs, target_dirs, log_path):
    """
    Process all source and target directory pairs to ensure one NIfTI file per source directory.
    """

        
    configure_logging(log_path)

    if len(source_dirs) != len(target_dirs):
        error_message = "Error: Source and target directories lists must have the same length."
        print(error_message)
        logging.error(error_message)
        return

    for source_dir, target_dir in zip(source_dirs, target_dirs):
        if os.path.exists(source_dir):
            run_dcm2niix(source_dir, target_dir)
        else:
            error_message = f"Source directory does not exist: {source_dir}"
            print(error_message)
            logging.error(error_message)


def list_nifti_files(directory):
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return
    nifti_files = []
    for root, _, files in os.walk(directory):
        if 'processed' in root:
            continue
        for file in files:
            if file.startswith('b1000-extracted-'):
                continue
            if file.endswith(('.nii', '.nii.gz')):
                nifti_files.append(os.path.join(root, file))
    return nifti_files

def list_nifti_files_no_ex(directory):
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return
    nifti_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.nii', '.nii.gz')):
                nifti_files.append(os.path.join(root, file))
    return nifti_files