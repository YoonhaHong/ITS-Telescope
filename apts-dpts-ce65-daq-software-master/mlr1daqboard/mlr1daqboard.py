#!/usr/bin/env python3
"""
DAQ board library for APTS/DPTS/CE65.
MLR1 DAQ board library implements communication between the DAQ board (fpga firmware) and 
host PC through the USB protocol (FX3 chip). The basic functionalities are reading and 
writing values in the registers-modules set in the fpga firmware on DAQ board.
"""
__author__ = "Mauro Aresti"
__maintainer__ = "Mauro Aresti"
__email__ = "mauro.aresti@cern.ch"
__status__ = "Development"
if __name__ == "__main__":
    from _version import __version__
else:
    from ._version import __version__
    
import numpy as np
import struct
import array
import yaml
import usb.core
import usb.backend.libusb1
import logging
import subprocess
import os
import json
from time import sleep
from datetime import datetime

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

DACS_U28 = ['CE_DACA','CE_DACB','CE_NMOS','CE_COL_AP_IBIASN','CE_MAT_AP_IBIAS4SF_DP_IBIASF','CE_VRESET','AP_SEL0','AP_SEL1']
DACS_U29 = ['CE_PMOS_AP_DP_IRESET','AP_IBIASP_DP_IDB','AP_IBIAS4OPA_DP_IBIASN','AP_IBIAS3_DP_IBIAS','CE_VOFFSET_AP_DP_VH','AP_VRESET','AP_VCASP_MUX0_DP_VCASB','AP_VCASN_MUX1_DP_VCASN']
APTS_PIXEL_ADC_MAPPING = [2,1,5,0,4,8,9,12,13,14,10,15,11,7,6,3]
APTS_MUX_PIXEL_ADC_MAPPING = [3,2,1,0,4,8,9,5,12,13,14,15,10,11,6,7]

