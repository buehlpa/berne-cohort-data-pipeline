import os
import json
import base64
import nibabel as nib
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cv2

app = Flask(__name__)
app.secret_key = "your_secret_key"
data_dir = "/home/bule/berner_daten_analyse/data/nifti_second_try"


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
    excluded_patients = []  # Add excluded patient IDs here  <---------------------------------------------------------------
    all_patients = [
        patient for patient in os.listdir(data_dir)
        if patient.startswith("0") and patient != "test" and patient not in excluded_patients
    ]
    patients = sorted(
        [d for d in all_patients if os.path.isdir(os.path.join(data_dir, d)) and d not in excluded_patients ]
    )        
    return render_template("index.html", patients=patients,)


@app.route("/patient/<patient_id>")
def patient_view(patient_id):
    patient_path = os.path.join(data_dir, patient_id)
    studies = sorted([d for d in os.listdir(patient_path) if os.path.isdir(os.path.join(patient_path, d))])
    return render_template("patient.html", patient_id=patient_id, studies=studies, )


@app.route("/study/<patient_id>/<study_id>")
def study_view(patient_id, study_id):
    study_path = os.path.join(data_dir, patient_id, study_id)
    sequences = sorted([d for d in os.listdir(study_path) if os.path.isdir(os.path.join(study_path, d))])
    
    return render_template("study.html", patient_id=patient_id, study_id=study_id, sequences=sequences)


@app.route("/sequence/<patient_id>/<study_id>/<path:sequence>")
def sequence_view(patient_id, study_id, sequence):
    sequence_path = os.path.join(data_dir, patient_id, study_id, sequence)
    print(sequence_path)
    sequence_path= [os.path.join(data_dir, patient_id, study_id, sequence, path) for path in os.listdir(sequence_path) if path.endswith('.nii.gz') ][0]
    nifti_img = nib.load(sequence_path)
    num_slices = nifti_img.shape[2]
    return render_template("sequence.html", patient_id=patient_id, study_id=study_id, sequence=sequence, num_slices=num_slices)



@app.route("/nifti_slice", methods=["POST"])
def nifti_slice():
    data = request.json
    nifti_file_path = os.path.join(
        data_dir, data["patient_id"], data["study_id"], data["sequence"]
    )
    try:
        nifti_img = nib.load(nifti_file_path)
        img_data = nifti_img.get_fdata()
        slice_index = int(data["slice_index"])  # Explicitly cast slice_index to integer

        if img_data.ndim == 4:  # Handle multi-channel data
            img_data = img_data[:, :, :, -1]

        slice_img = img_data[:, :, slice_index]
        normalized_img = (slice_img - np.min(slice_img)) / (np.max(slice_img) - np.min(slice_img)) * 255
        normalized_img = normalized_img.astype(np.uint8)
        _, img_encoded = cv2.imencode(".png", normalized_img)
        img_base64 = base64.b64encode(img_encoded).decode("utf-8")

        header = nifti_img.header
        metadata = {key: str(header[key]) for key in header.keys()}

        return jsonify({"image_data": f"data:image/png;base64,{img_base64}", "metadata": metadata})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/add_sequence", methods=["POST"])
def add_sequence():
    if "username" not in session:
        return redirect(url_for("login"))
    output_file = session["output_file"]
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
    if "username" not in session:
        return redirect(url_for("login"))
    output_file = session["output_file"]
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            selections = json.load(f)
        selections[current_patient] = selections.get(current_patient, {})
        with open(output_file, "w") as f:
            json.dump(selections, f, indent=4)
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
