#!/bin/bash

cd ../sw

echo "=====tb :: Region0====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/tb_full_rdo/region0/fhr_thr/*

echo "=====tb :: Region1====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/tb_full_rdo/region1/fhr_thr/*

echo "=====tb :: Region2====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/tb_full_rdo/region2/fhr_thr/*

echo "=====tb :: Region3====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/tb_full_rdo/region3/fhr_thr/*

echo "=====bb :: Region0====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/bb_full_rdo/region0/fhr_thr/*

echo "=====bb :: Region1====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/bb_full_rdo/region1/fhr_thr/*

echo "=====bb :: Region2====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/bb_full_rdo/region2/fhr_thr/*

echo "=====bb :: Region3====="
python3 -m moss_scans.scan_collection FakeHitRateScan ThresholdScan -e -c /home/palpidefs/testbeam/TB_August_2024/eudaq_configs/babyMOSS-2_2_W21D4/bb_full_rdo/region3/fhr_thr/*