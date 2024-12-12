#!/usr/bin/env python3
"""
SCOPE board library for APTS OPAMP.
OPAMP scope library implements communication between different models of scope (LeCroy and Keysight) and
host PC through the TPC protocol.
"""
__author__ = "Umberto Savino, Roberto Russo, Arianna Grisel Torres Ramos"
__maintainer__ = "Umberto Savino, Roberto Russo, Arianna Grisel Torres Ramos"
__email__ = "Umberto Savino, Roberto Russo, Arianna Grisel Torres Ramos"
__status__ = "Development"

import pyvisa
from pyvisa.resources import MessageBasedResource
import re
import numpy as np
import time
from datetime import datetime
import logging
import os
# Rhode
import RsInstrument  # The RsInstrument package is hosted on pypi.org, see Readme.txt for more details
from RsInstrument import *


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

class OPAMPscope:

    def __init__(self):
        name = self.__class__.__name__

        self.log=logging.getLogger(name)
        self.log.setLevel(logging.DEBUG)

        # inizializing variables common to all classes
        self.number_of_points = None # number of acquired points per saved waveform        
        self._dx = None # x axis increment unit (= time step)
        self._x0 = None # x axis origin
        self._dy = [None, None, None, None] # y axis increment unit (= voltage step)
        self._y0 = [None, None, None, None] # y axis origin (= offset)
        self._query_flags = [False, False, False, False] # query dx, x0, dy, y0 only once in the entire acquisition process
        self.data = [None, None, None, None] # the waveform binary data for each scope channel
        self.n_segment_scope_sequence = None # number of segments in the scope sequence

    # list of all methods that all the children classes should contain
    def configure(self, data_format, channels_termination, 
                             vdiv, tdiv, 
                             sampling_period_s, window_delay_s, trg_delay_s):
        raise NotImplementedError
    def set_offset(self,search,
                  channels_offset):
        raise NotImplementedError
    def set_trigger(self,trigger_on_channel,
                    baseline, 
                    slope, relative_trigger_level_volt):
        raise NotImplementedError
    def arm_trigger(self,force):
        raise NotImplementedError
    def is_ready(self):
        raise NotImplementedError
    def readout(self,debug_mode):
        raise NotImplementedError
    def set_trigger_sweep(self,mode):
        raise NotImplementedError
    def clear(self):
        raise NotImplementedError

    def get_waveform_axis_variables(self):
        return self._dx, self._x0, self._dy, self._y0

    def clear_waveform_axis_variables(self):
        self._query_flags = [False, False, False, False]
        self._dx = None
        self._x0 = None
        self._dy = [None, None, None, None]
        self._y0 = [None, None, None, None]