class MLR1DAQBoard:
    VID=0x1556
    PID=0x01B8
    COMPATIBLE_FW_LIST = ['0x107E7316']
    DAC_REGS = {}
    for i,dac in enumerate(DACS_U28): DAC_REGS[dac] = [0x4,0x1,(0b11<<24)|(i<<20)]
    for i,dac in enumerate(DACS_U29): DAC_REGS[dac] = [0x5,0x1,(0b11<<24)|(i<<20)]

    def __init__(self, calibration=None, serial=None):
        self.dev=None
        name='_'.join(s for s in [serial, calibration] if s)
        if not name: name=self.__class__.__name__
        self.log=logging.getLogger(name)
        self.log.setLevel(logging.DEBUG)
        self.log.info("Initialising MLR1 DAQ Board")
        self.log.debug(get_software_git())
        self.log.debug(get_software_diff())

        self.idacs_cal={'CE_DACA':None,'CE_DACB':None,'CE_NMOS':None,'CE_COL_AP_IBIASN':None,'CE_MAT_AP_IBIAS4SF_DP_IBIASF':None,'CE_PMOS_AP_DP_IRESET':None,'AP_IBIASP_DP_IDB':None,'AP_IBIAS4OPA_DP_IBIASN':None,'AP_IBIAS3_DP_IBIAS':None}
        self.vdacs_cal={'CE_VRESET':None,'AP_SEL0':None,'AP_SEL1':None,'AP_VCASN_MUX1_DP_VCASN':None,'AP_VCASP_MUX0_DP_VCASB':None,'AP_VRESET':None,'CE_VOFFSET_AP_DP_VH':None}
        if calibration is not None:
            if ".json" in calibration:
                calibration_file=calibration
            else:
                calibrations = [f.replace(".json","") for f in os.listdir(__location__+"/calibration")]
                assert calibration in calibrations, f"Calibration '{calibration}' not found. " + \
                    "Available calibrations: " + ", ".join(sorted(calibrations))
                calibration_file=__location__+"/calibration/"+calibration+".json"
            with open(calibration_file) as fcal:
                calib = json.load(fcal)
            self.idacs_cal.update(calib['IDAC'])
            self.vdacs_cal.update(calib['VDAC'])
            self.log.debug(f"Loaded DAC calibration from {calibration_file}: {json.dumps(calib,indent=4)}")

        if serial:
            devs=list(usb.core.find(idVendor=self.VID,idProduct=self.PID,serial_number=serial,find_all=True))
            if not devs:
                raise ValueError('No DAQ board with serial number "%s" found.'%serial)
            if len(devs)>1:
                raise ValueError('More than 1 DAQ board with serial number "%s" were found. Actually %d were found...'%(serial,len(devs)))
            self.dev=devs[0]
        else:
            devs=list(usb.core.find(idVendor=self.VID,idProduct=self.PID,find_all=True))
            if len(devs)>1:
                raise ValueError('More than 1 DAQ boards were found. Actually %d were found... please specify serial number (options are %s)'%(len(devs),', '.join('"%s"'%dev.serial_number for dev in devs)))
            if len(devs)==0:
                raise ValueError('No DAQ board was found.')
            self.dev=devs[0]
        self.log.debug(f"Using DAQ board with serial number {self.dev.serial_number}")

        cfg = self.dev.get_active_configuration() 
        intf = cfg[(0,0)] # usb interface 
        self.ep_in_data = usb.util.find_descriptor(intf, bEndpointAddress=0x83)
        self.ep_in_adc  = usb.util.find_descriptor(intf, bEndpointAddress=0x82)
        self.ep_in_reg  = usb.util.find_descriptor(intf, bEndpointAddress=0x81)
        self.ep_out_reg = usb.util.find_descriptor(intf, bEndpointAddress=0x1)
        for ep in [self.ep_in_data,self.ep_in_adc,self.ep_in_reg]:
            while True: # purge
                try:
                    ep.read(40960,100)
                except usb.core.USBError as e:
                    if e.errno in [60,110]: # TIMEOUT
                        break
                    raise e

        fw = self.read_fw_version()
        assert fw in self.COMPATIBLE_FW_LIST, \
            f"Firmware version {fw} is not compatible with software version {__version__}."
        self.log.debug(f"Firmware version: {fw}")

    def __del__(self):
        if self.dev:
            usb.util.dispose_resources(self.dev)


    def read_register(self, module, register,log_level=logging.DEBUG):
        assert module | 0xF == 0xF
        assert register | 0xFF == 0xFF
        cmd = 1 << 12 | module << 8 | register
        self.ep_out_reg.write(struct.pack('<I', cmd))
        res = self.ep_in_reg.read(8)
        self.log.log(log_level,f"Read cmd 0x{cmd:04x} returned {res.tobytes().hex()}")
        header,val = struct.unpack('<II', res)
        assert header == 0x0, hex(header)
        return val


    def write_register(self, module, register, value,log_level=logging.DEBUG):
        assert module | 0xF == 0xF
        assert register | 0xFF == 0xFF
        assert value | 0xFFFFFFFF == 0xFFFFFFFF
        cmd = 0 << 12 | module << 8 | register
        self.ep_out_reg.write(struct.pack('<I', cmd))
        self.ep_out_reg.write(struct.pack('<I', value))
        res = self.ep_in_reg.read(8)
        self.log.log(log_level,f"Write cmd 0x{cmd:04x} 0x{value:08x} returned {res.tobytes().hex()}")
        header,ack = struct.unpack('<II', res)
        assert header == 0x1, hex(header)
        assert ack == cmd, hex(ack)


    def read_data(self,packet_size, timeout=None):
        data = array.array('B')
        try:
            while(len(data)%512==0 and len(data)!=packet_size):
                data += self.ep_in_data.read(packet_size,timeout)
            return data
        except usb.core.USBError as e:
            if e.errno in [60,110]: # timeout
                if len(data)>0:
                    self.log.fatal(f"Encountered USB Timeout while reading data. Read {len(data)}, requested {packet_size}.")
                    raise e
                return None
            raise e


    def read_config(self,filename):
        """ Read configuration file (*.yaml|*.yml), returns dictionary config  
        Parameters
          filename: configuration file name, type: string 
        Returns
          config: configuration dictionary with the following keys:
            {'module':integer, 'register':integer, 'value':integer, 'priority':integer, 'enable':bool]
            were: 'priority' key is in ascending order from low to high,
            and the 'enable' enables (True) or disables (False) the key
        """
        
        with open(filename, 'r') as file:
            config = yaml.safe_load(file)   
        return config
        

    def set_config(self,config):
        """ set DAQ configuration using config dictionary
        Parameters
          config: configuration dictionary obtained with read_config(), type: dictionary 
        Note:
          configuration dictionary with the following keys:
            {'module':integer, 'register':integer, 'value':integer, 'priority':integer, 'enable':bool]
            were: 'priority' key is in ascending order from low to high,
            and the 'enable' enables (True) or disables (False) the key
        """
        
        lsp = []
        for k in config:
            if not config[k]['priority'] in lsp:
                lsp.append(config[k]['priority'])
                
                self.log.debug("> Configuration Settings:\n Set: mod, reg -> value\n---------------------------------")
                for prio in sorted(lsp):
                    for keys in config:
                        if config[keys]['active'] and config[keys]['priority'] == prio:
                            self.write_register(config[keys]['module'], config[keys]['register'], config[keys]['value'])
                            self.log.debug(" Set: {:2d}, 0x{:02X} -> 0x{:08X} | {:2d}".format(config[keys]['module'], config[keys]['register'], config[keys]['value'], config[keys]['value']))
                            self.log.debug("---------------------------------\n")
                                
                            
    def save_config(self, config, filename):
        """ Save configuration file *.yaml or *.yml
        Parameters
          config:   configuration dictionary obtained with read_config(), type: dictionary 
          filename: configuration file name, type: string 
        """
        
        with open(filename, 'w') as file:
            yaml.dump(config, file)
        self.log.debug("\nConfiguration file saved on {:s} file".format(filename))        
                            

    def set_dac(self, dac, val):
        ''' Sets any DAC directly, val is 16bit DAC value'''
        assert dac in self.DAC_REGS.keys(), f"Uknown DAC {dac}"
        assert val|0xFFFF==0xFFFF, f"DAC value out of range"
        mod,reg,cmd=self.DAC_REGS[dac]
        self.log.debug(f"Setting DAC {dac} to {val}")
        self.write_register(mod,reg,cmd|val<<4)


    def set_vdac(self, dac, val_mV):
        ''' Sets voltage DACs, val_mV is output value in mV'''
        assert dac in self.vdacs_cal.keys(), f"{dac} is not a voltage DAC"
        assert self.vdacs_cal[dac] is not None, f"Calibration not provided for {dac}"
        assert 0<=val_mV<=self.vdacs_cal[dac][2], f"DAC out of range. Max range for {dac}: {self.vdacs_cal[dac][2]:.3f}, requested value {val_mV} mV"
        val = int((val_mV-self.vdacs_cal[dac][1])/self.vdacs_cal[dac][0])
        assert val>=0, f"DAC out of range. Minimum for {dac} is {self.vdacs_cal[dac][1]:.3f} mV"
        self.log.debug(f"Setting DAC {dac} to {(val*self.vdacs_cal[dac][0])+self.vdacs_cal[dac][1]:.3f} mV")
        self.set_dac(dac,val)


    def set_idac(self, dac, val_uA):
        ''' Sets current DACs, val_uA is output value in uA'''
        assert dac in self.idacs_cal.keys(), f"{dac} is not a current DAC"
        assert self.idacs_cal[dac] is not None, f"Calibration not provided for {dac}"
        assert 0 <= val_uA <= self.idacs_cal[dac][2], f"DAC out of range. Max range for {dac}: {self.idacs_cal[dac][2]:.3f}, requested value {val_uA} uA"
        val = int((val_uA-self.idacs_cal[dac][1])/self.idacs_cal[dac][0])
        assert val>=0, f"DAC out of range. Minimum for {dac} is {self.idacs_cal[dac][1]:.3f} uA"
        self.log.debug(f"Setting DAC {dac} to {(val*self.idacs_cal[dac][0])+self.idacs_cal[dac][1]:.3f} uA.")
        self.set_dac(dac,val)


    def proximity_on(self):
        ''' Turn on LDOs on the proximity board'''
        self.log.info(f"Currents before Proximity ON: {self.read_chip_currents()} ")
        self.write_register(14,0x32,0x1) # LDO32 -> ON
        self.write_register(14,0x33,0x1) # LDO33 -> ON
        self.write_register(14,0x12,0x1) # LDO12_EN -> 1 (enable APTS v2 LDOs)
        sleep(0.001)
        self.write_register( 0x04, 0x01, (0x8<<24)|1 ) # set DAC U28 internal reference
        self.write_register( 0x05, 0x01, (0x8<<24)|1 ) # set DAC U29 internal reference
        sleep(0.002)
        self.log.info(f"Currents after Proximity ON: {self.read_chip_currents()} ")


    def proximity_off(self):
        self.log.info(f"Currents before Proximity OFF: {self.read_chip_currents()} ")
        for dac in self.DAC_REGS.keys(): self.set_dac(dac,0) # all dacs to 0
        self.write_register(14,0x12,0x0) # LDO12_EN -> 0 (disable APTS v2 LDOs)
        self.write_register(14,0x32,0x0) # LDO32 -> OFF
        self.write_register(14,0x33,0x0) # LDO33 -> OFF
        sleep(0.3)
        self.log.info(f"Currents after Proximity OFF: {self.read_chip_currents()} ")


    def power_off(self):
        self.proximity_off()
        self.log.info("Chip powered OFF.")


    def get_chip_type(self,verbose=False):
        """ Read jumper position on the board 
        Returns chip detectd APTS, DPTS or CE65 and board id via jumpers
        """
        val = self.read_register(6,0x00)
        chip,board = (val&0xF, (val>>4)&0xF)
        chip_dict = {0xB:'DPTS',0xD:'CE65',0xE:'APTS'}
        chip = chip_dict[chip] if chip in chip_dict else None
        
        if verbose:
            print("o======{ APTS/DPTS/CE65 DAQ Board }======o\n")
            print("> Detected Chip\n------------------")
            if chip == 'APTS':
                print("\033[0;32m I:: APTS <---\033[0;0m")
                print(" :I: CE65 ")
                print(" ::I DPTS ")
            elif chip == 'DPTS':
                print(" I:: APTS ")
                print(" :I: CE65 ")
                print("\033[0;32m ::I DPTS <---\033[0;0m")
            elif chip == 'CE65':
                print(" I:: APTS ")
                print("\033[0;32m :I: CE65 <---\033[0;0m")
                print(" ::I DPTS ")
            else:
                print("\nis the jumper present?")
                print(" I:: APTS ")
                print(" :I: CE65 ")
                print(" ::I DPTS ")
                print("------------------\n")
            print("\n> Board ID: \n------------------\n {}\n".format(board))
            print("> USB Address: \n------------------\n {}\n".format(self.dev.address))
        return chip,board


    def read_temperature(self):
        return (self.read_register(1,3)&0x00000FFF)/139. # TODO temp sensor fine calibration
    
    def read_isenseD(self):
        return 0.03*(self.read_register(1,4)&0x00000FFF)
    
    def read_isenseA(self):
        return 0.0378*((self.read_register(1,3)&0x00FFF000) >> 12)
    
    def read_isenseB(self):
        return 0.0244*(self.read_register(1,3)&0x00000FFF)
    
    def read_chip_currents(self):
        return f"Ia = {self.read_isenseA():0.2f} mA, Id = {self.read_isenseD():0.2f} mA, Ib = {self.read_isenseB():0.2f} mA"

    def read_fw_version(self):
        return f"0x{self.read_register(6,2):08X}"

    def pulse(self, ncycles_high=10000, ncycles_low=10000, npulses=1, wait=False):
        ''' Assert TRG signal, 1 cycle = 10 ns'''
        self.write_register(8,1,ncycles_high)
        self.write_register(8,2,ncycles_low)
        self.write_register(8,3,npulses)
        self.write_register(8,0,1)
        if wait: sleep(npulses*(ncycles_high+ncycles_low)*10e-9+0.001)


