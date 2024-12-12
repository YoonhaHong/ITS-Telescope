#!/usr/bin/env python3

import numpy as np

MIN_SEP=20e-9

def zero_suppress(t,p,n,invert=False,only_pos=False,fix_thresh=-1):
    if invert:   p,n=n,p
    is_fix_thresh = fix_thresh > 0 # optimisation
    if is_fix_thresh:
        d=np.diff((p>fix_thresh)-0.5)
    else:
        if only_pos: n=np.ones(p.shape)*np.max([0.5*(np.min(p)+np.max(p)),10])
        d=np.diff((p>n)-0.5)
    ts=np.nonzero(d!=0)[0] # optimisation: https://github.com/numpy/numpy/issues/11569
    t0s=[]
    for ti in ts:
        t1,t2=t[ti:ti+2]
        if is_fix_thresh:
            y1,y2=p[ti:ti+2]-fix_thresh
        else:    
            y1,y2=p[ti:ti+2]-n[ti:ti+2]
        t0=t1-y1*(t2-t1)/(y2-y1)
        t0s.append((t0,d[ti]))
    return t0s

def zs_to_trains(t0s):
    if type(t0s) is not list:
        t0s = t0s.tolist()
        t0s = t0s[:next((i for i in range(len(t0s)) if np.isnan(t0s[i][0])), len(t0s))]
    lastt=-np.inf
    edges=[]
    t0s.append((np.inf,0.))
    trains=[]
    bad_trains=[]
    for t,dy in t0s:
        dt=t-lastt
        lastt=t
        if dt>MIN_SEP:
            if len(edges)%4==0:
                while len(edges)>0:
                    trains.append(edges[:4])
                    edges=edges[4:]
            elif len(edges)>0:
                bad_trains.append(edges)
            edges=[]
        if len(edges)==0:
            if dy>0:
                 edges.append(t)
        else:
            edges.append(t)
    return trains,bad_trains

def decode(*args,**kwargs):
    return zs_to_trains(zero_suppress(*args,**kwargs))

def trains_to_gid_pid(trains):
    gps = []
    for edges in trains:
        pid = edges[2]-edges[0]
        gid = edges[3]-edges[2]
        gps.append((gid,pid))
    return gps
    
def min_dist(m,v):
    d = np.sum((m-v)**2,axis=2)
    return np.unravel_index(d.argmin(),d.shape)

def trains_to_pix(calibration,trains,bad_trains,falling_edge=False,fhr=False):
    # if calibration is a tuple, assume 0: rising, 1: falling
    # and return a tuple of rising and falling
    gps = trains_to_gid_pid(trains)
    if len(bad_trains)>0 and len(gps)==0:
        return [(-1,-1)]
    # assume first half of trains are rising, second falling, round up higher for rising
    if isinstance(calibration,(tuple,list)):
        # for fhr assume risng and falling pairs, i.e. r,f,r,f...
        if fhr:
            pixels_rising  = [min_dist(calibration[0],gps[i]) for i in range(len(gps)) if i % 2 == 0]
            pixels_falling = [min_dist(calibration[1],gps[i]) for i in range(len(gps)) if i % 2 == 1]
        else:
            pixels_rising  = [min_dist(calibration[0],gp) for gp in gps[:int(len(gps)/2+0.5)]]
            pixels_falling = [min_dist(calibration[1],gp) for gp in gps[int(len(gps)/2+0.5):]]
        return (pixels_rising,pixels_falling)
    elif falling_edge:
        return [min_dist(calibration,gp) for gp in gps[int(len(gps)/2+0.5):]]
    else:
        return [min_dist(calibration,gp) for gp in gps[:int(len(gps)/2+0.5)]]


def zs_to_pix(calibration,t0s,falling_edge=False):
    return trains_to_pix(calibration,*zs_to_trains(t0s),falling_edge=falling_edge)

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='DPTS decoder')
    parser.add_argument('filename')
    parser.add_argument('--plot','-p',action='store_true',default=False)
    parser.add_argument('--only-pos',action='store_true',default=False)
    parser.add_argument('--invert',action='store_true',default=False)
    parser.add_argument('--fix-thresh',type=int,default=-1)
    args = parser.parse_args()

    if args.filename.endswith('.csv'):
        d=np.genfromtxt(args.filename,delimiter=',',skip_header=1)
        t=d[:,1]*1e-9
        p=d[:,2]*1e-3
        n=d[:,3]*1e-3
    elif args.filename.endswith('.npy'):
        d=np.load(args.filename)
        if d.shape[0]==3:
            t=d[0,:]*1e-9
            p=d[1,:]*1e-3
            n=d[2,:]*1e-3
        elif d.shape[0]==2:
            t=np.linspace(0,d.shape[1]*2e-10,d.shape[1],endpoint=False)
            p=d[0,:]*0.006151574803149607*256
            n=d[1,:]*0.006151574803149607*256
    trains,bad_trains=decode(t,p,n,args.invert,args.only_pos,args.fix_thresh)
    for edges in trains:
        tpid=edges[2]-edges[0]
        tgid=edges[3]-edges[2]
        print('Train at %8.0f ns: Tpid (3-1) = %.2f ns, Tgid (4-3) = %.2f ns'%(1e9*edges[0],1e9*tpid,1e9*tgid))
    for edges in bad_trains:
        print('bad pattern',edges)
    if args.plot:
        import matplotlib.pyplot as plt
        plt.plot(t,p)
        plt.plot(t,n)
        plt.show()


