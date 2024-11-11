#!/bin/bash

echo '===== Shutting off the telescope ====='

echo '===== [babyMOSS] ====='
echo 'Power Off all babyMOSS'
source babymoss_power_off_all.sh

cd ~/testbeam/TB_August_2024/scripts

echo '===== [Trigger Board] ====='
echo 'Power Off the Trigger Board'
./ps_trg_OFF.py

echo '===== [DUT Plane] ====='
echo 'Power Off the DUT'
./ps_dut_daq_OFF.py
echo 'Turn off PSUB'
./ps_dut_psub_OFF.py

echo '===== [Reference Plane] ====='
echo 'Power Off the Reference Planes'
./ps_ref_daq_OFF.py

echo 'Turn off USB HUB'
./ps_usb_OFF.py

echo '===== Power Off is DONE ====='