class APTSDAQBoard(MLR1DAQBoard):
    def __init__(self, calibration=None, serial=None):
        MLR1DAQBoard.__init__(self, calibration=calibration, serial=serial)
        if calibration is not None:
            self.chip_type = calibration.split('-')[0]

        assert self.get_chip_type()[0]=='APTS', \
            f"Unexpected chip type {self.get_chip_type(verbose=True)[0]}"

    def set_pulse_sel(self,sel0=False,sel1=False):
        ''' Set pulse selection '''
        self.set_vdac('AP_SEL0',1200 if sel0 else 20)
        self.set_vdac('AP_SEL1',1200 if sel1 else 20)

    def set_mux(self,sel):
        ''' Set multiplexer selection '''
        assert sel in range(4), f"Multiplexer selection (sel) must be 0, 1, 2 or 3"
        self.log.info('Setting multiplexer to ' + str(sel))
        self.set_vdac('AP_VCASP_MUX0_DP_VCASB',1200 if sel&1 else 20)
        self.set_vdac('AP_VCASN_MUX1_DP_VCASN',1200 if sel>>1&1 else 20)

    def is_chip_powered(self):
        return self.read_isenseA()>3

    def power_on(self):
        self.log.info("Powering ON the chip with default DAC settings.")
        self.proximity_on()
        
        #Following channels expected for APTS-SF
        if self.chip_type == 'APTS':
            self.log.info("Setting DACs for APTS-SF.")
            self.set_idac('CE_COL_AP_IBIASN',             20) # unit uA
            self.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', 150)
            self.set_idac('CE_PMOS_AP_DP_IRESET',         1)
            self.set_idac('AP_IBIASP_DP_IDB',             2.0)
            self.set_idac('AP_IBIAS3_DP_IBIAS',           200.0)
            self.set_vdac('CE_VOFFSET_AP_DP_VH',          1200) # unit mV
            self.set_vdac('AP_VRESET',                    500)

        #Following channels expected for APTS-OA
        elif self.chip_type == 'OPAMP':
            self.log.info("Setting DACs for APTS-OA.")
            self.set_idac('AP_IBIAS4OPA_DP_IBIASN',       2600)
            self.set_vdac('AP_VCASP_MUX0_DP_VCASB',       270)
            self.set_vdac('AP_VCASN_MUX1_DP_VCASN',       900)
            self.set_idac('CE_COL_AP_IBIASN',             500) # unit uA
            self.set_idac('CE_PMOS_AP_DP_IRESET',         1)
            self.set_idac('AP_IBIASP_DP_IDB',             45)
            self.set_idac('AP_IBIAS3_DP_IBIAS',           850)
            self.set_vdac('CE_VOFFSET_AP_DP_VH',          1200) # unit mV
            self.set_vdac('AP_VRESET',                    400)
        
        else:
            raise ValueError(f'Expected APTS SF or OPAMP calibration file, not {self.chip_type}.')

        self.log.info("Chip powered ON.")
        self.log.info(f"Waiting 9 seconds for Ia current to stabilize...")
        for _ in range(9):
            self.log.info(f"   Ia = {self.read_isenseA():0.2f} mA")
            sleep(1) 
        self.log.info(f"Currents after setting DACs: {self.read_chip_currents()}")

    def set_internal_trigger_mask(self,trg_pixels,mux=False):
        mask = 0x0000 # Disable all pixels for internal trigger
        mapping = APTS_MUX_PIXEL_ADC_MAPPING if mux else APTS_PIXEL_ADC_MAPPING
        if trg_pixels==['inner']:
            pixels=[(1,1),(2,1),(1,2),(2,2)] # Enable internal pixels for internal trigger
        else:
            pixels=trg_pixels
        for coords in pixels:
            mask |= 1 << mapping.index(coords[0]+4*coords[1])
        self.write_register(0x3,0x08,mask) # Overwriting the register

    def configure_readout(self,
            sampling_period=40,
            n_frames_before=100,
            n_frames_after=100,
            trg_thr=1,
            n_frames_auto_trg=2,
            pulse=False,
            trg_type=1,
            pulse_length=10000
        ):
        assert sampling_period>=40 # 6.25 ns units, Max sampling rate 4 MSPs = 40 units
        assert 0<n_frames_before<=100 # max based on Valerio's tests
        assert 0<n_frames_after <=700 # max based on Valerio's tests
        assert 0<n_frames_auto_trg<32
        assert trg_type in [0,1]
        self.log.info("Configuring for readout")
        if pulse and n_frames_after*sampling_period > pulse_length:
            self.log.warning("Pulse length shorter than the acquisition window!")
        if pulse and pulse_length-n_frames_after*sampling_period > 16000:
            self.log.warning("Pulse ending more than 0.1 ms after the acquistion window! Possible interference between consecutive events!")
        self.write_register(0x0,0xEF,0)  # PacketEndWithEachFrame 1:on 0:off
        self.write_register(0x3,0x00,0)  # Switch ADC off (needs to be off when setting sampling period)
        self.write_register(0x3,0x87,0)  # setDebugMode: 0: actual data, 1: test pattern 
        self.write_register(0x3,0x01,sampling_period) 
        self.write_register(0x3,0x02,n_frames_after)
        self.write_register(0x3,0x03,n_frames_before)
        self.write_register(0x3,0x04,1)       # Time between pulse and next sample
        self.write_register(0x3,0x05,pulse_length)   # SetPulseDuration
        self.write_register(0x3,0x06,trg_thr) # Auto trigger threshold (1 bit = 38.1 uV)
        self.write_register(0x3,0x07,n_frames_auto_trg) # num. of frames between samples compared in auto trigger
        self.write_register(0x3,0x08,0xFFFF) # Enable all pixels for internal trigger as default
        self.write_register(0x3,0x09,pulse)     # Enable pulsing (disables triggering)
        self.write_register(0x3,0x0A,not pulse) # WaitForTrigger 0 = acquire immediately, 1 = wait for trigger (int or ext)
        self.write_register(0x3,0x0B,trg_type)  # TriggerType 0:external 1: auto
        self.write_register(0x3,0x0C,1)  # SaveTriggerTimestamps 1:save 0:not save
        self.write_register(0x3,0x0D,10) # TimeBeforeBusy 1 time unit = 10ns
        self.write_register(0x3,0x0E,10) # TriggerOutDuration - 100 ns
        self.write_register(0x3,0x00,1)  # Switch ADC on

    def read_event(self,timeout=1000,format=True):
        self.write_register(3,0xAC,1,log_level=9) # request data
        data = self.read_data(40960,timeout=timeout) # sufficent for up to 1k frames
        if data is None: return None
        tsdata = self.read_data(12,timeout=timeout)
        assert tsdata is not None
        if format: # add headers to the data
            head_data = b'\xaa\xaa\xaa\xaa'+struct.pack('<I',len(data))
            head_ts   = b'\xbb\xbb\xbb\xbb'
            return head_data+data+head_ts+tsdata
        return bytes(data),bytes(tsdata)