class WaveMaster(OPAMPscope):
    rm = pyvisa.ResourceManager()
    _X0_DIVISION = -5 # number of time divisions used to extract the zero of x axis
    TIME_DIVISION = 10 # total number of time divisions
    VOLTAGE_DIVISION = 8 # total number of voltage divisions
    _DY_ADC_CONVERSION = 0.03125 # V/ADC-units conversion factor from scope ADC to V. It comes from [vdiv*divisions/bits]=[vdiv*8/256]
    _MIN_SIGNAL = 0.001 # V minimum value of amplitude used to verify the presence of a signal (baseline)
    _V_DIVISION = 6 # number of Volt divisions used to scan y axis looking for a signal
    _SHIFT_DIVISION = 2.5 # number of Volt divisions used to set the offset with respect to the signal position
    _MAX_OFFSET = -1 # V maximum offset befor exiting the loop
    _MAX_SAMPLING_RATE = 40E9 # samples/s of maximum sampling rate
    _MIN_MEMORY_SIZE = 500 # minumum memory size

    def __init__(self,address='10.0.0.11',timeout_sec=30,active_channels=[1, 2, 3, 4]):
        OPAMPscope.__init__(self)

        self.scope = self.rm.open_resource(f'TCPIP0::{address}::inst0::INSTR', resource_pyclass=MessageBasedResource)
        self.log.info("Opening communication with " + self.scope.query("*IDN?"))

        visa_logger = logging.getLogger('pyvisa')
        visa_logger.setLevel(logging.WARNING)
        
        self.scope.timeout = timeout_sec*1000
        self.scope.channels = active_channels  # scope channels to be used
        assert 1<=len(active_channels)<=4, "active_channels is expected to be a list like [1,2,3,4] or smaller"
        self.scope.clear()

        # Keep/Remove comm header from self.scope answers
        self.scope.write("CHDR ON")
        # Initializing variables
        self.trg_time = None # trigger time (no date)
        self.vdiv = None # makes voltage division tuple available for all methods

    def __del__(self):
        # method to correcly close the connection to the scope.
        self.scope.close()
        self.rm.close()
        self.log.info("Communication closed. Scope I hate you scope.")


    def configure(self, data_format=None, channels_termination=(50, 50, 50, 50), 
                             vdiv=(0.020, 0.020, 0.020, 0.020), tdiv=5E-9, 
                             sampling_period_s=0.025E-9, window_delay_s=10E-9, trg_delay_s=0E-9):
        if data_format is not None:
            self.log.warning("data_format argument not used in WaveMaster class.")
        
        
        assert float(window_delay_s) <= self.TIME_DIVISION/2*float(tdiv), f'Error: maximum delay = {self.TIME_DIVISION/2*float(tdiv)}'

        ################################################################################
        # turning off the display
        self.scope.write("DISP OFF")
        # From Maui Manual:
        # When remotely controlling the oscilloscope, and if you do not need to use the display, 
        # it can be useful to switch off the display via the DISPLAY OFF command.
        # This improves oscilloscope response time, since the waveform graphic generation procedure is suppressed.
        
        # reset the setup
        self.log.info("Reset. Setting all traces to the GND line and recalling the factory default panel setup, with the trigger in STOP mode.")
        self.scope.write("*RST")
        # removing command header
        self.scope.write("CHDR OFF")
        self.log.debug("Setting command header to "+self.scope.query("CHDR?"))
        # get maximum memory size and divide based on the maximum sampling rate
        memory_size=float(self.scope.query("MSIZ?"))/(self._MAX_SAMPLING_RATE*sampling_period_s)
        
        self.scope.write(f"MSIZ {memory_size}")
        self.log.info("The memory size set is "+self.scope.query("MSIZ?"))

        # set quadgrid
        self.scope.write("GRID QUATTRO")
        self.log.info("Scope grid set to "+self.scope.query("GRID?"))
        # associate channels
        for ch in self.scope.channels:
            self.log.info(f"setting trace of c{ch} to ON")
            self.scope.write(f"C{ch}:TRACE ON")
            self.log.info(f"Trace of CH{ch} is "+self.scope.query(f"C{ch}:TRACE?"))
        # setting Input A on channels
        for ch in self.scope.channels:
            self.scope.write(fr"""vbs 'app.Acquisition.C{ch}.ActiveInput = "InputA"' """)
            self.log.info(f"Setting on channel {ch} "+self.scope.query(fr"""vbs? 'return=app.Acquisition.C{ch}.ActiveInput' """).split()[-1])
        # set termination
        for ch,cht in zip(self.scope.channels, channels_termination):
            self.log.info(f'setting to C{ch} the termination {cht}')
            self.scope.write(f"C{ch}:CPL D{cht}")
            self.log.info(f"Setting channel {ch} to "+self.scope.query(f"C{ch}:CPL?")+" termination.")
        # set bandwidth limit OFF
        self.scope.write("BWL OFF")
        self.log.info("The bandwidth limit is "+self.scope.query("BWL?"))
        # set attenuation factor to 1
        for ch in self.scope.channels:
            self.scope.write(f"C{ch}:ATTN 1")
            self.log.info(f"The attenuation factor of CH{ch} is "+self.scope.query(f"C{ch}:ATTN?")) 
        # select trigger type: TRIG_SELECT <trig_type>,SR,<source>[,QL,<source>,HT,<hold_type>,HV,<hold_value>,HV2,<hold value>]
        self.scope.write("TRIG_SELECT PA,SR,C1")
        self.log.info("The selected trigger is "+self.scope.query("TRIG_SELECT?"))
        
        self.vdiv = vdiv

        for ch, n_vdiv in zip(self.scope.channels, self.vdiv):
            # set the vertical scale of all the CHs
            self.scope.write(f"C{ch}:VDIV {n_vdiv*1000}mV")
            vertical_scale = self.scope.query(f"C{ch}:VDIV?")
            self.log.info(f"Ch.{ch} vertical scale = {vertical_scale}")
            assert float(vertical_scale)==n_vdiv, "Voltage division is not properly set."

            # set the time scale
            self.scope.write(f"TDIV {tdiv}")
            time_division=self.scope.query("TDIV?")
            self.log.info(f"Ch.{ch} horizontal scale = {time_division}")
            assert float(time_division)==tdiv, "Time division is not properly set."
            # set trigger delay
            self.scope.write(f"TRDL {trg_delay_s}")
            self.log.info(f"The trg delay is set at: "+self.scope.query("TRDL?"))

        ################################################################################
        # SCOPE GENERAL SETTINGS
        # Sampling interval in ns (normally: 25 ps @ 40 GS/s => sampling_period_s = 0.025 ns)
        #   for tests with 1 kHz square wave: 4 ns @ 250 MS/s
        self.sampling_period_s = sampling_period_s 
        sparsification = 1
        # if the minimum memory size is reached, the sparsification coefficient will be used, based on the wanted sampling rate
        if memory_size < self._MIN_MEMORY_SIZE:
            sparsification = int(round(self._MIN_MEMORY_SIZE/memory_size,0))
            self.log.info(f"Minum memory size set, using sparsification parameter = {sparsification}")
        # Number of points for "waveform"
        self.number_of_points = self.TIME_DIVISION*tdiv/sampling_period_s
        # compute the first datapoint for the finely sampled 'waveform'
        # using the trigger time position from the beginning of the waveform (window_delay_s)
        first_point = int(window_delay_s / sampling_period_s) - (self.number_of_points/2)
        self.log.debug("First data point (waveform) = "+str(first_point)+"\n")

        # Limit the number of data points acquired from the waveform:
        #   SP = sparsing parameter;
        #   NP = max. n. of data points;
        #   FP = first data point (counting from 0);
        #   SN = segment number
        for ch in self.scope.channels:
            self.scope.write(f"C{ch}"+":WFSU SP,"+str(sparsification)+",NP,"+str(self.number_of_points)+",FP,"+str(first_point)+",SN,0")
        
        self.log.info("Waveform setup is "+self.scope.query("WFSU?"))

    def set_offset(self,search=True,channels_offset=(300E-3, 300E-3, 300E-3, 300E-3)):
        # Method to set up the offset for each channel to allow correct waveform capture
        if search is False:
            for ch, n_offset in zip(self.scope.channels,channels_offset):
                self.scope.write(f"C{ch}:OFFSET "+str(-n_offset))
                self.log.info(f"The offset of CH{ch} is {n_offset} V")
            return
        self.log.info("Scanning the V scale looking for the signal.")
        for ch,n_vdiv in zip(self.scope.channels,self.vdiv):
            # define the parameters P1 that measure the baseline of CH1
            self.scope.write(f"PACU 1,MEAN,C{ch}")
            # define the parameters P2 that measure the amplitude of CH1
            self.scope.write(f"PACU 2,AMPL,C{ch}")
            # set the offset for CH1

            signal_amplitude = self.scope.query(r"""vbs? 'return=app.measure.p2.out.result.value' """)
            iteration = 0
            print(f"Check: {signal_amplitude}")
            while 'No Data Available' in signal_amplitude:
                self.log.debug("function failed to find the signal_amplitude. No Data Available returned.")
                self.scope.write("TRMD AUTO")
                time.sleep(1)
                self.scope.write("TRMD STOP")
                signal_amplitude = self.scope.query(r"""vbs? 'return=app.measure.p2.out.result.value' """)
                iteration+=1
                assert iteration < 5, "Scope cannot return the value of P2. No Data Available returned after 5 iterations."

            self.log.info(f"Searching for a signal in the scope channel {ch}")
            initial_offset = 0
            while float(signal_amplitude) < self._MIN_SIGNAL:
                self.log.debug(f"Inizial offset: {initial_offset}")
                self.scope.write(f"C{ch}:OFFSET "+str(initial_offset))
                initial_offset = initial_offset - n_vdiv*self._V_DIVISION
                self.scope.write("TRMD AUTO")
                trg_mode = self.scope.query("TRMD?")
                self.log.debug("New Trigger mode = " + trg_mode)

                time.sleep(1.3)

                self.scope.write("TRMD NORM")
                trg_mode = self.scope.query("TRMD?")
                self.log.debug("New Trigger mode = " + trg_mode)
                signal_amplitude = self.scope.query(
                    r"""vbs? 'return=app.measure.p2.out.result.value' """).split()[-1]
                assert initial_offset > self._MAX_OFFSET, "set_offset() failed to find a signal."

            self.log.info(f"A signal was found with an amplitude of {signal_amplitude}")
            
            baseline = self.scope.query(
                r"""vbs? 'return=app.measure.p1.out.result.value' """).split()[-1]

            shifting = n_vdiv*self._SHIFT_DIVISION
            offst = shifting - float(baseline)
            
            self.scope.write(f"C{ch}:OFFSET "+str(offst))

            self.log.info(f"The offset of CH{ch} is {offst} V")


    def set_trigger(self, trigger_on_channel=(True, True, True, True), 
                    baseline=None, 
                    slope="L", relative_trigger_level_volt=-0.01):
        if baseline is not None:
            self.log.warning("baseline tuple is not used in WaveMaster class.")
        # Set trigger states of the channels (H=high; L=low; X=don't care)
        ch_state = [slope if ch else "X" for ch in trigger_on_channel]

        # set the trigger pattern to trigger when either of the selected channels are triggering (OR logic)
        self.scope.write(
            f"TRPA C1,{ch_state[0]},C2,{ch_state[1]},C3,{ch_state[2]},C4,{ch_state[3]},EX,H,STATE,OR")

        # set the level of the external trg in V. DEPENDS ON TRIGGER BOARD
        self.scope.write("EX:TRLV 1.25V")

        self.log.info(f"External trigger level is: "+self.scope.query("EX:TRLV?"))
        for n_ch in self.scope.channels:

            # Set the trigger position relative to the baseline position
            self.scope.write(f"PACU 1,MEAN,C{n_ch}")
            self.scope.write(f"PACU 2,AMPL,C{n_ch}")

            self.scope.write("TRMD AUTO")
            time.sleep(1)
            self.scope.write("TRMD NORM")

            signal_amplitude = self.scope.query(
                r"""vbs? 'return=app.measure.p2.out.result.value' """).split()[-1]

            self.log.info(f"A signal was found with an amplitude of {signal_amplitude}")

            # read the position of the Baseline and set (by default) the trg 10 mV below (relativeposition = -0.01V)
            assert float(signal_amplitude) > self._MIN_SIGNAL, "Faild to find a signal. Check back the offset procedure"

            level = self.scope.query(
                r"""vbs? 'return=app.measure.p1.out.result.value' """).split()[-1]

            self.log.debug(f"The signal baseline is set to {level} V")

            trg = float(level) + relative_trigger_level_volt
            self.log.debug("trg level position is: "+str(trg))

            # set the level of the trg in V
            self.scope.write(f"C{n_ch}:TRLV {trg}")
            self.log.info(f"C{n_ch} trigger level is: "+self.scope.query(f"C{n_ch}:TRLV?"))

    def arm_trigger(self, force=False):
        # prepare the oscilloscope for triggering
        # method to catch a SINGLE waveform on the scope

        if force:
            self.scope.write("TRMD NORM")
            self.scope.write("FRTR") # forces the scope to make one trigger
            self.log.debug("Scope forced the acquisition of a signal")
            return
        
        self.scope.write("TRMD SINGLE")
        # wait for the Trigger mode Single to be set
        opc_value = None
        while opc_value != "1":
            opc_value = self.scope.query("*OPC?").split()[-1].strip()  # 0, 1
            self.log.debug(f"check: opc_value {opc_value}")  # check: value 1
            time.sleep(0.01)

    def is_ready(self):
        # Is the scope stopped such that it is ready to be readout?
        return self.scope.query("TRMD?") == "STOP\n"


    def readout(self,debug_mode=False):
        self.log.debug("START readout\n")

        if debug_mode:
            self.log.debug("VERTICAL_GAIN: "+self.scope.query("C4:INSPECT? VERTICAL_GAIN"))
            self.log.debug(f"The wave array from Channel 4 is: "+self.scope.query("C4:INSPECT? WAVE_ARRAY_1"))
        # TRIGGER_TIME       : Date = APR 27, 2022, Time = 17: 1:31.945696300
        self.trg_time = self.scope.query("C4:INSPECT? TRIGGER_TIME")
        self.log.debug("TRIGGER_TIME: "+self.trg_time)
        # Loop on the 4 channels
        for j in range(len(self.scope.channels)):
            self.log.debug(f"reading channel C{j+1}")
            self.scope.write(f"C{str(j+1)}:WF? DAT1")
            self.data[j] = self.scope.read_raw() # save the data as byte format
            # query dx, x0, dy, y0 only once in the entire acquisition process
            if not self._query_flags[j]:
                if (self._dx is None) and (self._x0 is None): # since x axis is common for all channels, is queried just once
                    self._dx = float(self.sampling_period_s) # sampling rate
                    self._x0 = float(self._X0_DIVISION*float(self.scope.query("TDIV?")) + float(self.scope.query("TRDL?"))) # starting point of time sampling (5 division before trdl)
                self._dy[j] = float(self.scope.query(f"C{j+1}:VDIV?"))*self._DY_ADC_CONVERSION
                self._y0[j] = -float(self.scope.query(f"C{j+1}:OFFSET?"))
                self._query_flags[j] = True
        self.log.debug("Scope has captured a waveform\n")
        return self.data 

    def get_trg_time(self,parse):
        if parse:
            return re.search(r'(?<=Time = )\s*\d+:\s*\d+:\s*\d+\.\d+', self.trg_time).group(0)
        else:
            return self.trg_time


    def scope_histos_readout(self):
        # under development
        self.scope.write("CHDR OFF")
        # Reading the mean value (P2) and rms (P3) of the baseline
        baseline = self.scope.query(
            r"""vbs? 'return=app.measure.p2.out.result.value' """).split()[-1]
        err_baseline = self.scope.query(
            r"""vbs? 'return=app.measure.p3.out.result.value' """).split()[-1]
        # Reading the mean value (P5) and rms (P6) of the falltime
        falltime = self.scope.query(
            r"""vbs? 'return=app.measure.p5.out.result.value' """).split()[-1]
        err_falltime = self.scope.query(
            r"""vbs? 'return=app.measure.p6.out.result.value' """).split()[-1]
        # Reading the mean value (P8) and rms (P9) of the amplitude
        amplitude = self.scope.query(
            r"""vbs? 'return=app.measure.p8.out.result.value' """).split()[-1]
        err_amplitude = self.scope.query(
            r"""vbs? 'return=app.measure.p9.out.result.value' """).split()[-1]

        return baseline, err_baseline, amplitude, err_amplitude, falltime, err_falltime

    def set_trigger_sweep(self, mode="AUTO"):
        assert mode in ["AUTO", "NORM", "SINGLE","STOP"]
        self.scope.write("TRMD {mode}")
        trg_mode = self.scope.query("TRMD?")
        self.log.debug(f"trigger mode: {trg_mode}")

    def clear(self):
        self.log.info("Clearing scope registers and query variables\n")
        self.scope.clear()
        self.data = [None, None, None ,None]
        self.clear_waveform_axis_variables()
    
    def set_auxiliary_output(self,mode):
        self.scope.write(fr"""vbs 'app.Acquisition.AuxOutput.Mode = "{mode}"' """)
        self.log.info("Auxiliary OUTput mode set to "+self.scope.query(r"""vbs? 'return=app.Acquisition.AuxOutput.Mode' """).split()[-1])

    def set_sequence_mode(self, nseg, timeout_enable, sequence_timeout):
        self.n_segment_scope_sequence=nseg
        self.scope.write(f"SEQ ON,{nseg},2.5E+6")
        self.log.info(f"Sequence set with {nseg} segments.")
        # setting sequence timeout - once reached it will transfer data even if the sequence is not fully filled
        self.scope.write(fr"""vbs 'app.Acquisition.Horizontal.SequenceTimeoutEnable = {timeout_enable}' """)
        self.log.info("SequenceTimeoutEnable (-1: on, 0: off): "+self.scope.query(r"""vbs? 'return=app.Acquisition.Horizontal.SequenceTimeoutEnable' """).split()[-1])
        if timeout_enable:        
            self.scope.write(fr"""vbs 'app.Acquisition.Horizontal.SequenceTimeoutEnable = {sequence_timeout}' """)
            self.log.debug("Sequence timeout set as "+self.scope.query(r"""vbs? 'return=app.Acquisition.Horizontal.SequenceTimeoutEnable' """).split()[-1])
    
    def get_trigger_mode(self):
        return self.scope.query("TRMD?")

