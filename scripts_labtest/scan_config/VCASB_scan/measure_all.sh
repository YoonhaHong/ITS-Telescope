

# use scan_config/config_generator to generate configs. Specify range in file.
#cd scan_config
#python3  config_generator_VCASB_scan.py
#cd ..

#thr_scan -c VCASB_40.json5
#thr_scan -c VCASB_50.json5
#thr_scan -c VCASB_60.json5
#thr_scan -c VCASB_70.json5
#thr_scan -c VCASB_80.json5
#thr_scan -c VCASB_90.json5

cd /home/hipex/Telescope/sw/analyses/
./thr_scan_analysis.py /home/hipex/MOSS_TEST_RESULTS/babyMOSS-2_4_W21D4/ThresholdScan/babyMOSS-2_4_W21D4_ThresholdScan_20250223_160223


# mv new results folders from ThresholdScan/ to ThresholdScanCollection2025/





# python3 vcasb2threshold.py "/home/hipex/MOSS_TEST_RESULTS/babyMOSS-2_4_W21D4/ThresholdScan/ScanCollection2025"