class DPTSDAQBoard(MLR1DAQBoard):
    def __init__(self, calibration=None, serial=None):
        MLR1DAQBoard.__init__(self, calibration=calibration, serial=serial)
        assert self.get_chip_type()[0]=='DPTS', \
            f"Unexpected chip type {self.get_chip_type(verbose=True)[0]}"

    def power_on(self):
        self.log.info("Powering ON the chip with default DAC settings.")
        self.proximity_on()
        self.set_dac('CE_MAT_AP_IBIAS4SF_DP_IBIASF',  0)
        self.set_idac('CE_PMOS_AP_DP_IRESET',         10)
        self.set_idac('AP_IBIASP_DP_IDB',             10)
        self.set_idac('AP_IBIAS3_DP_IBIAS',           10)
        self.set_idac('AP_IBIAS4OPA_DP_IBIASN',       10)
        self.set_vdac('CE_VOFFSET_AP_DP_VH',          600)
        self.set_vdac('AP_VCASP_MUX0_DP_VCASB',       300)
        self.set_vdac('AP_VCASN_MUX1_DP_VCASN',       300)
        self.log.info("Chip powered ON.")
        sleep(0.3) # time to stabilize current measurement
        self.log.info(f"Currents after setting DACs: {self.read_chip_currents()} ")

    def is_chip_powered(self):
        return self.read_isenseA()+self.read_isenseD()+self.read_isenseB()>3

    def clear_shreg_fifo(self):
        self.write_register(0x9,0xCF,0x00)
        while self.read_data(60,timeout=100):  # FIXME with new FW
            pass # purge the data already in FX3

    def write_shreg_raw(self,val):
        ''' Write 480 bits to shift register'''
        self.log.debug(f"Writing to shift register:\n0x{val:0120x}")
        self.write_register(0x9,16,0x00) # SEL to low
        for i in range(15): # FW pushes MSB first:
            self.write_register(0x9,i,(val>>32*i)&0xFFFFFFFF)
        self.write_register(0x9,15,0x00) # push

    def write_shreg(self,rs,mc,md,cs,mr,readback=False):
        ''' Format and write to shift register''' 
        self.log.debug(f"SHREG: RS:{rs:08x}|MC:{mc:08x}|MD:{md:08x}|CS:{cs:08x}|MR:{mr:08x}")
        sr = int('{:032b}'.format(mr)[::-1], 2) << 0\
            | int('{:032b}'.format(cs)[::-1], 2) << 32 \
            | md << 32*2 \
            | mc << 32*3 \
            | int('{:032b}'.format(rs)[::-1], 2) << 32*4
        self.log.debug(f"SI  write: "+"|".join(f"{(sr>>32*i)&0xFFFFFFFF:08x}" for i in range(4,-1,-1)))
        srt = 0 # triplicate
        for i in range(160): srt |= (((sr>>i)&1)<<(3*i))|(((sr>>i)&1)<<(3*i+1))|(((sr>>i)&1)<<(3*i+2))
        self.write_shreg_raw(srt)
        if readback:
            return sr,self.read_shreg()
        return sr
    
    def read_shreg(self, decode=True, timeout=1000):
        self.write_register(9,51,1) # let fx3 pull last shreg output from fpga fifo
        data = self.read_data(60,timeout=timeout)
        if data is None: return None
        data = bytes(data)
        assert len(data)==60, f"Unexpected data length {len(data)}. Data: {data.hex()}"
        self.log.debug(f"Reading from shift register:\n0x{data.hex()}")
        d = np.frombuffer(data,dtype='<u4')
        b = 0
        for i in range(15):
            for j in range(32):
                b |= int((d[i]>>(31-j))&1)<<(32*i+j)
        if decode:
            d = [0,0,0]
            for j in range(0,480,3):
                for i in range(3):
                    d[i] |= (b>>(j+i)&1)<<(j//3)
            for i in range(3):
                self.log.debug(f"SOx{i} read: "+"|".join(f"{(d[i]>>32*j)&0xFFFFFFFF:08x}" for j in range(4,-1,-1)))
            return d
        else:
            return b
            
    def set_ibiasf(self, val_uA):
        self.set_idac('CE_MAT_AP_IBIAS4SF_DP_IBIASF', val_uA)
        
    def set_ireset(self, val_uA):
        self.set_idac('CE_PMOS_AP_DP_IRESET',         val_uA)

    def set_idb(self, val_uA):
        self.set_idac('AP_IBIASP_DP_IDB',             val_uA)

    def set_ibias(self, val_uA):
        self.set_idac('AP_IBIAS3_DP_IBIAS',           val_uA)
        
    def set_ibiasn(self, val_uA):
        self.set_idac('AP_IBIAS4OPA_DP_IBIASN',       val_uA)
        
    def set_vh(self, val_mV):
        self.set_vdac('CE_VOFFSET_AP_DP_VH',    val_mV)

    def set_vcasb(self, val_mV):
        self.set_vdac('AP_VCASP_MUX0_DP_VCASB', val_mV)
        
    def set_vcasn(self, val_mV):
        self.set_vdac('AP_VCASN_MUX1_DP_VCASN', val_mV)

    def set_dacs(self, args, vh=False, level=logging.INFO):
        ''' Chip biases are expected in frontend values (e.g. IRESET in pA, IBIAS in nA)'''
        self.set_vcasb(args.vcasb)
        self.set_vcasn(args.vcasn)
        self.set_ireset(args.ireset)
        self.set_idb(args.idb/10)
        self.set_ibias(args.ibias/10)
        self.set_ibiasn(args.ibiasn)
        if args.ibiasf==0:
            self.set_dac('CE_MAT_AP_IBIAS4SF_DP_IBIASF',  0)
        else:
            self.set_ibiasf(args.ibiasf*1000)
        if vh:
            self.set_vh(args.vh)
        sleep(0.3)
        logging.log(level, f"VCASB  = {args.vcasb} mV")
        logging.log(level, f"VCASN  = {args.vcasn} mV")
        logging.log(level, f"IRESET = {args.ireset} pA")
        logging.log(level, f"IDB    = {args.idb} nA")
        logging.log(level, f"IBIAS  = {args.ibias} nA")
        logging.log(level, f"IBIASN = {args.ibiasn} nA")
        logging.log(level, f"IBIASF = {args.ibiasf} mA")
        if vh:
            logging.log(level, f"VH     = {args.vh} mV")

class CE65DAQBoard(MLR1DAQBoard):
    # This is for now just a placeholder class.
    # TODO calibration
    def __init__(self, calibration=None, serial=None):
        MLR1DAQBoard.__init__(self, calibration=calibration, serial=serial)
        assert self.get_chip_type()[0]=='CE65', \
            f"Unexpected chip type {self.get_chip_type(verbose=True)[0]}"

    def power_on(self):
        raise NotImplementedError # TODO

    def configure_readout(self):
        self.log.debug("> CE65 Configure readout")
        self.write_register(0x10,0xCF,1)  # CleanFifo
        self.write_register(0x10,0xAC,0)  # ResetSMs
        self.write_register(0x10,0x00,1536)  # SetPixelNumber 
        self.write_register(0x10,0x01,3) # SetFramesBeforeTrigger max 31
        self.write_register(0x10,0x02,5) # SetFramesAfterTrigger
        self.write_register(0x00,0xEF,1) # SetPacketEndWithEachFrame 1: only at the end  0: each frame
        self.write_register(0x10,0x0A,0) #  WaitForTrigger 0 = acquire immediately, 1 = wait for trigger (int or ext)
        self.write_register(0x10,0x87,1) # SetDebugMode
        self.write_register(0x10,0x07,16) # SetDataPhase 
        self.write_register(0x02,0xFF,0x6E1) # ResetADC
        self.write_register(0x02,0xFF,0x6D00) # SetInternalReference
        self.write_register(0x02,0xFF,0x6308) # SetDataFormat: # 0x6308 = offset binary, 0x6300 = 2s complement 

    def read_event(self,timeout=-1):
        # TODO make similar to APTS readout
        self.write_register(10,0xac,1) # acquire (waits for trigger if reg )
        datalist = []
        for i in range(1000):
            data = self.read_data(8192,timeout=timeout)
            datalist.append(data)
            self.log.debug("{:06d} | {:04X} {:04X} {:04X} {:04X} {:04X} {:04X} ... {:04X} {:04X} {:04X} {:04X} {:04X} {:04X} | {:06d}".format(i,data[0],data[1],data[2],data[3],data[4],data[5],data[-6],data[-5],data[-4],data[-3],data[-2],data[-1],data.size))
            self.write_register(10,0xac,0) # stop    
            if f'{data[-1]:04X}' == 'AEAE':
                break  
        return datalist


def get_software_git():
    try:
        return subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=__location__,stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError:
        with open(os.path.join(__location__,'git_hash')) as f:
            git_hash=f.read().strip()
        return f"v{__version__} - {__location__} is not a git repository but an installation directory. Git hash at installation: {git_hash}"


def get_software_diff():
    try:
        return subprocess.check_output(
            ['git','diff'],cwd=__location__,stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        st = os.stat(__file__)
        with open(os.path.join(__location__,'git_diff')) as f:
            git_diff=f.read().strip()
        return \
            f"File {__file__} installed in {__location__} v{__version__}:\n" +\
            f"Created:  {datetime.utcfromtimestamp(st.st_ctime)} UTC\n" +\
            f"Accessed: {datetime.utcfromtimestamp(st.st_atime)} UTC\n" +\
            f"Modified: {datetime.utcfromtimestamp(st.st_mtime)} UTC\n" +\
            f"Size:     {st.st_size}\n"+\
            f"git diff at installation:\n{git_diff}"

def main():
    import fire
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s')
    fire.Fire({"mlr1":MLR1DAQBoard,"apts":APTSDAQBoard,"dpts":DPTSDAQBoard})


if __name__ == '__main__':
    main()