class Infiniium(OPAMPscope):
    rm = pyvisa.ResourceManager()
    TIME_DIVISION = 10 # total number of time divisions
    VOLTAGE_DIVISION = 8 # total number of voltage divisions
    _EDGE_DICT = {'RISing': 'POSitive', 'FALLing': 'NEGative', 'EITHer': 'EITHer'} # nomenclature used to set trigger condition on multiple edges (keys) or single edges (values)

    def __init__(self, address='192.168.1.13', timeout_sec=25, active_channels=[1, 2, 3, 4]):
        OPAMPscope.__init__(self)

        self.scope = self.rm.open_resource(f'TCPIP0::{address}::inst0::INSTR', resource_pyclass=MessageBasedResource)
        self.log.info("Opening communication with " + self.scope.query("*IDN?"))

        visa_logger = logging.getLogger('pyvisa')
        visa_logger.setLevel(logging.WARNING)

        self.scope.timeout = timeout_sec*1000
        self.scope.channels = active_channels  # scope channels to be used
        assert 1<=len(active_channels)<=4, "active_channels is expected to be a list like [1,2,3,4] or smaller"
        self.scope.clear()
        self.scope.read_termination = '\n'
        self.scope.write_termination = '\n'

        # Initializing variables to record waveform for each channel and the flag variable to know when to query x and y axis origin and increment
        self._data_format = None # byte precision of acquired waveform. It can be BYTE (1 byte) or WORD (2 bytes, 10 bit effective)


    def __del__(self):
        # method to correcly close the connection to the scope.
        self.scope.close()
        self.rm.close()
        self.log.info("Communication closed. Scope I hate you scope.")


    def configure(self, data_format="BYTE", channels_termination=("DC50", "DC50", "DC50", "DC50"),
                             vdiv=(20E-3, 20E-3, 20E-3, 20E-3), tdiv=5E-9, 
                             sampling_period_s=0.0625E-9, window_delay_s=None, trg_delay_s=0E-9):
        if window_delay_s is not None:
            self.log.warning("window_delay_s arguments not used in Infiniium class.")
        ################################################################################
        #SCOPE GENERAL SETTINGS
        # Sampling interval in ns (normally: 62.5 ps @ 16 GSa/s => sampling_period_s = 0.0625 ns)
        #   for tests with 1 kHz square wave: 4 ns @ 250 MSa/s
        # configure scope general settings
        assert data_format in ['BYTE', 'WORD']
        self._data_format = data_format
        self.scope.write(f":WAVeform:FORMat {self._data_format}")  # scope output datatype
        if self._data_format == "WORD":
            self.scope.write(':WAVeform:BYTeorder LSBFirst') # MSBF is default, must be overridden for WORD to work
        self.scope.write(":WAVeform:STReaming ON") # allows more than 999,999,999 bytes of data to be transfered to a PC when using the :WAVeform:DATA? query
        self.scope.write(":SYSTem:HEADer OFF")  # query headers off
        self.scope.write(":ACQuire:INTerpolate OFF")  # turns off the sin(x)/x interpolation filter
        if sampling_period_s is None:
            self.scope.write(":ACQuire:SRATe:ANALog:AUTO ON")   # use the auto analog scope sampling rate
            self.scope.write(":ACQuire:SRATe:DIGital:AUTO ON")  # use the auto digital scope sampling rate
        else:
            self.scope.write(":ACQuire:SRATe:ANALog:AUTO OFF")   # manually set analog scope sampling rate
            self.scope.write(f":ACQuire:SRATe:ANALog {1/sampling_period_s}")
            self.scope.write(":ACQuire:SRATe:DIGital:AUTO OFF")  # manually set auto digital scope sampling rate
            self.scope.write(f":ACQuire:SRATe:DIGital {1/sampling_period_s}")
        sampling_frequency = float(self.scope.query(":ACQuire:SRATe?"))
        self.sampling_period_s = 1/sampling_frequency  # sampling period - time interval between sampled points
        self.log.debug(f"Sampling period: {self.sampling_period_s*1E9} ns")
        self.number_of_points = int(np.rint(self.TIME_DIVISION*tdiv/sampling_period_s))  # memory depth - number of acquired points per waveform (made such that only points displayed on the screen are saved)
        self.scope.write(f":ACQuire:POINts {self.number_of_points}")  # if the sampling rate is AUTO, it may be limited depending on the time per division
        self.log.debug(f"Memory depth: {self.number_of_points} points")
        for inpt in channels_termination:
            assert inpt in ['DC50', 'DC']  # 50 ohm or 1 Mohm input impedance
        # set the vertical scales for all the CHs
        for ch in self.scope.channels:
            self.scope.write(f":CHANnel{ch}:DISPlay ON")  # enable the channel on the display
            self.scope.write(f":CHANnel{ch}:INPut {channels_termination[int(ch)-1]}")  # set the input impedance to 50 ohm
            self.scope.write(f":CHANnel{ch}:SCALe {vdiv[int(ch)-1]}")
            self.log.info(f"Ch.{ch} vertical scale = "+self.scope.query(f":CHANnel{ch}:SCALe?")+" V")
            self.scope.write(f":CHANnel{ch}:ISIM:BANDwidth 4E9")  # set the channel bandwidth to 4 GHz
            self.log.debug(f"Ch.{ch} bandwidth = "+self.scope.query(f":CHANnel{ch}:ISIM:BANDwidth?")+" Hz")

        # set the time scale for the four channels (it is not possible to set different time scales for different channels)
        self.scope.write(f":TIMebase:SCALe {tdiv}")
        self.log.info(f"Horizontal scale = "+self.scope.query(":TIMebase:SCALe?")+" s")
        # set the time offset for the four channels (it is not possible to set different time offsets for different channels)
        self.scope.write(f":TIMebase:POSition {trg_delay_s}")
        self.log.debug(f"Horizontal offset = "+self.scope.query(":TIMebase:POSition?")+" s")
        self.log.info("Configured.")


    def set_offset(self, search=False, channels_offset=(300E-3, 300E-3, 300E-3, 300E-3)):
        # Method to set up the offset for each channel to allow correct waveform capture
        # The offset is the middle voltage level on the screen
        if search is not False:
            self.log.info("search argument cannot be used in Infiniium class.")
            raise ValueError('search argument in not implemented in Infiniium class.')
        for ch in self.scope.channels:
            self.scope.write(f"CHANnel{ch}:OFFSet {channels_offset[int(ch)-1]}")
            channel_offset = self.scope.query(f"CHANnel{ch}:OFFSet?")
            self.log.info(f"The offset of CH{ch} is {channel_offset} V")


    def set_trigger(self, trigger_on_channel=(True, True, True, True), baseline=(300E-3, 300E-3, 300E-3, 300E-3), slope="FALLing", relative_trigger_level_volt=-10E-3):
        for ch in trigger_on_channel:
            assert ch in [True, False]  # assert trigger condition is set on channel or not
        assert slope in ['RISing', 'FALLing', 'EITHer']
        #Set trigger states of the channels (RISing, FALLing, EITHer, DONTcare)
        channel_state = [slope if trigger_on_channel[ch-1] else "DONTcare" for ch in self.scope.channels]
        self.scope.write(":TRIGger:SWEep TRIGgered")
        if np.sum(trigger_on_channel) > 1:  # if the trigger condition is set for more than one channel
            self.scope.write("TRIGger:MODE OR")
            for ch in self.scope.channels:
                # Include the channel in the trigger logic
                self.scope.write(f":TRIGger:OR:LOGic CHANnel{ch}, {channel_state[int(ch)-1]}")
                # Set the trigger position relative to the baseline position
                self.scope.write(f":TRIGger:LEVel CHANnel{ch}, {str(baseline[int(ch)-1]+relative_trigger_level_volt)}")  # put the trigger level with an offset given by relative position with respect to the baseline
                self.log.debug(f"Channel {ch} trigger level is: "+self.scope.query(f":TRIGger:LEVel? CHANnel{ch}"))
            self.log.info("OR trigger mode correctly set")
        elif np.sum(trigger_on_channel) == 1:  # if the trigger condition is set for one channel only
            idx = trigger_on_channel.index(True)
            self.scope.write(":TRIGger:MODE EDGE")
            self.scope.write(":TRIGger:EDGE:COUPling DC")
            self.scope.write(f":TRIGger:EDGE:SLOPe {self._EDGE_DICT[channel_state[idx]]}")
            self.scope.write(f":TRIGger:EDGE:SOURce CHANnel{idx+1}")
            self.scope.write(f":TRIGger:LEVel CHANnel{idx+1}, {str(baseline[idx+1]+relative_trigger_level_volt)}")  # put the trigger level with an offset given by relative position with respect to the baseline
            self.log.debug(f"Channel {idx+1} trigger level is: "+self.scope.query(f":TRIGger:LEVel? CHANnel{idx+1}"))
            self.log.info(f"Trigger condition correctly set for channel {idx+1}")
        else:
            self.log.fatal('No channel selected for triggering. Terminating')
            raise ValueError('No channel selected for triggering!')


    def arm_trigger(self, force=False):
        # prepare the oscilloscope for triggering
        if force is False:
            # method to catch a SINGLE waveform on the scope
            self.scope.write(":SINGle")
            # wait for the trigger to be armed
            armed_status = int(self.scope.query(":AER?"))
            while armed_status != 1:
                armed_status = int(self.scope.query(":AER?"))
                self.log.debug(f"check armed status: value {armed_status}") # check: value 1
                time.sleep(0.01)
            return
        # if force, operate in RUN+STOP mode
        self.scope.write(":RUN")
        armed_status = int(self.scope.query(":AER?")) # check if the trigger is armed
        while armed_status != 1:
            armed_status = int(self.scope.query(":AER?"))
            self.log.debug(f"check armed status: value {armed_status}") # check: value 1
            time.sleep(0.01)
        time.sleep(0.1) # wait for the waveform to be displayed
        stop_status = int(self.scope.query(":STOP;*OPC?")) # stop the scope and check if it has successfully completed all the operations
        while stop_status != 1:
            stop_status = int(self.scope.query(":*OPC?"))
            self.log.debug(f"check stop status: value {stop_status}") # check: value 1
            time.sleep(0.01)
        self.log.debug(f"Scope has been stopped")


    def is_ready(self):
        # Is the scope stopped such that it is ready to be readout?
        return self.scope.query(":RSTate?") == "STOP"


    def readout(self,debug_mode=False):
        self.log.debug("START readout\n")
        if debug_mode:
            self.log.warning("debug_mode parameter not used.")
        # Loop on the used channels
        for j in range(len(self.scope.channels)):
            self.log.debug(f"reading channel {str(j+1)}")
            self.scope.write(f":WAVeform:SOURce CHANnel{str(j+1)}")
            if self._data_format == "BYTE":
                dataword = self.scope.query_binary_values(":WAVeform:DATA?", datatype='s', data_points=int(self.scope.query(":WAVeform:POINts?")), container=bytes)  # 8 bit precision
            else:
                dataword = self.scope.query_binary_values(":WAVeform:DATA?", datatype='h', data_points=int(self.scope.query(":WAVeform:POINts?")), container=np.array)  # 10 bit precision (two bytes needed)
                dataword = [int(i).to_bytes(2, 'little', signed=True) for i in dataword]  # convert int16 numbers in two bytes
                dataword = b''.join(dataword)
            self.data[j] = dataword # save the data as bytes format
            # query dx, x0, dy, y0 only once in the entire acquisition process
            if not self._query_flags[j]:
                if (self._dx is None) and (self._x0 is None): # since x axis is common for all channels, it is queried just once
                    self._dx = float(self.scope.query(":WAVeform:XINCrement?"))
                    self._x0 = float(self.scope.query(":WAVeform:XORigin?"))
                self._dy[j] = float(self.scope.query(":WAVeform:YINCrement?"))
                self._y0[j] = float(self.scope.query(":WAVeform:YORigin?"))
                self._query_flags[j] = True
        self.log.debug("Scope has captured a waveform\n")
        return self.data


    def set_trigger_sweep(self, mode="AUTO"):
        assert mode in ["AUTO", "TRIGgered", "SINGle"]  # SINGle sweep should not be used
        self.scope.write(f":TRIGger:SWEep {mode}")
        trg_sweep = self.scope.query(":TRIGger:SWEep?")
        self.log.debug(f"Trigger sweep is: {trg_sweep}")


    def clear(self):
        self.log.info("Clearing scope registers and query variables\n")
        # clear scope registers
        self.scope.write("*CLS")  # clear scope register and status 
        self.scope.write("*RST")  # go to the default setup which is the same as pressing the oscilloscope front panel [Default Setup] key.
        self.scope.write("STOP")        
        self.data = [None, None, None ,None]
        self.clear_waveform_axis_variables()


    def set_measurement(self):
        self.scope.write(":MEASure:STATistics ON")  # allow the statistics measurement
        self.scope.write("MEASure:SENDvalid OFF")   # when measuring statistics, disable the the result state code


    def baseline_measurement(self):
        self.scope.write(":MEASure:CLEar")  # clear the measurements present on the screen
        self.scope.write(":RUN")
        # prepare the command string to measure all the used channels
        measurement_command_string = ""
        for ch in self.scope.channels:
            measurement_command_string = measurement_command_string + f":MEASure:VAVerage DISPlay,CHANnel{ch}; "
        measurement_command_string = measurement_command_string[:-2]
        self.scope.write(measurement_command_string)  # send the measurement command


    def get_measurement_result(self):
        self.scope.write(":STOP")
        response = self.scope.query(":MEASure:RESults?")
        return response 

