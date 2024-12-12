from matplotlib import pyplot as plt
import numpy as np
import datetime
from matplotlib import rcParams
import matplotlib.style as style
from cycler import cycler
import json

with open('okabe_ito.json') as jf:
    colors_dict = json.load(jf)

colors = list(colors_dict.values())
colors_names = list(colors_dict.keys())
rcParams['axes.prop_cycle'] = cycler('color', colors)

def color_setting(args, split, pitch, typ):
    color = None
    if args.compared_params == 'split':
        color = colors[split-1]
    elif args.compared_params == 'pitch':
        if pitch == '10':
            color = colors[0]
        elif pitch == '15':
            color = colors[1]
        elif pitch == '20':
            color = colors[2]
        elif pitch == '25':
            color = colors[3]
        else:
            pass
    
    elif args.compared_params == 'flavour':
        if typ == 'B':
            color = colors[0]
        elif typ == 'P': 
            color = colors[1]


    return color

def add_parameters(args,p,design,pitch, split):

    ibiasp = p['ibiasp']/4
    ibiasn = p['ibiasn']/4

    if args.compared_params == "pitch":
        if args.sub_compared == 'Temperature':
            unit = '\u2103'
        elif args.sub_compared == 'Vbb':
            unit = 'V'
        info = [
        '$\\bf{%s}$'%p['id'],
        f'type: {design}',
        f'split: {split}',
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h}=%d\,\\mathrm{mV}$' %p['vh'],
        '$%s: %.1f\,\\mathrm{%s}$'%(args.sub_compared, p['sub_compared'], unit),
        '\n'
        ]
    if args.compared_params == "flavour":
        if args.sub_compared == 'Temperature':
            unit = '\u2103'
        elif args.sub_compared == 'Vbb':
            unit = 'V'
        info = [
        '$\\bf{%s}$'%p['id'],
        f'split: {split}',
        f'pitch: {pitch} \u03BCm',
        '$VH = -%s\, \\mathrm{V}$'%p['vh'],
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$%s: %.1f\,\\mathrm{%s}$'%(args.sub_compared, p['sub_compared'], unit),
        '\n'
        ]
    
    if args.compared_params == "split":
        if args.sub_compared == 'Temperature':
            unit = '\u2103'
        elif args.sub_compared == 'Vbb':
            unit = 'V'
        info = [
        '$\\bf{%s}$'%p['id'],
        f'type: {design}',
        f'pitch: {pitch} \u03BCm',
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h} = %d\,\\mathrm{mV}$' %p['vh'],
        '$%s: %.1f\,\\mathrm{%s}$'%(args.sub_compared, p['sub_compared'], unit),
        '\n'
        ]
    
    if args.compared_params == "chip":
        if args.sub_compared == 'Temperature':
            unit = '\u2103'
        elif args.sub_compared == 'Vbb':
            unit = 'V'
        info = [
        '$\\bf{%s}$'%p['id'],
        f"{p['proximity']}",
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h} = %d\,\\mathrm{mV}$' %p['vh'],
        '$%s: %.1f\,\\mathrm{%s}$'%(args.sub_compared, p['sub_compared'], unit),
        '\n'
        ]

    if args.compared_params == "vbb" or args.compared_params == 'temp':
        info = [
        '$\\bf{%s}$'%p['id'],
        '%s'%p['proximity'],
        '%s'%p['chip_ID'],
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h} = %d\,\\mathrm{mV}$' %p['vh'],
        '\n'
        ]

    if args.compared_params == "irradiation" or args.compared_params == "mux" :
        info = [
        '$\\bf{%s}$'%p['id'],
        f'pitch: {pitch} \u03BCm',
        f'type: {design}',
        'split: 4',
        '$V_{sub}=V_{pwell}= -%s\,\\mathrm{V}$'%p['vbb'],
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]

    
    if args.compared_params == "proximity":
        info = [
        '$\\bf{%s}$'%p['id'],
        f'{p["chip_ID"]}',
        f'type: {design}',
        #f'pitch: {pitch} \u03BCm',
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h} = %d\,\\mathrm{mV}$' %p['vh'],
        '$I_{reset}$ cut = %s pA' %args.ir_cut
        ]

    if args.compared_params == "pixel" or args.compared_params == 'waveform':
        info = [
        '$\\bf{%s}$'%p['id'],
        '%s'%p['chip_ID'],
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '$V_{h} = %d\,\\mathrm{mV}$' %p['vh'],
        '$Vbb: %.1f\,\\mathrm{V}$' %p['vbb'],
        '$Temperature: %d\,\\mathrm{\u2103}$' %p['T'],
        '\n'
        ]
    return info

def add_text_to_plots(args,fig,ax,info,x, y, position):
        left = 1.03
        down = 0.0
        if args.compared_params == 'waveform':
            left = 0.53
            down = 0.25
        fig.text(x - left,y - down,
        '\n'.join([
        '$\\bf{ALICE\;ITS3}$ $\\it{WIP}$'
        ]),
        fontsize=15,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x - left,y-down-0.055,
        '\n'.join([
        'Leakage current measurements',
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x - left,y-down-0.10,
        '\n'.join([
        datetime.datetime.now().strftime("Plotted on %d %b %Y"),
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )
   
        fig.text(
           # x,y-0.17,
            x, y ,
            '\n'.join(info),
            fontsize=12,
            ha= position, va='top',
            transform=ax.transAxes
        )

def add_text_to_cluster(fig,ax,info,x, y, position):
        left = 0.93
        down = 0.0
        fig.text(x - left,y - down,
        '\n'.join([
        '$\\bf{ALICE\;ITS3}$ $\\it{preliminary}$'
        ]),
        fontsize=15,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x - left,y-down-0.055,
        '\n'.join([
        'Fe-55 source measurements',
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x - left,y-down-0.10,
        '\n'.join([
        datetime.datetime.now().strftime("Plotted on %d %b %Y"),
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )
   
        fig.text(
           # x,y-0.17,
            x, y ,
            '\n'.join(info),
            fontsize=12,
            ha= position, va='top',
            transform=ax.transAxes
        )
    
def get_split(wafer, chip_ID):
        if wafer == 'W22':
            split = 4
        elif wafer == 'W19':
            split = 3
            chip_ID = chip_ID[0:10]
        elif wafer == 'W16':
            split = 2
            chip_ID = chip_ID[0:10]
        elif wafer == 'W13':
            split = 1
            chip_ID = chip_ID[0:10]
        else:
            print('Not exixting Wafer! Wafer should be W22 or W13 instead here is W',wafer)
            
        return split, chip_ID

def get_mux_label(mux, isMux):
        label = ''
        if isMux==True:
            if mux == 0:
                label= f'Larger nwell collection electrode'
            elif mux == 1:
                label= f'Reference'
            elif mux == 2:
                label= f'Finger-shape pwell enclosure'
            elif mux == 3:
                label= f'Smaller pwell enclosure'
            else:
                print('Not existing mux type! mux = [0, 1, 2, 3]')
        else:
            label= f'Not multiplexer'
        return label
