#!/usr/bin/env bash

# Isabella Sanna, 03/2022, CERN
# Bash script that controls the acquisition of all the scans of all paramters for APTS. 
# HAMEG.py: script used to control the power supply (on, off, set voltages ecc..)
# All directories should be checked and changed depending on the user needs

HAMEG --off -c 1
HAMEG --off -c 3
HAMEG -c 3 -v 0
HAMEG --on -c 1
HAMEG --on -c 3
../../tools/mlr1-daq-program --fx3=../../tools/fx3.img --fpga=../../tools/0x107E631E.bit #loading of firmwares
python3 ../../apts/apts_power_on.py APTS-003

for vbb in 0.0 1.0 2.0 3.0 4.0; do 
    HAMEG -c 3 -v="$vbb"
    python3 apts_readout_scan_operating_point.py APTS-003 --suffix="_vbb$vbb" -vdir="$vbb" -p f -n 50
done

HAMEG --off -c 1
HAMEG --off -c 3
HAMEG -c 3 -v 0
python3 apts_decode_scan_operating_point.py ../../../Data/scan_operating_point