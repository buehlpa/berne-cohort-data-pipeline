# MRI data from bern 

This repo is for the selection and creation of a skullstripped / defaced dataset for dwi MRI data.
    it includes:


1.
    - programatic  filter based on dicom tags reffering to dwi and t1 swequences
    - manual selection of sequences by doctors supported by browser app
2.
    - conversion of selected dicom files to nifit format

3.
    - skullstripping and defacing of the selected files with https://github.com/BrainLesion/preprocessing
    - manual positiv selection of qualitatively good strippings

4.
    - creation of a HDF dataset with skullstripped dwi / defaced dwi aswell as clinical data 

