#!/bin/bash

set -e

### Configure scintillator ###
/home/palpidefs/testbeam/TB_August_2024/trigger/software/mcp4728.py -p /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 CH0_GAIN -v 1.0  # Gain 0.9
/home/palpidefs/testbeam/TB_August_2024/trigger/software/mcp4728.py -p /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 CH0_THR  -v 0.5  # Threshold 0.9
/home/palpidefs/testbeam/TB_August_2024/trigger/software/mcp4728.py -p /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 CH3_GAIN -v 1.1  # Gain 1.1
/home/palpidefs/testbeam/TB_August_2024/trigger/software/mcp4728.py -p /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 CH3_THR  -v 0.1  # Threshold 0.3

### Configure trigger board ###
/home/palpidefs/testbeam/TB_August_2024/trigger/software/settrg.py --port /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 --trg="trg0&trg3&dt_trg>10000&dt_veto>5000&!bsy" --veto='ntrg>0'
#/home/palpidefs/testbeam/TB_August_2024/trigger/software/settrg.py --port /dev/serial/by-id/usb-CERN_ITS3_Trigger_Board_009-if01-port0 --trg="trg0&dt_trg>10000&!bsy"
