import os
import json
import pydicom
import pandas as pd


ANALYSIS_PATH='/home/bule/berner_daten_analyse/data'
output_path = os.path.join(ANALYSIS_PATH, "other_tags.json")





df = pd.read_csv(os.path.join(ANALYSIS_PATH,"dicom_files_df.csv"),sep=',')
unique_pairs = (df.sort_values(by="File_Name").drop_duplicates(subset=["Patient_ID", "Study_ID", "Sequence_ID"]).reset_index(drop=True))

unstructured={path:{} for path in unique_pairs['Full_Path']  }




# Function to extract DICOM tags
def extract_dicom_tags(dicom_path):
    try:
        ds = pydicom.dcmread(dicom_path)
        # Extract required tags
        image_type = ds.get((0x0008, 0x0008), None)
        study_description = ds.get((0x0008, 0x1030), None)
        repetition_time = ds.get((0x0018, 0x0080), None)
        echo_time = ds.get((0x0018, 0x0081), None)
        flip_angle = ds.get((0x0018, 0x1314), None)
        pixel_spacing = ds.get((0x0028, 0x0030), None)
        slice_thickness = ds.get((0x0018, 0x0050), None)

        # Return dictionary of extracted tags
        return {
            "Image_Type": image_type.value if image_type else None,
            "Study_Description": study_description.value if study_description else None,
            "Repetition_Time": repetition_time.value if repetition_time else None,
            "Echo_Time": echo_time.value if echo_time else None,
            "Flip_Angle": flip_angle.value if flip_angle else None,
            "Pixel_Spacing": [float(x) for x in pixel_spacing.value] if pixel_spacing else None,
            "Slice_Thickness": float(slice_thickness.value) if slice_thickness else None,
        }
    except Exception as e:
        return {"Error": str(e)}

# Function to convert non-serializable objects
def convert_to_serializable(obj):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return [str(item) for item in obj]  # Convert list or tuple to a list of strings
    return str(obj)  # Convert other types to string

# Main workflow
if not os.path.exists(output_path):
    for path in unstructured.keys():  # Process DICOM files
        print(f"Processing: {path}")
        unstructured[path] = extract_dicom_tags(path)

    # Convert to JSON-serializable format
    serializable_unstructured = {
        path: {key: convert_to_serializable(value) for key, value in metadata.items()}
        for path, metadata in unstructured.items()
    }

    # Save to JSON file
    with open(output_path, "w") as json_file:
        json.dump(serializable_unstructured, json_file, indent=4)
    print(f"Dictionary saved as JSON to: {output_path}")

else:
    # Load from existing JSON file
    with open(output_path, "r") as json_file:
        unstructured = json.load(json_file)
        print(f"Dictionary loaded from JSON: {output_path}")
