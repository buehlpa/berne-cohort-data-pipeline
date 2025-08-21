# Copyright [2025] [Pascal Buehler]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



import os
import json
import base64
import pydicom
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cv2



# To run this app open terminal and type the following commands:
# export FLASK_APP=0_0_app.py
# run on server : flask run --host=0.0.0.0 --port=5000

# (berner_daten) bule@deepthought:~/berner_daten_analyse/apps/app_manual_preselection$ export FLASK_APP=0_1_adc_app.py
# (berner_daten) bule@deepthought:~/berner_daten_analyse/apps/app_manual_preselection$ python -m flask --app 0_1_adc_app run --host=0.0.0.0 --port=5000

DATA_DIR = "/nasdata/Berner_Daten/Other_Side_Bilddaten"  # <------ Path to the RAW data
PROJECT_DIR = "/home/bule/berner_daten_analyse"          # <------ Path to the project directory


## if file does not exist comment the following lines:
# df_path = os.path.join(PROJECT_DIR,'data','dwi_t1_df_merged.csv')# "/home/bule/xAI_bern/lesion_segmentation/dwi_t1_df_merged_selection_for_adc.csv"
# df = pd.read_csv(df_path)

df = pd.read_csv("/home/bule/berner_daten_analyse/data/dwi_t1_df_merged_selection_for_adc2.csv")
##

# app
app = Flask(__name__)
app.secret_key = "your_secret_key"  


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        if username:
            session["username"] = username
            session["output_file"] = f"{username}_sequences.json"
            if not os.path.exists(session["output_file"]):
                with open(session["output_file"], "w") as f:
                    json.dump({}, f, indent=4)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Please enter a name.")
    return render_template("login.html")

@app.route("/index")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    excluded_patients = []  # Add excluded patient IDs here if needed <------------------------------
    all_patients = [
        patient for patient in os.listdir(DATA_DIR)
        if patient.startswith("0") and patient != "test" and patient not in excluded_patients
    ]
    patients = sorted(
        [d for d in all_patients if os.path.isdir(os.path.join(DATA_DIR, d)) and d not in excluded_patients ]
    )        
    highlighted_patients = [patient for patient in all_patients if int(patient.lstrip("0")) in list(set(df['Patient_ID']) )]
    return render_template("index.html", patients=patients, highlighted_patients=highlighted_patients)

@app.route("/patient/<patient_id>")
def patient_view(patient_id):
    patient_path = os.path.join(DATA_DIR, patient_id)
    studies = sorted([d for d in os.listdir(patient_path) if os.path.isdir(os.path.join(patient_path, d))])
    
    highlighted_studies = [
        study for study in studies if study in set(df['Study_ID'])
    ]
    
    return render_template("patient.html", patient_id=patient_id, studies=studies, highlighted_studies=highlighted_studies)



@app.route("/study/<patient_id>/<study_id>")
def study_view(patient_id, study_id):
    study_path = os.path.join(DATA_DIR, patient_id, study_id)
    sequences = sorted([d for d in os.listdir(study_path) if os.path.isdir(os.path.join(study_path, d))])

    try:
        if 'df' in locals() or 'df' in globals():
            highlighted_sequences = [
                seq for seq in sequences if seq in set(df['Sequence_ID'])
            ]
        else:
            highlighted_studies = []
    except NameError:
        highlighted_studies = []
    return render_template("study.html", patient_id=patient_id, study_id=study_id, sequences=sequences, highlighted_sequences=highlighted_sequences)


@app.route("/sequence/<patient_id>/<study_id>/<sequence>")
def sequence_view(patient_id, study_id, sequence):
    sequence_path = os.path.join(DATA_DIR, patient_id, study_id, sequence)
    dicom_files = sorted([f for f in os.listdir(sequence_path) if f.endswith(".dcm")])
    return render_template("sequence.html", patient_id=patient_id, study_id=study_id, sequence=sequence, dicom_files=dicom_files)

@app.route("/dicom_slice", methods=["POST"])
def dicom_slice():
    data = request.json
    dicom_file_path = os.path.join(
        DATA_DIR, data["patient_id"], data["study_id"], data["sequence"], data["dicom_file"]
    )
    try:
        ds = pydicom.dcmread(dicom_file_path)
        if hasattr(ds, "pixel_array"):
            pixel_array = ds.pixel_array
            img = (pixel_array - np.min(pixel_array)) / (np.max(pixel_array) - np.min(pixel_array)) * 255
            img = img.astype(np.uint8)
            _, img_encoded = cv2.imencode(".png", img)
            img_base64 = base64.b64encode(img_encoded).decode("utf-8")
        else:
            img_base64 = None
        metadata = {tag: str(ds[tag].value) for tag in ds.dir() if tag in ds}

        return jsonify({"image_data": f"data:image/png;base64,{img_base64}" if img_base64 else None, "metadata": metadata})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/add_sequence", methods=["POST"])
def add_sequence():
    if "username" not in session:
        return redirect(url_for("login"))
    output_file = session["output_file"]
    data = request.json
    patient_id = data["patient_id"]
    study_id = data["study_id"]
    
    category = data["category"]
    sequence = data["sequence"]
    
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            selections = json.load(f)
    else:
        selections = {}
    if patient_id not in selections:
        selections[patient_id] = {"dwi": [], "t1": [], "other": []}
    if sequence not in selections[patient_id][category]:
        selections[patient_id][category].append(os.path.join(study_id,sequence))

    with open(output_file, "w") as f:
        json.dump(selections, f, indent=4)
    return jsonify({"message": "Sequence added and saved."})

@app.route("/save_and_next/<current_patient>")
def save_and_next(current_patient):
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
