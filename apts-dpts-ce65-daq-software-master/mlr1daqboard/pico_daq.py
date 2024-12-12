#!/usr/bin/env python3

import ctypes
from time import sleep
from picosdk.ps6000a import ps6000a as ps
from picosdk.PicoDeviceEnums import picoEnum as enums
from picosdk.PicoDeviceStructs import picoStruct as structs
from picosdk.functions import adc2mV, mV2adc, assert_pico_ok
import numpy as np
import re

# for some reasons there is no PICO_CONNECT_PROBE_RANGE in picoEnum
PICO_CONNECT_PROBE_RANGE={
    'PICO_10MV' : 0,
    'PICO_20MV' : 1,
    'PICO_50MV' : 2,
    'PICO_100MV': 3,
    'PICO_200MV': 4,
    'PICO_500MV': 5,
    'PICO_1V'   : 6,
    'PICO_2V'   : 7,
    'PICO_5V'   : 8,
    'PICO_10V'  : 9,
    'PICO_20V'  :10
}

def find_picoscope():
    count=ctypes.c_int16(0)
    serials=ctypes.create_string_buffer(100)
    serialLth=ctypes.c_int16(100)
    serials.value=bytes("-v",encoding='utf-8')
    ret=ps.ps6000aEnumerateUnits(
        ctypes.byref(count),
        serials,
        ctypes.byref(serialLth)
    )
    assert_pico_ok(ret)
    if count.value==0:
        raise RuntimeError("Picoscope not found")
    elif count.value==1:
        return re.findall('(.*)\[(.*)\]', serials.value.decode('utf-8'))[0] #(serial,model)
    else:
        raise NotImplementedError("Multiple Picoscopes found")
    return count.value,serials.value.decode('utf-8')

