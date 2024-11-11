#!/bin/bash

echo 'Power Cycling the REF Planes'

echo 'Power Off all REF Planes'
cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_1_2_W24B5.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_5_1_W20E1.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_2_1_W22C7.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_2_5_W21D4.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_3_5_W24B5.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_4_6_W20E1.json5 fire_ts_config.json5
cd ~/testbeam/TB_August_2024/sw
moss_tb power_off_all_half_units

cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_conifg.json5
cd config
ln -s tb_conifgs/ts_config_raiser_2_2_W21D4.json5 fire_ts_config.json5

cd ~/testbeam/TB_August_2024/scripts
echo 'Power Off the REf DAQ board'
./ps_ref_daq_OFF.py
sleep 1

echo 'Power On the REF DAQ board'
./ps_ref_daq_ON.py
echo 'Programing the REF DAQ board'
sleep 1

echo 'Plane 0'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012905D1153D
echo 'Plane 1'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012905CF1604
echo 'Plane 2'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012D0F0A340F
echo 'Plane 4'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-00090101054B1F08
echo 'Plnae 5'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-00090101054B3009
echo 'Plane 6'
raiser-daq-program --fx3 ~/fw/fx3.img --fpga ~/fw/raiser-daq-fpga-firmware_rdo.bit --serial DAQ-0009012D0F0A1520

echo 'Programing is Done'

echo 'REF Planes Power Cycling is Done'

