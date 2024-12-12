from matplotlib import pyplot as plt
import numpy as np
import datetime

def add_parameters(args,p,design,pitch):

    ibiasp = p['ibiasp']/4
    ibiasn = p['ibiasn']/4
    ireset = p['ireset']*100

    if args.compared_params == "pitch":
        info = [
        '$\\bf{%s}$'%p['id'],
        f'type: {design}',
        'split: 4',
        '$V_{sub}=V_{pwell}= -%s\,\\mathrm{V}$'%p['vbb'],
        '$I_{reset}=%d\,\\mathrm{pA}$' %ireset,
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]
    if args.compared_params == "flavour":
        info = [
        '$\\bf{%s}$'%p['id'],
        f'pitch: {pitch} \u03BCm',
        '$V_{sub}=V_{pwell}= -%s\,\\mathrm{V}$'%p['vbb'],
        '$I_{reset}=%d\,\\mathrm{pA}$' %ireset,
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]
    if args.compared_params == "vbb":
        info = [
        '$\\bf{%s}$'%p['id'],
        '%s'%p['chip_ID'],
        f'pitch: {pitch} \u03BCm',
        f'type: {design}',
        'split: 4',
        '$V_{sub}=V_{pwell}$',
        '$I_{reset}=%d\,\\mathrm{pA}$' %ireset,
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]

    if args.compared_params == "irradiation" or args.compared_params == "mux" :
        info = [
        '$\\bf{%s}$'%p['id'],
        f'pitch: {pitch} \u03BCm',
        f'type: {design}',
        'split: 4',
        '$V_{sub}=V_{pwell}= -%s\,\\mathrm{V}$'%p['vbb'],
        '$I_{reset}=%d\,\\mathrm{pA}$' %ireset,
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]

    if args.compared_params == "ires":
        info = [
        '$\\bf{%s}$'%p['id'],
        f'pitch: {pitch} \u03BCm',
        f'type: {design}',
        'split: 4',
        '$V_{sub}=V_{pwell}= -%s\,\\mathrm{V}$'%p['vbb'],
        #'$I_{reset}=%d\,\\mathrm{pA}$' %ireset,
        '$I_{biasn}=%d\,\\mathrm{\u03BCA}$' %ibiasn,
        '$I_{biasp}=%.1f\,\\mathrm{\u03BCA}$' %ibiasp,
        '$I_{bias4}=%d\,\\mathrm{\u03BCA}$'   %p['ibias4'],
        '$I_{bias3}=%d\,\\mathrm{\u03BCA}$'   %p['ibias3'],
        '$V_{reset}=%d\,\\mathrm{mV}$' %p['vreset'],
        '\n'
        ]

    return info

def add_text_to_plots(fig,ax,info,x, y, position):
        fig.text(x,y,
        '\n'.join([
        '$\\bf{ALICE\;ITS3}$ $\\it{WIP}$'
        ]),
        fontsize=12,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x,y-0.05,
        '\n'.join([
        'Fe55 source measurements',
        ]),
        fontsize=9,
        ha= position, va='top',
        transform=ax.transAxes
        )

        fig.text(x,y-0.1,
        '\n'.join([
        datetime.datetime.now().strftime("Plotted on %d %b %Y"),
        ]),
        fontsize=8,
        ha= position, va='top',
        transform=ax.transAxes
        )
   
        fig.text(
            x,y-0.17,
            '\n'.join(info),
            fontsize=10,
            ha= position, va='top',
            transform=ax.transAxes
        )
    
def get_split(wafer, chip_ID):
        if wafer == 'W22':
            split = 4
        elif wafer == 'W13':
            split = 1
            chip_ID = chip_ID[0:10]
        elif wafer == 'W16':
            split = 2
        elif wafer == 'W19':
            split = 3
        elif wafer == 'W24':
            split = 2
        else:
            print('Not exixting Wafer! Wafer should be W22, W19, W16 or W13 for MLR1 or W24 for ER1 instead here is W',wafer)
            
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
