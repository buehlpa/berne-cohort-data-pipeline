# MRI data from bern 

- This repo is for the selection and creation of a skullstripped / defaced dataset for dwi MRI data.
    it includes:



- programatic  filter based on dicom tags reffering to dwi and t1 swequences
- manual selection of sequences by doctors supported by browser app
- conversion of selected dicom files to nifit format
- skullstripping and defacing of the selected files
- manual positiv selection of qualitatively good strippings
- creation of a HDF dataset with skullstripped dwi / defaced dwi aswell as clinical data 

