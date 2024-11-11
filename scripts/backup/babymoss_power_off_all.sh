#!/bin/bash

echo 'Power off all babyMOSS'

for SENSOR in "1_2_W24B5" "5_1_W20E1" "2_1_W22C7" "2_2_W21D4" "2_5_W21D4" "3_5_W24B5" "4_6_W20E1"
do
    echo "Turning off babyMOSS-$SENSOR"
    cd ~/testbeam/TB_August_2024/sw
    rm config/fire_ts_config.json5
    cd config
    ln -s tb_configs/ts_config_raiser_$SENSOR.json5 fire_ts_config.json5
    cd ~/testbeam/TB_August_2024/sw
    moss_tb power_off_all_half_units
done

echo "Setting default fire_ts_config for DUT"
cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_2_2_W21D4.json5 fire_ts_config.json5

echo "All babyMOSS are now powered off!"