class Rohde(OPAMPscope):
    RsInstrument.assert_minimum_version('1.21.0.78')
    _X0_DIVISION = -5 # number of time divisions used to extract the zero of x axis
    _DY_ADC_CONVERSION = 1 # V/ADC-units conversion factor from scope ADC to V
    _BASELINE_INCREMENT = 0.3 # V increment of the baseline variable
    _TIME_DIVISION = 10 # total number of time divisions
    _VOLTAGE_DIVISION = 10 # total number of voltage divisions
    _V_DIVISION = 6 # number of Volt divisions used to scan y axis looking for a signal
    _MAX_OFFSET = -1 # V maximum offset befor exiting the loop
    sampling_period_s=0.05E-9 # sampling period
    
    def __init__(self, address='169.254.167.233', timeout_sec=30, active_channels=[1, 2, 3, 4]):
        OPAMPscope.__init__(self)

        self.scope = RsInstrument(f"TCPIP::{address}::INSTR", True, False)
        self.log.info("Opening communication with " + self.scope.query("*IDN?"))
        self.scope.query_opc() # Wait for operation complete 

        #Initializing variables
        self.trg_time = None # trigger time (no date)
        self.vdiv = None # makes voltage division tuple available for all methods
        self.scope.channels = active_channels


    def __del__(self):
        self.scope.close()
        self.log.info("Communication closed.")
        
        
    def configure(self, data_format=None, channels_termination=(None, None, None, None), vdiv=(0.075, 0.075, 0.075, 0.075), tdiv=5E-9, sampling_period_s=0.05E-9, window_delay_s=10E-9, trg_delay_s = 10E-9):
        #for pulsing_calibration vdiv should be set to 0.020
        if data_format is not None:
            self.log.warning("data_format argument not used in Rhode class.")

        timeout_sec=60

        self.scope.visa_timeout = 400000  # Timeout for VISA Read Operations
        self.scope.timeout = timeout_sec*1000 # Set timeout in milliseconds (ms: 1500 s at least for radioactive source op.) and clear buffers        
        self.scope.opc_timeout = 60000  # Timeout for opc-synchronised operations
        
        self.scope.write("SYST:DISP:UPD ON")
        # channel turn on 
        for ch in self.scope.channels:
            self.scope.write(f"CHAN{ch}:STAT ON")
            self.scope.write(f"CHAN{ch}:COUP DC") # channels coupling set to direct connection with 50Ω termination
            self.scope.query("*OPC?")
            self.log.info(f"Channel {ch}: Status "+ self.scope.query(f"CHAN{ch}:STAT?") + "  Coupling "+ self.scope.query(f"CHAN{ch}:COUP?") )

        self.scope.write("TIM:REF 40") # reference point of the time scale in % of the display 40%
        self.scope.write("ACQuire:COUNt 1") # it sets the number of waveforms acquired with RUNSingle and the number of waveforms used to calculate the average waveform

        time.sleep(2)
        self.log.info("Waiting 2 seconds for settings to be completed")

        self.vdiv = vdiv
        for ch, n_vdiv in zip(self.scope.channels, self.vdiv):
            
            self.scope.write(f"CHAN{ch}:POS 0")  # Vertical Position
            # set the vertical scale of all the CHs
            self.scope.write(f"CHANnel{ch}:SCALe {n_vdiv}")
            
            self.log.info(f"Ch.{ch} vertical scale = " + self.scope.query(f"CHANnel{ch}:SCALe?"))
            
            # set the time scale
            self.scope.write(f"TIM:SCAL {tdiv}")
            
            self.log.info(f"channel {ch} horizontal scale = " + self.scope.query("TIM:SCAL?"))
            
        self.scope.write(f"TIM:POS {trg_delay_s}")
        self.log.info(f"Trigger delay = " + self.scope.query("TIM:POS?"))
        
    def set_offset(self, search=True, channels_offset=(300E-3, 300E-3, 300E-3, 300E-3)):
        
        if search is True:
            self.scope.write("RUNContinous")
            self.scope.write('TRIGger:MODE AUTO')
            # Method to set up the offset for each channel to allow correct waveform capture
            
            for ch, n_offset in zip(self.scope.channels,channels_offset):
                self.scope.write(f"MEAS{ch} ON") # Switches the indicated measurement on or off
                self.scope.write(f"MEAS{ch}:SOUR C{ch}W1")  # source of the measurement
                self.scope.write(f"MEAS{ch}:CAT AMPT")     # measurement category. Amplitude and Time
                self.scope.write(f"MEAS{ch}:MAIN HIGH")    # Defines or queries the main measurement. Baseline
                self.scope.write(f"MEAS{ch}:STAT ON")      # Enables statistics calculation for the measurement
                self.scope.write_str(f"MEAS{ch}:VERT:AUTO")# vertical scaling is adapted to the current measurement results automatically during the long term measurement period
                # set the offset
                initial_offset = 0
                self.scope.write(f"MEAS{ch}:STAT:RES")              
                self.scope.write(f"CHAN{ch}:OFFS {initial_offset}")


                self.scope.write("TRIG1:MODE AUTO")
                time.sleep(0.4)

                self.scope.write("STOP")
                self.scope.query_opc()
                baseline = self.scope.query(f"MEAS{ch}:RES:AVG?")
                standard_deviation = self.scope.query(f"MEAS{ch}:RES:STDD?")
                self.scope.write("RUN")

                while float(standard_deviation) == 0 :
                    n_vdiv=self.scope.query(f"CHANnel{ch}:SCALe?")
                    initial_offset = initial_offset + n_vdiv*self._V_DIVISION
                    
                    self.scope.write(f"CHAN{ch}:OFFS {initial_offset}")
                    self.scope.write("TRIG1:MODE AUTO")
                    time.sleep(0.5)
                    self.scope.write("STOP")
                    self.scope.query_opc()
                    standard_deviation = self.scope.query(f"MEAS{ch}:RES:STDD?")
                    assert initial_offset > self._MAX_OFFSET, "set_offset() failed to find a signal."

                self.scope.write("TRIG1:MODE AUTO")
                time.sleep(0.5)

                self.scope.write("STOP")
                self.scope.query_opc()

                baseline = self.scope.query(f"MEAS{ch}:RES:AVG?")
                self.scope.write("RUN")

                baseline = float(baseline) + self._BASELINE_INCREMENT*self.vdiv[0]
                
                self.scope.write(f"CHAN{ch}:OFFS {baseline}")
                channel_offset=self.scope.query(f"CHAN{ch}:OFFS?")
                self.scope.write("TRIG1:MODE AUTO")
                time.sleep(0.5)
                self.scope.query_opc()
                self.scope.write(f"MEAS{ch}:STAT:RES")
            return
        for ch, n_offset in zip(self.scope.channels,channels_offset):
            self.scope.write(f"CHAN{ch}:OFFS {n_offset}")
            self.log.info(f"The offset of CH{ch} is {n_offset}")
        
    def set_trigger(self, trigger_on_channel=(None, None, None, None), baseline=None, slope="L", relative_trigger_level_volt=-0.01):
        if baseline is not None:
            self.log.warning("baseline tuple is not used in Rohde class.")
        chan = 0
        not_none_count=0
        for trig in trigger_on_channel:
            chan += 1
            if trig is not None:
                self.scope.write(f"TRIG1:SOUR CHAN{chan}") # source of the trigger signal
                not_none_count+=1
            if not_none_count > 1:
                self.log.warning("trigger_on_channel tuple is not used in Rohde class.")

        for ch in self.scope.channels:
            self.scope.write(f"CHAN{ch}:POS 0")  # Vertical Position
            self.scope.write(f"MEAS{ch} ON") # Switches the indicated measurement on or off
            self.scope.write(f"MEAS{ch}:SOUR C{ch}W1")  # source of the measurement
            self.scope.write(f"MEAS{ch}:CAT AMPT")     # measurement category. Amplitude and Time
            self.scope.write(f"MEAS{ch}:MAIN HIGH")    # Defines or queries the main measurement. Baseline
            self.scope.write(f"MEAS{ch}:ADD AMPL,ON")
            self.scope.write(f"MEAS{ch}:ADD FTIM,ON")
            self.scope.write(f"MEAS{ch}:STAT ON")      # Enables statistics calculation for the measurement
            self.scope.write_str(f"MEAS{ch}:VERT:AUTO")# vertical scaling is adapted to the current measurement results automatically during the long term measurement period     

        self.scope.write("DISP:TRIG:LIN ON")
        self.scope.write("TRIG1:TYPE PATT")
        self.scope.write("TRIG1:QUAL11:STAT ON")
        self.scope.write("TRIG1:QUAL11:A:ENAB ON")
        self.scope.write("TRIG1:QUAL11:B:ENAB ON")
        self.scope.write("TRIG1:QUAL11:C:ENAB ON")
        self.scope.write("TRIG1:QUAL11:D:ENAB ON")
        self.scope.write("TRIG1:SOUR CHAN1")
        self.scope.write("TRIG1:QUAL11:A:LOG NOT")
        self.scope.write("TRIG1:QUAL11:B:LOG NOT")
        self.scope.write("TRIG1:QUAL11:C:LOG NOT")
        self.scope.write("TRIG1:QUAL11:D:LOG NOT")
        self.scope.write("TRIG1:QUAL11:AB:LOG OR")
        self.scope.write("TRIG1:QUAL11:CD:LOG OR")
        self.scope.write("TRIG1:QUAL11:ABCD:LOG OR")
    
        for ch in self.scope.channels:
           self.scope.write("TRIG1:MODE AUTO")
           time.sleep(0.5)
           self.scope.write("TRIG1:MODE NORM")
           time.sleep(0.5)
           self.scope.query_opc()

           baseline = self.scope.query(f"MEAS{ch}:RES:AVG?") #baseline
           
           trigger_level = float(baseline) + relative_trigger_level_volt
           
           self.scope.write("TRIG1:MODE AUTO")
           self.scope.write(f"TRIG1:LEV{ch} {trigger_level}")
           self.scope.query("TRIG1:LEV?")
           self.log.debug(f"Trigger level Ch. {ch}   " + self.scope.query(f"TRIG1:LEV{ch}?") + " V" )
           self.scope.write("TRIG1:MODE NORM")
           self.scope.write(f"MEAS{ch}:STAT:RES")

        self.scope.query_opc()
        time.sleep(0.5)


    def arm_trigger(self, force=False):
        if force is False:
            self.scope.write_str_with_opc("RUNsingle")
            self.scope.write("ACQuire:COUNt 1")
        else:
            self.scope.write_str_with_opc("RUNContinous")

        self.log.debug('RTO triggered, capturing data ...')
        self.log.debug(f'Number of sample points: {self.scope.query_float("ACQ:POIN?")}')
        self.log.debug(f'Number of points sampled in one second: {self.scope.query_float("ACQ:POIN:ARAT?")}')

        value = None
        while value is not 1:
            value = self.scope.query("*OPC?").split("*OPC") # 0, 1
            self.log.debug(f"check: value {value}") # check: value 1
            time.sleep(0.01)

        self.scope.write("RUN")
        self.scope.write("*WAI")
        self.scope.query("*OPC?")
        self.ready_for_acquisition = True
        self.log.info("self.ready_for_acquisition")

        return
        
    def is_ready(self):
        self.log.debug('scope query *OPC: '+self.scope.query("*OPC?") )
        return int(self.scope.query("*OPC?"))
 
    def readout(self, debug_mode):
        self.log.debug("START data taking\n")
        self.log.debug("collecting 1 trigger\n")

        self.log.debug('Number of sample points: '+self.scope.query_float("ACQ:POIN?"))

        # Loop on the 4 channels
        for j in self.scope.channels:
            
            self.log.debug("reading channel "+str(j+1))
            
            dataword = self.scope.query_bin_block(f'FORM REAL,32;:CHAN{str(j+1)}:DATA?') #read binary waveform
            self.scope.write("*WAI")
            self.scope.query("*OPC?")
            self.data[j] = dataword # save the data as byte format               

        return self.data #return false oppure true e uso 4 variabili con le 4 forme d'onda "buffer" che vado a richiamare. Devo fare un master e uno slave delle apts. Lo slave legge solo quando il master glielo dice 

        if debug_mode:
            for ch in self.scope.channels:
                self.log.debug(f"Ch.{ch} vertical scale = " + self.scope.query(f"CHANnel{ch}:SCALe?"))

        # TRIGGER_TIME
        dt1 = datetime.now()       
        self.log.debug("Trigger time = "+ self.scope.query("CHAN1:HIST:TSAB?")) 
        
        # Loop on the 4 channels
        for j in self.scope.channels:            
            self.log.debug("reading channel "+str(j+1))            
            dataword = self.scope.query_bin_block(f'FORM REAL,32;:CHAN{str(j+1)}:DATA?') #read binary waveform
            self.scope.write("*WAI")
            self.scope.query("*OPC?")
            self.data[j] = dataword # save the data as byte format  

            if not self._query_flags[j]:
                if (self._dx is None) and (self._x0 is None): # since x axis is common for all channels, is queried just once
                    self._dx = float(self.sampling_period_s) # sampling rate
                    self._x0 = float(self._X0_DIVISION*float(self.scope.query("TIMebase:SCALe?")) + float(self.scope.query("TIMebase:HORizontal:POSition?"))) # starting point of time sampling
                self._dy[j] = float(self.scope.query(f"CHANnel{j}:SCALe?"))*self._DY_ADC_CONVERSION
                self._y0[j] = -float(self.scope.query(f"CHANnel{j}:OFFS?"))
                self._query_flags[j] = True
        self.log.debug("Scope has captured a waveform\n")             

        return self.data

    def get_trg_time(self,parse):
        if parse:
            return re.search(r'\d+:\d+\s*\d+\,\d+\.\d+\.\d+',self.scope.query("CHAN1:HIST:TSAB?")).group(0)
        else:
            return self.scope.query("CHAN1:HIST:TSAB?")

    def set_trigger_sweep(self, mode="AUTO"):
        assert mode in ["AUTO", "NORM"]
        self.scope.write(f"TRIG1:MODE {mode}")
        self.log.debug("Trigger sweep is: " + self.scope.query("TRIG1:MODE?"))
        
      
    def clear(self):
        self.log.debug("Clearing scope registers")
        self.data=[None, None, None, None]
        self.clear_waveform_axis_variables()
