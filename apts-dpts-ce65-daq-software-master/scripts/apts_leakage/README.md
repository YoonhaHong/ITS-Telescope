# APTS SF Leakage analysis scripts
Created on 06-10-2023 by Long LI

## APTS SF leakage data taking 

- This scrip is based on D. Schledewitz's work, Many thanks to him

- First of al, run `python3 apts_leakage_scan.py` to take data, for example, 
`python3 apts_leakage_scan.py PROXIMITY chip_ID -n 1000 -nvres 50 -ty int -fw 0x*.bit 
-hpath /dev/hmp2030 -daqc 1 -vbbc 2 -vbbr 0.0 1.2 2.4 3.6 4.8 -irr 0.2 0.4 0.6 0.8 1.0 1.2 1.4 1.6 
-tr 20 -p f -o ../../Data`, please use`-h` for usage.
- Temperature control module is not used for the moment, since no chiller is available for APTS measurement.
Need optimization if you need various temperatures.

## Data calibration
- Next do the decoding and signal callibration using `python3 apts_leakage_calibration.py 
-d ../../Data -prox PROXIMITY -c chip_ID -tr 20 -vbbr 0.0 1.2 2.4 3.6 4.8 -irr 0.2 0.4 0.6 0.8 
1.0 1.2 1.4 1.6`, please use your own data location and proximity & chip name, same as follows. Please see `-h` for usage.


## Leakage analysis
- Before the leakage current comparison among multiple chips, you should put all data for chips in 
comparison in the same directory, for example, `../../Data/APTS-013/AF15P_W22B3` and `../../Data/APTS-013
/AF15P_W19B1`
- Next use the `python3 apts_leakage_fit.py -d ../../Data -prox PROXIMITY -c chip_ID` 
to do the waveform fit, all results are saved in `apts_*_Fit_results.npz` 

- To show the pulse waveform, you could simply run `python3 apts_leakage_waveform.py -d ../../Data 
-prox PROXIMITY -c chip_ID -ir 100 -v 4.8 -p 0 0 `, all plots will be saved under `../../Data/
PROXIMITY/chip_ID/leakage_results/` by default, you could also define the output directory using
`-o`, please use `-h` for more usage. 

- To show leakage current as function of `T` of `vbb`, you could run `python3 apts_leakage_analysis 
-d ../../Data -cc AF15P_W15B3 AF15P_W19B1 -cpar split -tr 20 -vbbr 0.0 1.2 2.4 3.6 4.8 -yr -5 10 -dp 3`, 2 folders will be created automatically, 
`../../Data/APTS-013/AF15P_W22B3/leakage_results` and `../../Data/leakage_comparison`. The first 
one contains the leakage analysis results againt `vbb` and `T` of the corresponding sensor, while
the latter contains the leakage comparison results among sensors(`AF15P_W22B3` and `AF15P_W19B1`here,
for example)
### Additional info
- For calibration and waveform fit, you could simply run `python3 run_full_leakage_analysis.py -d ../../Data`.
The default vbb range is `0.0 1.2 2.4 3.6 4.8` and the default ireset range is `0.2 0.4 0.6 0.8 1.0
1.2 1.4 1.6`