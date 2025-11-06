# MRI Data Processing Pipeline — Bernese Dataset

## Overview
This repository provides a complete pipeline for the **selection, preprocessing, and dataset creation** of skull-stripped and defaced **DWI MRI data** from the Bern dataset.  
It includes steps for data selection, DICOM-to-NIfTI conversion, quality control, skull stripping, defacing, and integration of clinical tabular data.
Additionally it provides the Lesions a Lesion Segmentation Script using DeepIsles (https://github.com/ezequieldlrosa/DeepIsles).


---

## Data Requirements
To run the pipeline, you need access to the following data sources:

- MRI image data:  
  `/nasdata/Berner_Daten/Other_Side_Bilddaten`

- Clinical tabular data:  
  `/data/clinical/Kopie Olea von Relevent Data Other File 20181005.xlsx`

---

## Environment Setup
1. Create a new Conda environment.  
2. Install all dependencies:
   ```bash
   pip install -r requirements_pip_freeze.txt

## Pipeline Components
1. Sequence Selection

Manual selection of MRI sequences by medical experts, supported by a browser-based interface:

Run 0_0_app.py for visual inspection and selection.

2. DICOM to NIfTI Conversion

Converts selected DICOM files into NIfTI format.

Prepares data for ADC map selection, which is later used for lesion segmentation and concept extraction (RCAV).

3. Skull Stripping and Defacing

Uses preprocessing tools from BrainLesion/preprocessing
.

Includes manual quality control and positive selection of high-quality skull-stripped images.

4. HDF5 Dataset Creation

Combines skull-stripped and defaced DWI images with clinical data into an HDF5 dataset.

Builds upon previously selected DWI and T1 files.

Remaining patients (n = 297) undergo ADC selection and NIfTI conversion.

Lesion segmentation is performed using DeepIsles
 (Docker image required).

5. Data Comparison and Analysis

Final step includes tensor comparison and evaluation of processed datasets.

## Notes

The DeepIsles Docker image must be installed prior to running the segmentation step.

Ensure that all required paths and environment variables are accessible within the computing environment.

## Summary

This repository provides a structured and reproducible workflow for creating a high-quality MRI dataset (DWI, skull-stripped, and defaced) integrated with clinical data from Bern. It is designed to facilitate subsequent lesion segmentation, model training, and analysis.
