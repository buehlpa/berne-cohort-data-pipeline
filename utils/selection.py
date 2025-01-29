import csv
import pydicom
import re
import pandas as pd

def collect_all_file_paths(root_directory):
    dcm_files = []
    other_files = []
    for dirpath, _, filenames in os.walk(root_directory):
        for file in filenames:
            full_path = os.path.join(dirpath, file)
            if file.endswith(".dcm"):
                dcm_files.append(full_path)
            else:
                other_files.append(full_path)
    return dcm_files, other_files

def write_list_to_csv(file_list, output_csv_path, header):
    with open(output_csv_path, mode='w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([header])  # Add a header row
        for file_path in file_list:
            writer.writerow([file_path])
            
def read_file_paths_from_csv(file_path):
    file_paths = []
    with open(file_path, mode='r') as csvfile:
        reader = csv.reader(csvfile)
        # Skip the header row
        next(reader, None)
        for row in reader:
            if row:  # Ensure row is not empty
                file_paths.append(row[0])
    return file_paths


def split_at_anynumber_all(sequences):
    return [re.split(r'__\d+\.', seq, maxsplit=1)[0] for seq in sequences]

def split_at_anynumber_seq(sequence):
    return re.split(r'__\d+\.', sequence, maxsplit=1)[0] 



def get_dicom_value(dicom_path):
    try:
        dicom_data = pydicom.dcmread(dicom_path, stop_before_pixels=True)
        mod=dicom_data.Modality
        return mod
    except Exception:
        return None
    
    
def select_modalities(patient_data):
    dwi = patient_data[patient_data['Modality'] == 'dwi'].sort_values(by='Date').head(1)
    t1 = patient_data[patient_data['Modality'] == 't1'].sort_values(by='Date').head(1)
    if not dwi.empty and not t1.empty:
        return pd.concat([dwi, t1])
    return pd.DataFrame()  