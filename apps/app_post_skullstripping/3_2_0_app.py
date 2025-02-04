import os
import json
import nibabel as nib
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import base64
import matplotlib.pyplot as plt
from io import BytesIO


#export FLASK_APP=3_2_0_app.py
# run on server : flask run --host=0.0.0.0 --port=5001


# Flask application setup
app = Flask(__name__)
app.secret_key = "your_secret_key"


# change path here for the fional nifti files
data_dir = "/home/bule/berner_daten_analyse/data/nifti_third_try/processed"


selection_file = "user_selection.json"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        if username:
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Please enter a name.")
    return render_template("login.html")

@app.route("/index")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    patients = sorted(os.listdir(data_dir))
    return render_template("index.html", patients=patients)

@app.route("/patient/<patient_id>")
def patient_view(patient_id):
    patient_path = os.path.join(data_dir, patient_id)
    
    
    image_paths = {
        "dwi_bet_normalized": os.path.join(patient_path, "norm_bet_dir/dwi_bet_normalized.nii.gz"),
        "dwi_defaced_normalized": os.path.join(patient_path, "norm_defaced_dir/dwi_defaced_normalized.nii.gz"),
        
        "t1_bet_normalized": os.path.join(patient_path, "norm_bet_dir/t1_bet_normalized.nii.gz"),
        "t1_defaced_normalized": os.path.join(patient_path, "norm_defaced_dir/t1_defaced_normalized.nii.gz"),
        
        # "t1_bet_mask": os.path.join(patient_path, "masks/t1_bet_mask.nii.gz"),
        # "t1_defacing_mask": os.path.join(patient_path, "masks/t1_defacing_mask.nii.gz")
        
        "dwi_skull_normalized": os.path.join(patient_path, "norm_skull_dir/dwi_skull_normalized.nii.gz"),
        "t1_skull_normalized": os.path.join(patient_path, "norm_skull_dir/t1_skull_normalized.nii.gz"),
    }

    default_image = "dwi_bet_normalized"
    selected_image_path = image_paths.get(default_image)
    nifti_data = nib.load(selected_image_path)
    dimensions = nifti_data.shape  # Get dimensions for slider limits

    return render_template("patient.html", patient_id=patient_id, image_paths=image_paths, dimensions=dimensions, default_image=default_image)

@app.route("/get_slice", methods=["POST"])
def get_slice():
    data = request.json
    image_path = data.get("image_path")
    slice_index = int(data.get("slice_index", 0))

    if not image_path or not os.path.exists(image_path):
        return jsonify({"error": "Invalid image path."}), 400
    try:
        nifti_data = nib.load(image_path)
        img = nifti_data.get_fdata()
        slice_img = img[:, :, slice_index]
        norm_slice = (slice_img - np.min(slice_img)) / (np.max(slice_img) - np.min(slice_img)) * 255
        norm_slice = norm_slice.astype(np.uint8)

        plt.figure(figsize=(4, 4))
        plt.axis('off')
        plt.imshow(norm_slice, cmap='gray')
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()
        plt.close()
        return jsonify({"slice": img_base64})
    except Exception as e:
        print(f"Error generating slice: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/add_result", methods=["POST"])
def add_result():
    if "username" not in session:
        return jsonify({"error": "User not logged in."}), 403

    username = session["username"]
    data = request.json
    patient_id = data.get("patient_id")
    result = data.get("result")

    if patient_id and result:
        if os.path.exists(selection_file):
            with open(selection_file, "r") as f:
                selections = json.load(f)
        else:
            selections = {}
        if username not in selections:
            selections[username] = {}
        selections[username][patient_id] = result
        with open(selection_file, "w") as f:
            json.dump(selections, f, indent=4)
        return jsonify({"message": f"Result saved in {selection_file} for user {username}."})
    return jsonify({"error": "Invalid data."}), 400

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True, port=5001)
