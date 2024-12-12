# DPTS TID Campaign Scripts

The scripts in this folder help to take and analyse data from TID campaigns. 

In particular `run_chip_characterization.py` can be used to run all analyses prior to characterization. `fullcharacterizationana.py` analyses the output from that script automatically. The data taking script is able to utilize a Thorlabs FW102C filter wheel to be able to take source scans as well as the other scans without manual intervention. For the momennt, there is not possibility to run without this device attached.
The file `config_testconf_B30.json` is an example of how a config file for a full characterization could look like.

`interval.py` enables to run a given script in reoccuring intervals.

The scripts `thr_vs_time.py` and `fhr_vs_time.py` can show evolutions of threshold, fake-hit rate and their associates deviations over time. It is run with the outputs from `thresholdana.py`.

Finally, `plot_temperature_logs.py` can plot the temperature logs, which are usually written during irradiation.