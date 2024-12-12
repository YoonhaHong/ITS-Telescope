## analysis of apts-sf source data
- Taking data with the source: after you connect the chip and turn on the hameg, run the following script from apts folder putting all the options you might need (the script powers the DUTs, uploads the fw, performs a gain calibration and after input from the user, starts the source scan voltage).
```
./apts_source_scan.py PROXIMITY CHIP_ID
```
Note that for the choice of the threshold, it might be useful to run the script apts_readout.py

- Now you can move the the folder analysis/apts/ . After decoding of data (using the script apts_decode.py) and calibrated runs (using the script analysis_gain.py), to run the analysis you can simply run the follwing script (putting or removing all the options you might need)

```
./run_full_analysis.py file_in directory  --file_calibration apts_gain_XXX_analysed.npz -ls
```
Where file_in is the output of apts_decode.py, directory is where you want to put the output files (suggestion: put it in the same directory of the file_in) and file_calibration is the output of analysis_gain.py


- Finally, to compare all the results run the following script with self-explaining options: results_comparison.py 
