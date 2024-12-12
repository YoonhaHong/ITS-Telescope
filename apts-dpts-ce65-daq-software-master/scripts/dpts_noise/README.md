## Code for the evaluation of the FHR thermal model
The main script `DPTS_noise_model_analysis.py` computes the FHR thermal model based on the input data, using the thermal model descriveb here: https://cds.cern.ch/record/2303618?ln=en

**Input**
1. Output of [fhana_param.py](analysis/dpts/fhrana_param.py): .json file with the measured FHR 
2. Output of [threhsoldana_param.py](analysis/dpts/threhsoldana_param.py): .json file with the thresholds and noise and .json file with the threshold fit parameters
3. A json file from one of the FHR measurements