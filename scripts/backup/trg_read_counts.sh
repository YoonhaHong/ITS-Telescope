#!/bin/bash

## Read trigger counts
/home/palpidefs/testbeam/TB_August_2024/trigger/software/readtrgincnts.py Rxxx xxxR RxxR -d 0.01 -n1000 | tee trg_rates.txt
