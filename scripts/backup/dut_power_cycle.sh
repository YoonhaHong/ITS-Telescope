#!/bin/bash

echo '===== Power Cycling the DUT ====='
echo 'Powering off the DUT babyMOSS'
cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_2_2_W21D4.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/scripts
echo 'Powering Off the DUT DAQ'
./ps_dut_daq_OFF.py
sleep 1

echo 'Powering ON the DUT DAQ board'
./ps_dut_daq_ON.py
echo 'Programing the DUT DAQ board'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012905D1223E

echo '===== DUT Power Cycling is DONE ====='
