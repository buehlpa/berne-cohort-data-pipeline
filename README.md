# MRI data from bern 

## Data
For this "Pipeline" to work you need the Data Export:

`/nasdata/Berner_Daten/Other_Side_Bilddaten` From Bern

aswell as the tabular data:

`/data/clinical/Kopie Olea von Relevent Data Other File 20181005.xlsx`

## Environment
Install packages via:

create conda environment and : `pip install -r requirements_pip_freeze.txt` all packages into it


## Content
This repo is for the selection and creation of a skullstripped / defaced dataset for dwi MRI data.
    it includes:



1. - manual selection of sequences by doctors supported by browser app in 0_0_app.py
2. - conversion of selected dicom files to nifit format
   -prepartion for adc selection -> used for lesion segmentatoion -> used as concepts for RCAV

3. - skullstripping and defacing of the selected files with https://github.com/BrainLesion/preprocessing
   - manual positiv selection of qualitatively good strippings

4. - creation of a HDF dataset with skullstripped dwi / defaced dwi aswell as clinical data 
   - based on the eralier selection of dwi and t1 files, the remaining patients n= 297 are also up for a selection of adc files -> nifti conversion
   - descriptions of the tabular data
   
5. Compare the final tensors 
