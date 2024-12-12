# ALICE ITS3 WP3 MLR1 DAQ Software

Software to control and readout APTS, CE65 and DPTS chips connected to the MLR1 (rev4) DAQ board via a Proximity card.

## Hardware setup

Full description of the hardware and how to set it up can be found on the [TWiki](https://twiki.cern.ch/twiki/bin/view/ALICE/ITS3WP3MLR1TestSystem). In case you don't have access, a short getting started guide is also available [here](https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-fpga-firmware/-/blob/master/README.md).

## MLR1 DAQ board library installation

Clone the repository:

    git clone https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software.git

Install _libusb_:

- on Debian: `sudo apt install libusb-1.0-0-dev`
- on CentOS: `sudo dnf install libusbx-devel`

and install the python package:

    cd apts-dpts-ce65-daq-software && pip3 install .

### Settings for the USB FX3 and FPGA firmware

change the rules to be able to use FX3 USB:

    cd apts-dpts-ce65-daq-software
    sudo cp etc/fx3.rules /etc/udev/rules.d
    sudo cp etc/87-DAQboard-MLR1.rules /etc/udev/rules.d

reload udev rules

    sudo udevadm control --reload-rules && sudo udevadm trigger

### Look for DAQ boards and test

    mlr1-daq-program --list

### Program FX3 and FPGA firmwares

This needs to be done after every power cycle, the firmwares are not persistent (on purpose).
In case you have not done that yet, download the latest firmwares from: <https://twiki.cern.ch/twiki/bin/view/ALICE/MLR1DAQBoardFirmware>

    mlr1-daq-program --fx3=/path/to/fx3.img --fpga=/path/to/0xXXXXXXXX.bit

Where `0xXXXXXXXX.bit` is latest FPGA firware version available.

## HAMEG installation

Some scripts require HAMEG power supply to run. To use them, clone and install <https://gitlab.cern.ch/alice-its3-wp3/lab-equipment.git> (see respective README).

## Picoscope installation

Most of DPTS scripts rely on Picoscope for readout. Please follow steps in this section to install the needed software. If you are not using testing DPTS chips, you can skip this section.

### Ubuntu (20.04 or 18.04)

Follow the instructions at: <https://www.picotech.com/downloads/linux>.

### RaspberyPi

Download latest PicoLog Cloud package from <https://www.picotech.com/downloads>.
e.g. `wget https://www.picotech.com/download/software/picolog6/sr/picolog-6.2.4-armhf.deb`

Unpack the .deb package and install the necessary libaries:

    dpkg -x picolog-6.2.4-armhf.deb picolog-6.2.4
    cd picolog-6.2.4
    sudo cp opt/PicoLog/resources/libps6000a.so /usr/lib
    sudo ln -s /usr/lib/libps6000a.so /usr/lib/libps6000a.so.2
    sudo cp opt/PicoLog/resources/libpicoipp.so /usr/lib

### Picoscope python wrappers

Once the picoscope drivers are installed, the python wrappers are needed. Clone <https://github.com/picotech/picosdk-python-wrappers> and install (see respective README).

### Udev rules for picoscope

Add

    SUBSYSTEM=="usb", ATTRS{idVendor}=="0ce9", MODE="0666", GROUP="dialout"

to `/etc/udev/rules.d/95-pico.rules` and reload udev rules

    sudo udevadm control --reload-rules && sudo udevadm trigger

___________

## Getting Started

Either run a script from respective directory, e.g.:

    cd apts
    ./apts_readout.py APTS-003

Or, perform test software interactively with python, example: read the FPGA firmware version:

    $ python3
    >>> import mlr1daqboard
    >>> mlr1daqboard.<TAB> # completion of commands with the <TAB> key 
        MLR1daqBoard() APTSDAQBoard() ... 
        write_register() read_fw_version() ...
        read_register()  read_temperature()  ...
        ...              ...
    >>> daq = mlr1daqboard.MLR1DAQBoard()
    >>> print(daq.read_fw_version())

Or, the same with a single shell command:

    python3 -m mlr1daqboard mlr1 read_fw_version
    python3 -m mlr1daqboard dpts --calibration DPTS-001 set_vcasb 250
    python3 -m mlr1daqboard.dpts_decoder FILE

Running Picoscope in standalone mode:

    pico-daq

or

    python3 -m mlr1daqboard.pico_daq

___________

## C++ library

A C++ library is available in `cpp` directory **for expert use only**.

___________

## Known issues

DPTS Shift register reading/writing is correlated with setting VH -> see [issue #19](https://gitlab.cern.ch/alice-its3-wp3/apts-dpts-ce65-daq-software/-/issues/19).
