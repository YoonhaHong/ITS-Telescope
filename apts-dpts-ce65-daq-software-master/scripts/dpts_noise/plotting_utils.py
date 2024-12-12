from matplotlib import pyplot as plt
import numpy as np

def plot_parameters(pars, x=0.75, y=0.6):
    p = {k: '?' for k in ['wafer','chip','version','split', 'id', 'temperature',
                          'pwell','sub','vcasn','vcasb', 'idb',
                          'ireset', 'ibias', 'ibiasn','vbb','vh','ibiasf','prefix']}
    p.update(pars)

    #if ("decoding" or "dpts_RTN_") not in p['prefix']:
    #    p['vh']=None
    if "aout" not in p['prefix']:
        p['ibiasf']=None

    # remove potential .0
    for k in ['vcasb','vcasn','ireset','idb','ibias','ibiasn','vh','ibiasf','temperature']:
        if p[k]=="?" or p[k] is None or p[k]=='variable': continue
        if float(p[k]).is_integer(): p[k] = int(p[k])

    if 'Diff' in p['id']:
        p['wafer'] = None
        p['chip'] = None
        p['version'] = None
    if p['sub'] is None or p['pwell'] is None or p['pwell']=="?": p['vbb'] = ""
    else: p['vbb'] = "=%s\,\\mathrm{V}"%p['sub']

    if p['temperature']!="variable": p['temperature'] = "%s\,\\mathrm{°C}"%p['temperature']
    if p['vcasb']!="variable": p['vcasb'] = "%s\,\\mathrm{mV}"%p['vcasb']
    if p['vcasn']!="variable": p['vcasn'] = "%s\,\\mathrm{mV}"%p['vcasn']
    if p['ireset']!="variable": p['ireset'] = "%s\,\\mathrm{pA}"%p['ireset']
    if p['idb']!="variable": p['idb'] = "%s\,\\mathrm{nA}"%p['idb']
    if p['ibias']!="variable": p['ibias'] = "%s\,\\mathrm{nA}"%p['ibias']
    else: p['ibiasn'] = "I_{bias}/10"
    if "/" not in str(p['ibiasn']): p['ibiasn'] = "%s\,\\mathrm{nA}"%p['ibiasn']

    if p['vh']!="variable": p['vh'] = "%s\,\\mathrm{mV}"%p['vh']
    if p['ibiasf']!="variable": p['ibiasf'] = "%s\,\\mathrm{mA}"%p['ibiasf']

    info = [
        '$\\bf{ITS3}$ $\it{WIP}$',
        '$\\bf{%s}$'%p['id'],
        'wafer: %s'%p['wafer'],
        'chip: %s'%p['chip'],
        'version: %s'%p['version'],
        'split:  %s'%p['split'],
        '$T=%s$' %p['temperature'],
        '$I_{reset}=%s$' %p['ireset'],
        '$I_{bias}=%s$' %p['ibias'],
        '$I_{biasn}=%s$' %p['ibiasn'],
        '$I_{db}=%s$'   %p['idb'],
        '$V_{casn}=%s$' %p['vcasn'],
        '$V_{casb}=%s$' %p['vcasb'],
        '$V_{pwell}=V_{sub}%s$' %p['vbb'],
        '$V_{h}=%s$' %p['vh'],
        '$I_{biasf}=%s$' %p['ibiasf']
    ]

    plt.text(x,y,
        '\n'.join([i for i in info if ("None" not in i) and ("?" not in i)]),
        fontsize=8,
        ha='left', va='top',
        transform=plt.gca().transAxes
    )

def add_fhr_limit(limit=1./(1e4*4.001e-5*1024)):
    plt.axhline(limit,linestyle='dotted',color='grey')
    plt.text(plt.gca().get_xlim()[1]*0.98,limit*0.85,
        "FHR measurement sensitivity limit",
        fontsize=7,
        ha='right', va='top',
    )

def compute_profile(x, y, nbin=(100,100)):
    
    # make sure they are numpy arrays
    x=np.array(x)
    y=np.array(y)

    # use of the 2d hist by numpy to avoid plotting
    h, xe, ye = np.histogram2d(x,y,nbin)
    
    # bin width
    xbinw = xe[1]-xe[0]

    # getting the mean and RMS values of each vertical slice of the 2D distribution
    # also the x valuse should be recomputed because of the possibility of empty slices
    x_array      = []
    x_slice_mean = []
    x_slice_rms  = []
    for i in range(xe.size-1):
        yvals = y[ (x>xe[i]) & (x<=xe[i+1]) ]
        if yvals.size>0: # do not fill the quanties for empty slices
            x_array.append(xe[i]+ xbinw/2)
            x_slice_mean.append( yvals.mean())
            x_slice_rms.append( yvals.std())
    x_array = np.array(x_array)
    x_slice_mean = np.array(x_slice_mean)
    x_slice_rms = np.array(x_slice_rms)

    return x_array, x_slice_mean, x_slice_rms
