# APTS OA calibration data analysis scripts

Scripts to analyse the calibration data of APTS Op Amp chips operated with MLR1 DAQ board, oscilloscope and HMP power supply.

**Author** : Roberto Russo

**email** : r.russo@cern.ch

**Maintainer** : Roberto Russo

**Status**: Development test 

_______________
_______________

## Usage principles

All the software is entirely Python3 based. It is intended to be used to process and analyse data taken with the DAQ software https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/tree/master/opamp and https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/tree/master/scripts/opamp.

Requirements:
- mlr1daqboard (see https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/blob/master/README.md)
- lmfit package installed (https://lmfit.github.io/lmfit-py/)

Performed analysis:
- `00_gain_analysis.py`: analyse .raw data taken with the script opamp_gain.py by converting ADC and scope acquired waveforms in a _decoded.npz file and saving, for each measured Vbb and Vreset, average and rms baseline values, average and rms gain (defined as derivative of baseline) in an _analysed.npz file. On top of this, baseline and gain values for the scope measured pixels (for Vreset where gain > 0.80*max(gain)) are saved in a .json file (called gain.json). This file is used as a reference for further measurements.
- `01_pulsing_processing.py`: process .raw data taken with the script opamp_pulsing.py. ADC and scope acquired waveforms are converted in a _decoded.npz file. For each oscilloscope waveform, parameters like baseline, underline, amplitude, times at 10%, 50%, 90% constant fraction, falltime 10%-50% and falltime 10%-90% are extracted and saved into a .csv file. Another .csv file with signal amplitude mean and rms, falltime 10%-50% mean and rms, falltime 10%-90% mean and rms is generated. To compute mean and rms of amplitude and falltime, datasets are cleaned with InterQuartile Range (IQR) technique to discard outliers (https://towardsdatascience.com/ways-to-detect-and-remove-the-outliers-404d16608dba). By enabling the "control_plots" flag, signal amplitude, falltime 10%-50% and falltime 10%-90% distributions for each measured configuration are plotted. **When decoding raw data, data precision of the scope must be selected (1, 2 or 4 bytes).**
- `02_pulsing_analysis.py`: analyse the datasets produced by 01_pulsing_processing.py to find the optimal vreset to operate the chip at a given applied reverse bias. This is defined as the closest point to maximum gain, maximum signal amplitude, minimum falltime. Two .json files (optimal_smoothed_values.json and operation_point.json), containing, respectively, the vreset to optimize any single parameter and the global optimal working point are produced.
- `03_vh_scan_processing.py`: equivalent to 01_pulsing_processing.py for data taken with opamp_vh_scan.py. By enabling the proper flag, waveforms can be gain calibrated before being analysed. Different datasets are produced in case of gain calibration enabled. **When decoding raw data, data precision of the scope must be selected (1, 2 or 4 bytes).**
- `04_vh_scan_analysis.py`: analyse the datasets produced by 03_vh_scan_processing.py. Produce plots of signal amplitude and falltime at varying injected Vh. Supports the analysis of both non-gain calibrated and gain calibrated data. 
- `05_jitter_processing.py`: takes as input the dataset with waveform parameters produced by 03_vh_scan_processing.py to measure the time residuals between all the possible combinations of pixel couples measured with the oscilloscope for all the pulsed Vh values. Produces a .npy file for every pixel couple and Vh value. Supports the analysis of both non-gain calibrated and gain calibrated data.
- `06_jitter_analysis.py`: analyses files produced by 05_jitter_processing.py, fits time residuals distributions with a gaussian and produces a plot of the trend of time residuals width at varing Vh and Vbb. Supports the analysis of both non-gain calibrated and gain calibrated data.


The script `opamp_decode.py` is used as support to decode ADC and oscilloscope data, `analysis_utils.py` contains a set of common useful functions for the analysis. Finally, the folder `waveform_analysis` contains a script with a set of functions for the analysis of oscilloscope acquired waveforms (same as testbeam analysis routines).

Please refer to the next section for a usage example of the software. 

_________________________
_________________________

## Example

List of commands with example flags. Use the flag -h to access the helper.

- Gain calibration:
    ```
    $ ./00_gain_analysis.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/gain_calibration/20230310_172850
    ```

- Pulsing calibration:
    ```
    $ ./01_pulsing_processing.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/pulsing_calibration/20230311_012035 --control_plots --scope_data_precision 1
    ```
    ```
    $ ./02_pulsing_analysis.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/pulsing_calibration/20230311_012035 -g /run/media/alpide/Elements/Data/W22AO10Pb14/gain_calibration/20230310_172850/gain.json -p
    ```    

- Vh scan calibration:
    ```
    $ ./03_vh_scan_processing.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/vh_scan_calibration/20230312_162141 --control_plots --scope_data_precision 1
    ```
    ```
    $ ./04_vh_scan_analysis.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/vh_scan_calibration/20230312_162141
    ```

- Jitter analysis:
    ```
    $ ./05_jitter_processing.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/vh_scan_calibration/20230312_162141
    ```
    ```
    $ ./06_jitter_analysis.py -d /run/media/alpide/Elements/Data/W22AO10Pb14/vh_scan_calibration/20230312_162141
    ```