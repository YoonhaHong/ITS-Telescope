#!/bin/bash

TB_DIR=TB_July_2024
EOS_DIR=2024-08_PS_Raiser

if [[ `uname -n` != 'pcepaiddtlab5' ]]; then
	echo "You need to run this script from pcepaiddtlab5"
	exit
fi

if [ -z "$1" ]
  then
    echo "No argument supplied."
    echo "Please provide your cern username."
    exit
fi

rsync -avruh --exclude 'labtests' /home/palpidefs/testbeam/$TB_DIR/data ${1}@lxplus.cern.ch:/eos/project/a/aliceits3/ITS3-WP3/Testbeams/$EOS_DIR/
rsync -avruh /home/palpidefs/testbeam/$TB_DIR/eudaq_configs ${1}@lxplus.cern.ch:/eos/project/a/aliceits3/ITS3-WP3/Testbeams/$EOS_DIR/
rsync -avruh /home/palpidefs/testbeam/$TB_DIR/eudaq/user/ITS3/misc/configs ${1}@lxplus.cern.ch:/eos/project/a/aliceits3/ITS3-WP3/Testbeams/$EOS_DIR/eudaq_configs/
rsync -avruh /home/palpidefs/MOSS_TEST_RESULTS ${1}@lxplus.cern.ch:/eos/project/a/aliceits3/ITS3-WP3/Testbeams/$EOS_DIR/
