
import os
import pandas as pd
from datetime import datetime
import magic
import pydicom
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import csv
import re
from pymongo import MongoClient
import os
import pandas as pd
import pydicom
from pymongo import MongoClient


ANALYSIS_PATH='/home/bule/berner_daten_analyse'
df = pd.read_csv(os.path.join(ANALYSIS_PATH,"dicom_files_df.csv"),sep=',')

client = MongoClient("mongodb://localhost:27017/")
db_name = "bern_db"
db = client[db_name]

def extract_dicom_metadata(file_path):
    """Extract all tags from a DICOM file dynamically, handling nested datasets."""
    try:
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)  # Exclude pixel data for efficiency
        metadata = {}

        def parse_element(element):
            """Recursively parse a DICOM element."""
            if element.VR == "SQ":  # Sequence
                sequence_data = []
                for item in element.value:
                    item_metadata = {}
                    for sub_elem in item:
                        item_metadata[sub_elem.name] = parse_element(sub_elem)
                    sequence_data.append(item_metadata)
                return sequence_data
            elif isinstance(element.value, pydicom.dataset.Dataset):
                nested_metadata = {}
                for sub_elem in element.value:
                    nested_metadata[sub_elem.name] = parse_element(sub_elem)
                return nested_metadata
            else:
                return str(element.value)  
        for elem in ds:
            metadata[elem.name] = parse_element(elem)

        return metadata
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def populate_flattened_mongo(df, mongo_db):
    """Populate MongoDB with a flattened schema, avoiding duplicates."""
    for _, row in df.iterrows():
        patient_id = row["Patient_ID"]
        study_id = row["Study_ID"]
        sequence_id = row["Sequence_ID"]
        full_path = row["Full_Path"]

        # Extract metadata from DICOM file
        metadata = extract_dicom_metadata(full_path)
        if metadata is None:
            print(f"Skipped: Metadata extraction failed for {full_path}")
            continue

        # Define the filter for uniqueness
        filter_condition = {
            "patient_id": patient_id,
            "study_id": study_id,
            "sequence_id": sequence_id,
            "full_path": full_path,
        }

        # Check if the record already exists
        existing_record = mongo_db["dicom_data"].find_one(filter_condition)
        if existing_record:
            print(f"Skipped: Record already exists for {full_path}")
            continue

        # Insert the new record
        mongo_db["dicom_data"].insert_one({
            **filter_condition,
            "metadata": metadata
        })
        print(f"Inserted metadata for: {full_path}")

populate_flattened_mongo(df, db)