class ScopeAcqPS6000a:
    def __init__(self,trg_ch,trg_mV,npre,npost,nsegments=1,auto_trigger_us=0,model='auto'):
        self.npre=npre
        self.npost=npost
        self.nsegments=nsegments
        self.handle=ctypes.c_int16()
        if model=='auto':
            _,self.model=find_picoscope()
        else:
            self.model=model
        if self.model[1] == '8':
            self.channels = list('ABCDEFGH')
            self.active_channels=['D','E']
        elif self.model[1] == '4':
            self.channels = list('ABCD')
            self.active_channels=['B','C']
        else:
            raise ValueError(f'Uknown model type {self.model}, expected 68xxE or 64xxE')
        assert trg_ch in self.active_channels+['AUX'], \
            f"Model {self.model} forseen to be triggered on channels {self.active_channels} or AUX, not {trg_ch}"
        self.ranges   =dict((c,PICO_CONNECT_PROBE_RANGE['PICO_200MV']) for c in self.active_channels)
        self.couplings=dict((c,enums.PICO_COUPLING['PICO_DC_50OHM'])   for c in self.active_channels)

        resolution=enums.PICO_DEVICE_RESOLUTION['PICO_DR_8BIT']
        ret=ps.ps6000aOpenUnit(
            ctypes.byref(self.handle),
            None, # TODO: check this
            resolution
        )
        assert_pico_ok(ret)

        self.adc_min=ctypes.c_int16() # this is ugly, but the mV2ADC function calls adc_min.value
        self.adc_max=ctypes.c_int16()
        ret=ps.ps6000aGetAdcLimits(
            self.handle,
            resolution,
            ctypes.byref(self.adc_min),
            ctypes.byref(self.adc_max)
        )
        assert_pico_ok(ret)
        
        for c in self.channels:
            if c in self.active_channels:
                ret=ps.ps6000aSetChannelOn(
                    self.handle,
                    enums.PICO_CHANNEL[f'PICO_CHANNEL_{c}'],
                    self.couplings[c],
                    self.ranges[c],
                    0, # offset
                    enums.PICO_BANDWIDTH_LIMITER['PICO_BW_FULL']
                )
                assert_pico_ok(ret)
            else:
                ret=ps.ps6000aSetChannelOff(
                    self.handle,
                    enums.PICO_CHANNEL[f'PICO_CHANNEL_{c}']
                )
                assert_pico_ok(ret)

        nsamplesmax=ctypes.c_uint64()
        ret=ps.ps6000aMemorySegments(
            self.handle,
            nsegments,
            ctypes.byref(nsamplesmax)
        )
        assert_pico_ok(ret)
        assert(nsamplesmax.value>=npre+npost)

        if self.nsegments!=1:
            ret=ps.ps6000aSetNoOfCaptures(
                self.handle,
                self.nsegments
            )
            assert_pico_ok(ret)

        timebase=ctypes.c_uint32()
        dt=ctypes.c_double()
        ret=ps.ps6000aGetMinimumTimebaseStateless(
            self.handle,
            sum([enums.PICO_CHANNEL_FLAGS[f'PICO_CHANNEL_{c}_FLAGS'] for c in self.active_channels]),
            ctypes.byref(timebase),
            ctypes.byref(dt),
            resolution
        )
        assert_pico_ok(ret)
        self.timebase=timebase.value
        self.dt=dt.value

        ntot=self.npre+self.npost
        self.buffer=(ctypes.c_int8*(ntot*len(self.active_channels)*nsegments))()
        for iseg in range(self.nsegments):
            for ich,ch in enumerate(self.active_channels):
                ret=ps.ps6000aSetDataBuffer(
                    self.handle,
                    enums.PICO_CHANNEL[f'PICO_CHANNEL_{ch}'],
                    ctypes.byref(self.buffer,(iseg*len(self.active_channels)+ich)*ntot),
                    ntot,
                    enums.PICO_DATA_TYPE['PICO_INT8_T'],
                    iseg, # "waveform": segment index
                    enums.PICO_RATIO_MODE['PICO_RATIO_MODE_RAW'], #downsample_ratio_mode 
                    enums.PICO_ACTION['PICO_ADD']
                )
                assert_pico_ok(ret)

        self.set_trigger(trg_ch,trg_mV,auto_trigger_us)
        self.set_signal_generator()


    def __del__(self):
        if self.handle.value>0:
            self.stop()
            ps.ps6000aCloseUnit(self.handle)

    def stop(self):
        ret=ps.ps6000aStop(self.handle)
        assert_pico_ok(ret)

    def set_trigger(self,trg_ch,trg_mV,auto_trigger_us=0,aux_busy=False):
        trg_conds = []
        trg_dirs = []
        trg_props = []
        if trg_ch in self.channels:
            # N.B. 600 ns latency between scope trigger and function generator output, ref Phillipp
            trg_conds.append(structs.PICO_CONDITION(
                enums.PICO_CHANNEL[f'PICO_CHANNEL_{trg_ch}'],
                enums.PICO_TRIGGER_STATE['PICO_CONDITION_TRUE']
            ))
            trg_dirs.append(structs.PICO_DIRECTION(
                enums.PICO_CHANNEL[f'PICO_CHANNEL_{trg_ch}'],
                enums.PICO_THRESHOLD_DIRECTION['PICO_RISING'],
                enums.PICO_THRESHOLD_MODE['PICO_LEVEL']
            ))
            trg_props.append(structs.PICO_TRIGGER_CHANNEL_PROPERTIES(
                mV2adc(trg_mV,self.ranges[trg_ch],self.adc_max),
                0, # no hysteresis
                0, # no lower threshold
                0, # no hysteresis either
                enums.PICO_CHANNEL[f'PICO_CHANNEL_{trg_ch}']
            ))
            if aux_busy:
                trg_conds.append(structs.PICO_CONDITION(
                    enums.PICO_CHANNEL['PICO_TRIGGER_AUX'],
                    enums.PICO_TRIGGER_STATE['PICO_CONDITION_TRUE']
                ))
                trg_dirs.append(structs.PICO_DIRECTION(
                    enums.PICO_CHANNEL['PICO_TRIGGER_AUX'],
                    enums.PICO_THRESHOLD_DIRECTION['PICO_BELOW'],
                    enums.PICO_THRESHOLD_MODE['PICO_LEVEL']
                ))
                trg_props.append(structs.PICO_TRIGGER_CHANNEL_PROPERTIES(
                    0,
                    0,
                    0, 
                    0,
                    enums.PICO_CHANNEL['PICO_TRIGGER_AUX']
                ))
        elif trg_ch=='AUX':
            trg_conds.append(structs.PICO_CONDITION(
                enums.PICO_CHANNEL['PICO_TRIGGER_AUX'],
                enums.PICO_TRIGGER_STATE['PICO_CONDITION_TRUE']
            ))
            trg_dirs.append(structs.PICO_DIRECTION(
                enums.PICO_CHANNEL['PICO_TRIGGER_AUX'],
                enums.PICO_THRESHOLD_DIRECTION['PICO_RISING'],
                enums.PICO_THRESHOLD_MODE['PICO_LEVEL']
            ))
            trg_props.append(structs.PICO_TRIGGER_CHANNEL_PROPERTIES(
                0, # dummy
                0, # dummy
                0, 
                0,
                enums.PICO_CHANNEL['PICO_TRIGGER_AUX']
            ))
        else:
                raise ValueError(f'Unknown trigger source: {trg_ch}')

        trg_conds_c = (structs.PICO_CONDITION*len(trg_conds))(*trg_conds)
        ret=ps.ps6000aSetTriggerChannelConditions(
            self.handle,
            ctypes.byref(trg_conds_c),
            len(trg_conds), # number of conditions
            enums.PICO_ACTION['PICO_CLEAR_ALL']|enums.PICO_ACTION['PICO_ADD']
        )
        assert_pico_ok(ret)
        trg_dirs_c = (structs.PICO_DIRECTION*len(trg_dirs))(*trg_dirs)
        ret=ps.ps6000aSetTriggerChannelDirections(
            self.handle,
            ctypes.byref(trg_dirs_c),
            len(trg_dirs), # number of directions
        )
        assert_pico_ok(ret)
        trg_props_c = (structs.PICO_TRIGGER_CHANNEL_PROPERTIES*len(trg_props))(*trg_props)
        ret=ps.ps6000aSetTriggerChannelProperties(
            self.handle, 
            ctypes.byref(trg_props_c),
            len(trg_props), # number of properties 
            0, # auxOutputEnable
            auto_trigger_us, #autoTriggerMicroSeconds: 0=inf
        )
        assert_pico_ok(ret)


    def set_signal_generator(self,freq=1e4):
        ret=ps.ps6000aSigGenWaveform(
            self.handle,
            enums.PICO_WAVE_TYPE['PICO_SQUARE'],
            0,
            0
        )
        assert_pico_ok(ret)
        
        ret=ps.ps6000aSigGenRange(
            self.handle,
            5.0,
            2.5
        )
        assert_pico_ok(ret)

        ret=ps.ps6000aSigGenWaveformDutyCycle(
            self.handle,
            50 # in percent
        )
        assert_pico_ok(ret)

        ret=ps.ps6000aSigGenFrequency(
            self.handle,
            freq
        )
        assert_pico_ok(ret)

        ret=ps.ps6000aSigGenTrigger(
            self.handle,
            enums.PICO_SIGGEN_TRIG_TYPE['PICO_SIGGEN_RISING'],
            enums.PICO_SIGGEN_TRIG_SOURCE['PICO_SIGGEN_SCOPE_TRIG'],
            1, # only play a single cycle
            0 # no auto-trigger
        )
        assert_pico_ok(ret)
        
        fint=ctypes.c_int16(int(freq))
        ret=ps.ps6000aSigGenApply(
            self.handle,
            1, # enable
            0, # no sweep
            1, # triggered
            0, # no auto_clock_opt
            0, # no override_auto_clock_and_prescale
            ctypes.byref(fint),
            None, # stop_frequency
            None, # frequency_increment
            None  # dwell_time
        )
        assert_pico_ok(ret)

    def print(self):
        print(f'Picoscope model: {self.model}')
        for c,r in self.ranges.items():
            v=adc2mV([1],r,self.adc_max)[0]
            print(f'CHANNEL {c}: vertical resolution: {v} mV, ADC max: {self.adc_max.value}')
        print(f'HORIZONTAL BINS: {self.dt*1e9} ns')

    def arm(self):
        ret=ps.ps6000aRunBlock(
            self.handle,
            self.npre,
            self.npost,
            self.timebase,
            None,
            0,  # segmentIndex
            None,  # lpReady = None   Using IsReady rather than a callback
            None  # pParameter
        )
        assert_pico_ok(ret)
        sleep(0.001) # seems that the scope is really armed only some 1ms after this previous call returned TODO: find out programmatically...

    def ready(self):
        ready=ctypes.c_int16(0)
        ret=ps.ps6000aIsReady(
            self.handle,
            ctypes.byref(ready)
        )
        assert_pico_ok(ret)
        return ready.value!=0

    def wait(self):
        while not self.ready():
            sleep(0.001)

    def rdo(self,ncaptures=None):
        if ncaptures is None: ncaptures=self.nsegments
        assert ncaptures>0, "Cannot read 0 segments!"
        ntot=self.npre+self.npost
        nread=ctypes.c_uint64(ntot)
        ovfl =(ctypes.c_int16*self.nsegments)()
        ret=ps.ps6000aGetValuesBulk(
            self.handle,
            0,  # startIndex
            ctypes.byref(nread),
            0, # fromSegmentIndex
            ncaptures-1, # toSegmentIndex
            1,  # downSampleRatio
            enums.PICO_RATIO_MODE['PICO_RATIO_MODE_RAW'],
            ctypes.byref(ovfl)
        )
        assert_pico_ok(ret)
        data=np.frombuffer(self.buffer,dtype=np.int8,count=ntot*len(self.active_channels)*ncaptures)
        if ncaptures!=1:
            data=np.reshape(data,(ncaptures,len(self.active_channels),ntot))
        else:
            data=np.reshape(data,(len(self.active_channels),ntot))
        return data

    def get_ncaptures(self):
        ncaptures=ctypes.c_uint64()
        ret=ps.ps6000aGetNoOfCaptures(
            self.handle,ctypes.byref(ncaptures)
        )
        assert_pico_ok(ret)
        return ncaptures.value


