#!/usr/bin/env python3

import rtmidi, time
import numpy as np
import logging
import argparse
from tqdm import tqdm
from time import sleep
import os, sys, datetime
import numpy as np
import json
from mlr1daqboard import DPTSDAQBoard 
from mlr1daqboard import dpts_decoder as decoder
from labequipment import HAMEG
import datetime

buttons = {
    58: 'track_left',
    59: 'track_right',
    46: 'cycle',
    60: 'marker_set',
    61: 'marker_left',
    62: 'marker_right',
    43: 'rwd',
    44: 'fwd',
    42: 'stop',
    41: 'play',
    45: 'record',
    32: 's_0',
    33: 's_1',
    34: 's_2',
    35: 's_3',
    36: 's_4',
    37: 's_5',
    38: 's_6',
    39: 's_7',
    48: 'm_0',
    49: 'm_1',
    50: 'm_2',
    51: 'm_3',
    52: 'm_4',
    53: 'm_5',
    54: 'm_6',
    55: 'm_7',
    64: 'r_0',
    65: 'r_1',
    66: 'r_2',
    67: 'r_3',
    68: 'r_4',
    69: 'r_5',
    70: 'r_6',
    71: 'r_7'
}

knobs = [16, 17, 18, 19, 20, 21, 22, 23]

sliders = [0, 1, 2, 3, 4, 5, 6, 7]

def mask_pattern(pxl_list=[], mask=True): 
    mc=mr=md=0x0
    for col,row in pxl_list:
        mr |= 1<<row
        mc |= 1<<col
        md |= 1<<((row-col) if row>=col else (32+row-col))
    if not mask:
        mr ^= 0xFFFFFFFF
        mc ^= 0xFFFFFFFF
        md ^= 0xFFFFFFFF
    return mc,md,mr

def pulse_pattern(pxl_list=[]):
    cs=rs=0x0
    for col,row in pxl_list:
        cs |= 1<<col
        rs |= 1<<row
    return cs,rs

def pulse(dpts, col, row):
    cs,rs=pulse_pattern([(col, row)])
    mc,md,mr=mask_pattern()
    dpts.clear_shreg_fifo()
    dpts.write_shreg(rs=rs,mc=mc,md=md,cs=cs,mr=mr)
    dpts.read_shreg(decode=True)
    dpts.pulse(ncycles_high=10000,ncycles_low=10000,npulses=1)

def set_dpts_params(dpts, params, ps, hameg_conf, force_set=False):
    for param in params:
        if param["changed"] or force_set:
            # print("Set %s to %d %s \n" % (param["name"], param["val"], param["unit"]))
            if param["name"] == "VBB" and ps:
                if param["val"] >= 0 and param["val"] <= 3000:
                    ps.set_volt(int(hameg_conf), param["val"]/1000)
                else:
                    raise ValueError("VBB out of range!")
            if param["name"] == "VCASB":
                dpts.set_vcasb(param["val"])
            if param["name"] == "VCASN":
                dpts.set_vcasn(param["val"])
            if param["name"] == "IRESET":
                dpts.set_ireset(param["val"])
            if param["name"] == "IBIAS":
                dpts.set_ibias(param["val"])
            if param["name"] == "IBIASN":
                dpts.set_ibiasn(param["val"])
            if param["name"] == "IDB":
                dpts.set_idb(param["val"])
            if param["name"] == "VH":
                dpts.set_vh(param["val"])
            param["changed"]=False

def save_params(params):
    out = {}
    for param in params:
        if param["name"] == "VBB":
            out["pwell"] = param["val"]/1000
            out["sub"] = param["val"]/1000
        if param["name"] == "VCASB":
            out["vcasb"] = param["val"]
        if param["name"] == "VCASN":
            out["vcasn"] = param["val"]
        if param["name"] == "IRESET":
            out["ireset"] = param["val"]
        if param["name"] == "IBIAS":
            out["ibias"] = param["val"]*10
        if param["name"] == "IBIASN":
            out["ibiasn"] = param["val"]
        if param["name"] == "IDB":
            out["idb"] = param["val"]*10
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out["savedtimestamp"] = now
    with open("dpts_midi_params_" + now + ".json", "w") as f:
        json.dump(out, f, indent=4)     

