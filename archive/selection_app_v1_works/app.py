import os
import json
import base64
import pydicom
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for
import cv2

 
# patids mit excluded hier rein
excluded_patients = []#["0000076813"]

app = Flask(__name__)
data_dir = "/nasdata/Berner_Daten/Other_Side_Bilddaten"
output_file = "sequences.json"


if not os.path.exists(output_file):
    with open(output_file, "w") as f:
        json.dump({}, f, indent=4)

# if there iis alredeay a selectio n file 
if os.path.exists(output_file):
    with open(output_file, "r") as f:
        selections = json.load(f)
else:
    selections = {}
    
@app.route("/")
def index():
    patients = sorted(
        [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)) and d not in excluded_patients]
    )
    return render_template("index.html", patients=patients)

@app.route("/patient/<patient_id>")
def patient_view(patient_id):
    patient_path = os.path.join(data_dir, patient_id)
    studies = sorted([d for d in os.listdir(patient_path) if os.path.isdir(os.path.join(patient_path, d))])
    return render_template("patient.html", patient_id=patient_id, studies=studies)

@app.route("/study/<patient_id>/<study_id>")
def study_view(patient_id, study_id):
    study_path = os.path.join(data_dir, patient_id, study_id)
    sequences = sorted([d for d in os.listdir(study_path) if os.path.isdir(os.path.join(study_path, d))])
    return render_template("study.html", patient_id=patient_id, study_id=study_id, sequences=sequences)

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
    data = request.json
    patient_id = data["patient_id"]
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
        selections[patient_id][category].append(sequence)

    with open(output_file, "w") as f:
        json.dump(selections, f, indent=4)
    return jsonify({"message": "Sequence added and saved."})

@app.route("/save_and_next/<current_patient>")
def save_and_next(current_patient):
    print('')
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
