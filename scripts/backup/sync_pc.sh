#!/bin/bash

TB_DIR=TB_August_2024

if [[ `uname -n` != 'pcepaiddtlab5' ]]; then
	echo "You need to run this script from pcepaiddtlab5"
	exit
fi

rsync -avruh --exclude 'lab_test' /home/palpidefs/testbeam/$TB_DIR/data palpidefs@pcepaiddtlab4:/home/palpidefs/testbeam_august_baby/
rsync -avruh /home/palpidefs/MOSS_TEST_RESULTS palpidefs@pcepaiddtlab4:/home/palpidefs/testbeam_august_baby/