def update_cmdline(params, running=None, same_line=True):   
    out=" | ".join([paramdict["name"] + ": " + str(int(paramdict["val"])) + " " + paramdict["unit"] for paramdict in params])
    if running is not None: out+=" | Running: "+str(running)+"       "
    print(out, end = "\r" if same_line else "\n")

class MidiCtrl(object):
    def __init__(self, running=True, single=False):
        self.running = running
        self.single = single
        self.params = None

    def set_params(self, params):
        self.params = params

    def get_params(self):
        return self.params

    def callback(self, message, data):
        control = message[0][1]
        value = message[0][2]
        if control in buttons.keys():
            name = buttons[control]
            if (value == 127):
                return self.button_down(name)
            else:
                return self.button_up(name)
        else:
            try:
                idx = knobs.index(control)
                return self.twisted_knob(idx, value)
            except ValueError:
                pass
            try:
                idx = sliders.index(control)
                return self.slid_slider(idx, value)
            except ValueError:
                pass
            print("Control: %d, Value: %d" % (control, value))

    def button_down(self, button):
        if button == "play":
            self.running = True
        if button == "stop":
            self.running = False
        if button == "fwd":
            self.single = True
        if button == "record":
            save_params(self.params)

    def button_up(self, button):
        pass

    def twisted_knob(self, idx, value):
        pass

    def slid_slider(self, idx, value):
        mapped_val = round(np.interp(value, [0, 127], [self.params[idx]["min"], self.params[idx]["max"]]))
        if mapped_val<self.params[idx]["min"]:
            self.params[idx]["val"] = self.params[idx]["min"]
        elif mapped_val>self.params[idx]["max"]: 
            self.params[idx]["val"] = self.params[idx]["max"]
        else:
            self.params[idx]["val"] = mapped_val
        self.params[idx]["changed"] = True

if __name__=="__main__":
    parser = argparse.ArgumentParser("DPTS midi live control",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('proximity',metavar="PROXIMITY",help='Proximity card name (e.g. DPTS-001). The name must be in the same format as the corresponding calibration file.')
    parser.add_argument('midiport',metavar="MIDIPORT",type=float,help='Port of the MIDI connection.')
    parser.add_argument('--hameg-conf',nargs=2,metavar=("HAMEGPATH", "HAMEGVBBCHANNEL"),default=None,help='Path to the HAMEG control and channel of the HAMEG used for VBB.')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_term = logging.StreamHandler()
    log_term.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_term.setLevel(logging.INFO)
    logging.getLogger().addHandler(log_term)


    midiin = rtmidi.MidiIn()
    port = midiin.open_port(args.midiport)
    midi = MidiCtrl()
    port.set_callback(midi.callback)

    ps = HAMEG(args.hameg_conf[0]) if args.hameg_conf else None

    with open(os.path.join(sys.path[0], "midistate.json"), 'r') as file_json:
        print("Loading old state from file...")
        print("Sliders may vary from current value now!")
        initial_params = json.load(file_json)

    print("Initializing DAQ board")
    dpts = DPTSDAQBoard(calibration=args.proximity)
    dpts.log.setLevel(logging.INFO)
    if not dpts.is_chip_powered():
        logging.warning(f"Is chip powered? Current seems low: {dpts.read_chip_currents()}")
    set_dpts_params(dpts, initial_params, ps, args.hameg_conf[1], force_set=True)
    dpts.set_ibiasf(4000)
    sleep(0.3)

    midi.set_params(initial_params)

    try:
        while True:
            if midi.running:
                pulse(dpts, 31, 31)
            if midi.single:
                pulse(dpts, 31, 31)
                midi.single = False
            params = midi.get_params()
            if any([param["changed"] for param in params]):
                set_dpts_params(dpts, params, ps, args.hameg_conf[1])
                midi.set_params(params)
            update_cmdline(params, running=midi.running)
            time.sleep(.1)
    except KeyboardInterrupt:
        print("")
        print("User stopped.")
        print("Final values:")
        midi.running=False
        update_cmdline(params, running=midi.running, same_line=False)
        print("Saving last state to midistate.json...")
        with open(os.path.join(sys.path[0], "midistate.json"), 'w') as f:
            json.dump(params, f, indent=4)
    except Exception as e:
        logging.exception(e)
        logging.fatal("Terminating!")
    finally:
        # set HAMEG to non-remote control
        if ps:
            ps.cmd_("SYSTEM:LOCAL")
