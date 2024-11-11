#!/bin/bash

echo '===== Start up the telescope ====='
./ps_usb_ON.py
echo 'Wating for the USB HUB Power to Stabilize for 10 sec'
sleep 10
echo '===== [Refernce Plane] ====='
echo 'Power on the Reference Planes'
./ps_ref_daq_ON.py
sleep 2 
echo 'Programing the Reference DAQ boards'
raiser-daq-program --list

raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --all 

echo '===== [DUT Plane] ====='
echo 'Power on the DUT psub'
./ps_dut_psub_ON.py
echo 'Power on the DUT Plane'
./ps_dut_daq_ON.py
sleep 2

echo 'Programing the DUT DAQ board'
raiser-daq-program --list

raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012905D1223E

echo '===== [Triger Board] ====='
echo 'Power on the Triger Board'
./ps_trg_ON.py
echo 'Set the tirgger logic'
source trg_config_and_set.sh

echo '===== Sart up is DONE ====='

