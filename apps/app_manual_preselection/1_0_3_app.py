import os
import json
import base64
import pydicom
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cv2


#export FLASK_APP=1_0_3_app.py
# run on server : flask run --host=0.0.0.0 --port=5000

app = Flask(__name__)
app.secret_key = "your_secret_key"  
data_dir = "/nasdata/Berner_Daten/Other_Side_Bilddaten"

import pandas as pd

df_path = "/home/bule/berner_daten_analyse/data/dwi_t1_df_2.csv" #
df = pd.read_csv(df_path)


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
    excluded_patients = []  # Add excluded patient IDs here <------------------------------
    all_patients = [
        patient for patient in os.listdir(data_dir)
        if patient.startswith("0") and patient != "test" and patient not in excluded_patients
    ]
    patients = sorted(
        [d for d in all_patients if os.path.isdir(os.path.join(data_dir, d)) and d not in excluded_patients ]
    )        
    highlighted_patients = [patient for patient in all_patients if int(patient.lstrip("0")) in list(set(df['Patient_ID']) )]
    return render_template("index.html", patients=patients, highlighted_patients=highlighted_patients)

@app.route("/patient/<patient_id>")
def patient_view(patient_id):
    patient_path = os.path.join(data_dir, patient_id)
    studies = sorted([d for d in os.listdir(patient_path) if os.path.isdir(os.path.join(patient_path, d))])
    
    highlighted_studies = [
        study for study in studies if study in set(df['Study_ID'])
    ]
    
    return render_template("patient.html", patient_id=patient_id, studies=studies, highlighted_studies=highlighted_studies)



@app.route("/study/<patient_id>/<study_id>")
def study_view(patient_id, study_id):
    study_path = os.path.join(data_dir, patient_id, study_id)
    sequences = sorted([d for d in os.listdir(study_path) if os.path.isdir(os.path.join(study_path, d))])

        
    highlighted_sequences = [
        seq for seq in sequences if seq in set(df['Sequence_ID'])
    ]
    return render_template("study.html", patient_id=patient_id, study_id=study_id, sequences=sequences, highlighted_sequences=highlighted_sequences)


@app.route("/sequence/<patient_id>/<study_id>/<sequence>")
def sequence_view(patient_id, study_id, sequence):
    sequence_path = os.path.join(data_dir, patient_id, study_id, sequence)
    dicom_files = sorted([f for f in os.listdir(sequence_path) if f.endswith(".dcm")])
    return render_template("sequence.html", patient_id=patient_id, study_id=study_id, sequence=sequence, dicom_files=dicom_files)

@app.route("/dicom_slice", methods=["POST"])
def dicom_slice():
    data = request.json
    dicom_file_path = os.path.join(
        data_dir, data["patient_id"], data["study_id"], data["sequence"], data["dicom_file"]
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
    #TODO save logic 
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