if __name__=='__main__':
    import argparse
    import logging
    import os
    import datetime
    import numpy as np
    logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')
    gitrepo = "apts-dpts-ce65-daq-software"
    if gitrepo in os.getcwd():
        default_data_dir = os.path.realpath(os.path.join(os.getcwd().split(gitrepo)[0]+gitrepo,"./Data"))
    else:
        default_data_dir = "./pico-data"
    parser=argparse.ArgumentParser('DPTS scope DAQ')
    parser.add_argument('--outdir' ,default=default_data_dir,help='directory with output files')
    parser.add_argument('--trigger',default='AUX'    ,help='trigger source: B,C,D,E or AUX')
    parser.add_argument('-n',default=1,type=int      ,help='total number of aquisitions')
    parser.add_argument('-N',default=1,type=int      ,help='group N acquisitions in semgend acquisition')
    parser.add_argument('--model',default='auto',help="Picoscope model")
    parser.add_argument('--drop-data',action='store_true',help='Do not save data')
    args=parser.parse_args()

    logging.info('Setting up the scope...')
    daq=ScopeAcqPS6000a(trg_ch=args.trigger,trg_mV=50,npre=5000,npost=200000,nsegments=args.N,model=args.model)
    daq.print()
    if not os.path.exists(args.outdir): os.makedirs(args.outdir)
    itrg=0
    while itrg<args.n:
        logging.info(f'Waiting for trigger #{itrg} from channel {args.trigger}...')
        daq.arm()
        daq.wait()
        data=daq.rdo()
        if args.drop_data:
            itrg+=args.N
            continue

        logging.info('Data acquired!')
        now=datetime.datetime.now()
        if args.N==1:
            fname='dpts_'+now.strftime('%Y%m%d_%H%M%S')+'_'+str(itrg)+'.npy'
        else:
            fname='dpts_'+now.strftime('%Y%m%d_%H%M%S')+'_'+str(itrg)+'_'+str(itrg+args.N)+'.npy'
        np.save(args.outdir+"/"+fname,data)
        itrg+=args.N

