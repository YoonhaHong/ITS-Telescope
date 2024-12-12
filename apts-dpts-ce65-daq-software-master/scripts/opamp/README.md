# APTS OA calibration data acquisition scripts

Scripts to control the data acquisition of calibration procedure with test pulses for APTS OPAMP chips with MLR1 DAQ board, oscilloscope and HMP power supply.
The oscilloscope has to be connected to the computer via TCP port (ethernet), the power supply via USB.

**Author** : Roberto Russo

**email** : r.russo@cern.ch

**Maintainer** : Roberto Russo

**Status**: Development test

_______________
_______________

## Usage principles

All the software is entirely Python3 based.
Requirements:
- mlr1daqboard (see https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/blob/master/README.md)
- labequipment (see https://gitlab.cern.ch/alice-its3-wp3/lab-equipment)
- Oscilloscope with programming interface compatible with one of the classes implemented in mlr1daqboard/opamp_scope.py

Measurements performed:
- opamp_pulsing.py: based on the result of opamp_gain.py (https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/blob/master/opamp/opamp_gain.py) measurement, pulse the pixels with Vh = 1200 mV for Vreset values where gain >= 0.8*max(gain) at varying Vsub. The acquired waveforms are used to establish the optimal working point (Vreset) for each Vsub applied. The measurement is based on the file gain.json produced by the analysis of the data taken with opamp_gain.py. It is also possible to send test pulses at a fixed Vreset value by enabling the proper flag.
- opamp_vh_scan.py: based on the optimal working points found with opamp_pulsing.py, acquire waveforms with different pulsing voltage Vh. The measurement is based on the files gain.json and operation_point.json produced by the analysis of the data taken with opamp_gain.py and opamp_pulsing.py, respectively.

As described, some of the measurements are based on the result of the analysis of previously taken data. The analysis software can be found in https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/tree/master/analysis/opamp.
Please refer to the next section for a usage example of the software.

_________________________
_________________________

## Example

List of commands with example flags. Use the flag -h to access the helper.

- Pulsing calibration:
    ```
    $ ./opamp_pulsing.py OPAMP-015 W22AO10Pb14 /run/media/alpide/Elements/Data/W22AO10Pb14/gain_calibration/20230119_164530/gain.json Infiniium --vbb_scan -o /run/media/alpide/Elements/Data/ -hpath /dev/hmp4040 -daqc 1 -vbbc 2 -ip 192.168.1.13 -ssp 0.0625E-9
    ```
    If want to perform the measurement at a fixed Vreset, enble the flag `--fixed_vreset_measurement`. In this case, the desired operation Vreset value should be specified with the flag `--vreset`, or the default value of 400 mV will be set.

- Vh scan:
    ```
    $ ./opamp_vh_scan.py OPAMP-015 W22AO10Pb14 /run/media/alpide/Elements/Data/W22AO10Pb14/gain_calibration/20230119_164530/gain.json /run/media/alpide/Elements/Data/W22AO10Pb14/pulsing_calibration/20230119_225710/operation_point.json  Infiniium --vbb_scan -o /run/media/alpide/Elements/Data/ -hpath /dev/hmp4040 -daqc 1 -vbbc 2 -ip 192.168.1.13 -ssp 0.0625E-9
    ```
