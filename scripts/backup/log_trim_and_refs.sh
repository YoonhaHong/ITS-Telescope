#!/bin/bash

echo 'Measure all BabyMOSS DAC references and trimming settings'
cd ~/testbeam/TB_August_2024/sw

CURRENT_TIME=$(date +%Y-%m-%d_%H_%M_%S)
WORKING_DIR=~/testbeam/TB_August_2024/data/trim_ref_logs/$CURRENT_TIME
mkdir $WORKING_DIR

for SENSOR in "1_2_W24B5" "5_1_W20E1" "2_1_W22C7" "2_2_W21D4" "2_5_W21D4" "3_5_W24B5" "4_6_W20E1"
do
    echo "Measuring trimming and reference settings for babyMOSS-$SENSOR"
    rm config/fire_ts_config.json5
    cd config
    ln -s tb_configs/ts_config_raiser_$SENSOR.json5 fire_ts_config.json5
    cd ~/testbeam/TB_August_2024/sw
    python3 scripts/log_trim_and_ref.py $WORKING_DIR
done

echo "Setting default fire_ts_config for DUT"
cd ~/testbeam/TB_August_2024/sw
rm config/fire_ts_config.json5
cd config
ln -s tb_configs/ts_config_raiser_2_2_W21D4.json5 fire_ts_config.json5

echo 'Logging done'
