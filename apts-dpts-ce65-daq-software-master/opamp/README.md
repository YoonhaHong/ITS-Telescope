# APTS OA control scripts

Scripts to control APTS OPAMP chips operated with MLR1 DAQ board, oscilloscope and HMP power supply.
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

Opertions performed:
- opamp_gain.py: measure the pixel baselines at varying Vbb and Vreset to evaluate the gain curves
- opamp_power.py: power on/off the chip
- opamp_readout.py: general purpose DAQ script

The analysis script for data taken with `opamp_gain.py` is https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/blob/master/analysis/opamp/00_gain_analysis.py.
Please refer to the next section for a usage example of the software.

_________________________
_________________________

## Example

List of commands with example flags. Use the flag -h to access the helper.

- Power on:
    ```
    $ ./opamp_power.py OPAMP-015 W22AO10Pb14 on
    ```

- Baseline measurement:
    ```
    $ ./opamp_gain.py OPAMP-015 W22AO10Pb14 Infiniium --vbb_scan -o /run/media/alpide/Elements/Data -hpath /dev/hmp4040 -daqc 1 -vbbc 2 -ip 192.168.1.13 -ssp 0.0625E-9
    ```

- Power off:
    ```
    $ ./opamp_power.py OPAMP-015 W22AO10Pb14 off
    ```