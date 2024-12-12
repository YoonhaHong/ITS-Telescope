#!/usr/bin/env python3

import ROOT
import numpy as np
from utils_source_fit import common as f

def BKG_linear(x, p):
    if (x[0]<p[2] and x[0]>p[3]):
        ROOT.TF1.RejectPoint()
        return 0
    return p[0] + p[1]*x[0]

def peak_analysis(npzfile,h,h_res,hBkg,hBkg_res,par,fname,nBIN,dx,resultPeak1,resultPeak2,tot_events):
    f.histoSettings(h_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    f.histoSettings(hBkg_res,'',"Fractional difference",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    h.GetXaxis().SetTitle("Calibrated ToT (mV)")
    h_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing " + par['name'] + " peak...")
    cAr = ROOT.TCanvas('cAr', 'cAr', 5, 5, 1300, 800)
    cAr,pad1Ar,pad2Ar,pad3Ar,pad4Ar,pad5Ar = f.padBackgroundAndSignal(cAr)
    f.printTitle(pad1Ar,"Background and signal fit for " + par['name'] + " peak",npzfile)
    pad2Ar.cd()
    h.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    h_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    hBkg_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    # define function for linear background fit
    lin_bkg_pAr = ROOT.TF1("lin_bkg_pAr",BKG_linear,par['xmin_bkg'],par['xmax_bkg'],4)
    lin_bkg_pAr.SetParNames("p_{0}","p_{1}")
    lin_bkg_pAr.SetParameter(0,3500)
    lin_bkg_pAr.SetParameter(1,3)
    lin_bkg_pAr.SetParameter(2,par['xcut_max'])
    lin_bkg_pAr.SetParameter(3,par['xcut_min'])
    hBkg.Fit(lin_bkg_pAr,"RQ")
    # define function for visualization
    lin_bkg_rejected = ROOT.TF1("lin_bkg_fin","pol1",par['xcut_min'],par['xcut_max'],2)
    f.TF1Settings(lin_bkg_rejected,f.bkg_color,2,3)
    lin_bkg_rejected.SetParameters(lin_bkg_pAr.GetParameters())
    lin_bkg_L = ROOT.TF1("lin_bkg_L","pol1",par['xmin_bkg'],par['xcut_min'],2)
    f.TF1Settings(lin_bkg_L,f.bkg_color,2,1)
    lin_bkg_L.SetParameters(lin_bkg_pAr.GetParameters())
    lin_bkg_R = ROOT.TF1("lin_bkg_R","pol1",par['xcut_max'],par['xmax_bkg'],2)
    f.TF1Settings(lin_bkg_R,f.bkg_color,2,1)
    lin_bkg_R.SetParameters(lin_bkg_pAr.GetParameters())
    # BACKGROUND visualization
    pad2Ar.cd()
    hBkg.Draw("HIST,E,X0")
    lin_bkg_rejected.Draw("SAME")
    lin_bkg_L.Draw("SAME")
    lin_bkg_R.Draw("SAME")
    pad2Ar.cd().Update()
    stat_p11Ar = f.statsPositioned(hBkg,0.63,0.95,0.58,0.86)
    stat_p11Ar.Draw("SAME")
    legend_p11Ar = ROOT.TLegend(0.63,0.41,0.95,0.57)
    legend_p11Ar.AddEntry(lin_bkg_L," lin bkg","l")
    legend_p11Ar.AddEntry(lin_bkg_rejected," excluded bkg","l")
    legend_p11Ar.Draw()
    pad2Ar.cd().Update()

    pad4Ar.cd()
    # define functions for preliminary fit
    gausAr = ROOT.TF1("gausAr","gaus",par['xmin_fit_1'],par['xmax_fit_1'])
    gausSnLa = ROOT.TF1("gausSnLa","gaus",par['xmin_fit_2'],par['xmax_fit_2'])
    h.Fit(gausAr,"RQ")
    h.Fit(gausSnLa,"RQ")
    # function for final fit
    peakArSn = ROOT.TF1("peakArSn","gaus(0)+gaus(3)+pol1(6)",par['xmin_fit'],par['xmax_fit'])
    peakArSn.SetParNames("A K#alpha","#mu K#alpha","#sigma K#alpha","A K#beta","#mu K#beta","#sigma K#beta","p_{0}","p_{1}")
    peakArSn.SetParameter(0,gausAr.GetParameter(0))
    peakArSn.SetParameter(1,gausAr.GetParameter(1))
    peakArSn.SetParameter(2,gausAr.GetParameter(2))
    peakArSn.SetParameter(3,gausSnLa.GetParameter(0))
    peakArSn.SetParameter(4,gausSnLa.GetParameter(1))
    peakArSn.SetParameter(5,gausSnLa.GetParameter(2))
    peakArSn.FixParameter(6,lin_bkg_pAr.GetParameter(0))
    peakArSn.FixParameter(7,lin_bkg_pAr.GetParameter(1))
    h.Fit(peakArSn,"R")
    # signal Ka only
    peakAr_signal = ROOT.TF1("peakAr_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peakAr_signal,f.signal_color,2,1)
    peakAr_signal.FixParameter(0,peakArSn.GetParameter(0))
    peakAr_signal.FixParameter(1,peakArSn.GetParameter(1))
    peakAr_signal.FixParameter(2,peakArSn.GetParameter(2))
    # signal Kb only
    peakSnLa_signal = ROOT.TF1("peakSnLa_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peakSnLa_signal,f.signal_color+2,2,1)
    peakSnLa_signal.FixParameter(0,peakArSn.GetParameter(3))
    peakSnLa_signal.FixParameter(1,peakArSn.GetParameter(4))
    peakSnLa_signal.FixParameter(2,peakArSn.GetParameter(5))
    # visualize
    h.Draw("HIST,E,X0")
    peakAr_signal.Draw("SAME")
    peakSnLa_signal.Draw("SAME")
    peakArSn.Draw("SAME")
    pad4Ar.cd().Update()
    stat_p45 = f.statsPositioned(h,0.63,0.95,0.48,0.86)
    stat_p45.Draw("SAME")
    legend_p45 = ROOT.TLegend(0.63,0.31,0.95,0.47)
    legend_p45.AddEntry(peakArSn," gaus signals + background","l")
    legend_p45.AddEntry(peakAr_signal," signal Ar K#alpha","l")
    legend_p45.AddEntry(peakSnLa_signal," signal Sn L#alpha","l")
    legend_p45.Draw()
    pad4Ar.cd().Update()
    # RESIDUALS
    f.residuals_background(hBkg,hBkg_res,lin_bkg_pAr,pad3Ar,par['xmin_bkg'],par['xcut_min'],par['xcut_max'],par['xmax_bkg'],nBIN)
    f.residuals_signal(h,h_res,peakArSn,pad5Ar,par['xmin_fit'],par['xmax_fit'],nBIN)


    cAr.cd()
    cAr.Print(fname)
    p4_events = int(peakAr_signal.Integral(0,10000)/dx)
    p5_events = int(peakSnLa_signal.Integral(0,10000)/dx)
    p4_resolution = 100.*2.35*peakArSn.GetParameter(2)/peakArSn.GetParameter(1)
    p4_resolution_err = 100.*f.std_dev(2.35*peakArSn.GetParameter(2),2.35*peakArSn.GetParError(2),peakArSn.GetParameter(1),peakArSn.GetParError(1))
    p5_resolution = 100.*2.35*peakArSn.GetParameter(5)/peakArSn.GetParameter(4)
    p5_resolution_err = 100.*f.std_dev(2.35*peakArSn.GetParameter(5),2.35*peakArSn.GetParError(5),peakArSn.GetParameter(4),peakArSn.GetParError(4))
    print("  INFO PEAK Ar Ka:")
    print(" Events:     ",p4_events,"+-",np.sqrt(p4_events))
    print(" FWHM:       ",2.35*peakArSn.GetParameter(2),"+-",2.35*peakArSn.GetParError(2))
    print(" Resolution: ",p4_resolution,"+-",p4_resolution_err)
    tot_events += p4_events
    print("  INFO PEAK Sn La:")
    print(" Events:     ",p5_events,"+-",np.sqrt(p5_events))
    print(" FWHM:       ",2.35*peakArSn.GetParameter(5),"+-",2.35*peakArSn.GetParError(5))
    print(" Resolution: ",p5_resolution,"+-",p5_resolution_err)
    tot_events += p5_events

    resultPeak1["events"] = p4_events
    resultPeak1["p0"] = peakArSn.GetParameter(0)
    resultPeak1["mean"] = peakArSn.GetParameter(1)
    resultPeak1["err mean"] = peakArSn.GetParError(1)
    resultPeak1["sigma"] = peakArSn.GetParameter(2)
    resultPeak1["err sigma"] = peakArSn.GetParError(2)
    resultPeak1["resolution"] = p4_resolution
    resultPeak1["err resolution"] = p4_resolution_err
    resultPeak2["events"] = p5_events
    resultPeak2["p3"] = peakArSn.GetParameter(3)
    resultPeak2["mean"] = peakArSn.GetParameter(4)
    resultPeak2["err mean"] = peakArSn.GetParError(4)
    resultPeak2["sigma"] = peakArSn.GetParameter(5)
    resultPeak2["err sigma"] = peakArSn.GetParError(5)
    resultPeak2["resolution"] = p5_resolution
    resultPeak2["err resolution"] = p5_resolution_err

    return resultPeak1, resultPeak2, tot_events

def peak_analysis1(npzfile,h,h_res,hBkg,hBkg_res,par,fname,nBIN,dx,resultPeak1,resultPeak2,tot_events):
    f.histoSettings(h_res,'',"Residuals",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    f.histoSettings(hBkg_res,'',"Residuals",0.07,0.07,0.6,"Calibrated ToT (mV)",0.07,0.07,0.0)
    h.GetXaxis().SetTitle("Calibrated ToT (mV)")
    h_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg.GetXaxis().SetTitle("Calibrated ToT (mV)")
    hBkg_res.GetXaxis().SetTitle("Calibrated ToT (mV)")
    print("="*150)
    print("   [INFO] Processing " + par['name'] + " peak...")
    cAr = ROOT.TCanvas('cAr', 'cAr', 5, 5, 1300, 800)
    cAr,pad1Ar,pad2Ar,pad3Ar,pad4Ar,pad5Ar = f.padBackgroundAndSignal(cAr)
    f.printTitle(pad1Ar,"Background and signal fit for " + par['name'] + " peak",npzfile)
    pad2Ar.cd()
    h.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    h.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    h_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    hBkg.GetYaxis().SetRangeUser(par['ymin'],par['ymax'])
    hBkg_res.GetXaxis().SetRangeUser(par['xmin'],par['xmax'])
    # define function for linear background
    lin_bkg = ROOT.TF1("lin_bkg",BKG_linear,par['xmin_bkg'],par['xmax_bkg'],4)
    lin_bkg.SetParNames("p_{0}","p_{1}")
    lin_bkg.SetParameter(0,3500)
    lin_bkg.SetParameter(1,3)
    lin_bkg.FixParameter(2,par['xcut_max'])
    lin_bkg.FixParameter(3,par['xcut_min'])
    hBkg.Fit(lin_bkg,"RQ")
    # define function for visualization
    lin_bkg_rejected = ROOT.TF1("lin_bkg_rejected","pol1",par['xcut_min'],par['xcut_max'],2)
    f.TF1Settings(lin_bkg_rejected,f.bkg_color,2,3)
    lin_bkg_rejected.SetParameters(lin_bkg.GetParameters())
    lin_bkg_L = ROOT.TF1("lin_bkg_L","pol1",par['xmin_bkg'],par['xcut_min'],2)
    f.TF1Settings(lin_bkg_L,f.bkg_color,2,1)
    lin_bkg_L.SetParameters(lin_bkg.GetParameters())
    lin_bkg_R = ROOT.TF1("lin_bkg_R","pol1",par['xcut_max'],par['xmax_bkg'],2)
    f.TF1Settings(lin_bkg_R,f.bkg_color,2,1)
    lin_bkg_R.SetParameters(lin_bkg.GetParameters())
    # BACKGROUND visualization
    hBkg.Draw("HIST,E,X0")
    lin_bkg_rejected.Draw("SAME")
    lin_bkg_L.Draw("SAME")
    lin_bkg_R.Draw("SAME")
    pad2Ar.cd().Update()
    stat_p11Ar = f.statsPositioned(hBkg,0.55,0.95,0.65,0.89)
    stat_p11Ar.Draw("SAME")
    legend_p11Ar = ROOT.TLegend(0.55,0.55,0.95,0.64)
    legend_p11Ar.AddEntry(lin_bkg_L," lin bkg","l")
    legend_p11Ar.AddEntry(lin_bkg_rejected," excluded bkg","l")
    legend_p11Ar.Draw()
    pad2Ar.cd().Update()
    # define function for preliminary fit
    pad4Ar.cd()
    gaus1 = ROOT.TF1("gaus1","gaus",par['xmin_fit_1'],par['xmax_fit_1'])
    gaus2 = ROOT.TF1("gaus2","gaus",par['xmin_fit_2'],par['xmax_fit_2'])
    h.Fit(gaus1,"RQ")
    h.Fit(gaus2,"RQ")
    # final fit lin + gaus
    peakAr = ROOT.TF1("peakAr","gaus(0)+gaus(3)+pol1(6)",par['xmin_fit'],par['xmax_fit'],5)
    peakAr.SetParNames("A K#alpha","#mu K#alpha","#sigma K#alpha","A K#beta","#mu K#beta","#sigma K#beta","p_{0}","p_{1}")
    peakAr.SetParameter(0,gaus1.GetParameter(0))
    peakAr.SetParameter(1,gaus1.GetParameter(1))
    peakAr.SetParameter(2,gaus1.GetParameter(2))
    peakAr.SetParameter(3,gaus2.GetParameter(0))
    peakAr.SetParameter(4,gaus2.GetParameter(1))
    peakAr.SetParameter(5,gaus2.GetParameter(2))
    peakAr.FixParameter(6,lin_bkg.GetParameter(0))
    peakAr.FixParameter(7,lin_bkg.GetParameter(1))
    h.Fit(peakAr,"R")
    # signal 1 only
    peakAr_signal = ROOT.TF1("peakAr_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peakAr_signal,f.signal_color,2,1)
    peakAr_signal.FixParameter(0,peakAr.GetParameter(0))
    peakAr_signal.FixParameter(1,peakAr.GetParameter(1))
    peakAr_signal.FixParameter(2,peakAr.GetParameter(2))
    # signal 2 only
    peakSnLa_signal = ROOT.TF1("peakSnLa_signal","gaus",par['xmin'],par['xmax'],3)
    f.TF1Settings(peakSnLa_signal,f.signal_color+2,2,1)
    peakSnLa_signal.FixParameter(0,peakAr.GetParameter(3))
    peakSnLa_signal.FixParameter(1,peakAr.GetParameter(4))
    peakSnLa_signal.FixParameter(2,peakAr.GetParameter(5))
    # visualize
    h.Draw("HIST,E,X0")    
    peakAr_signal.Draw("SAME")
    peakSnLa_signal.Draw("SAME")
    peakAr.Draw("SAME")
    pad4Ar.cd().Update()
    stat_p12Ar = f.statsPositioned(h,0.55,0.95,0.65,0.89)
    stat_p12Ar.Draw("SAME")
    legend_p12Ar = ROOT.TLegend(0.55,0.55,0.95,0.64)
    legend_p12Ar.AddEntry(peakAr," bkg + gaus","l")
    legend_p12Ar.AddEntry(peakAr_signal," signal","l")
    legend_p12Ar.Draw()
    pad4Ar.cd().Update()
    # RESIDUALS
    f.residuals_background(hBkg,hBkg_res,lin_bkg,pad3Ar,par['xmin_fit'],par['xcut_min'],par['xcut_max'],par['xmax_fit'],nBIN)
    f.residuals_signal(h,h_res,peakAr,pad5Ar,par['xmin_fit'],par['xmax_fit'],nBIN)

    cAr.cd()
    cAr.Print(fname)
    p4_events = int(peakAr_signal.Integral(0,10000)/dx)
    p5_events = int(peakSnLa_signal.Integral(0,10000)/dx)
    p4_resolution = 100.*2.35*peakAr.GetParameter(2)/peakAr.GetParameter(1)
    p4_resolution_err = 100.*f.std_dev(2.35*peakAr.GetParameter(2),2.35*peakAr.GetParError(2),peakAr.GetParameter(1),peakAr.GetParError(1))
    p5_resolution = 100.*2.35*peakAr.GetParameter(5)/peakAr.GetParameter(4)
    p5_resolution_err = 100.*f.std_dev(2.35*peakAr.GetParameter(5),2.35*peakAr.GetParError(5),peakAr.GetParameter(4),peakAr.GetParError(4))
    print("  INFO PEAK Ar Ka:")
    print(" Events:     ",p4_events,"+-",np.sqrt(p4_events))
    print(" FWHM:       ",2.35*peakAr.GetParameter(2),"+-",2.35*peakAr.GetParError(2))
    print(" Resolution: ",p4_resolution,"+-",p4_resolution_err)
    tot_events += p4_events
    print("  INFO PEAK Sn La:")
    print(" Events:     ",p5_events,"+-",np.sqrt(p5_events))
    print(" FWHM:       ",2.35*peakAr.GetParameter(5),"+-",2.35*peakAr.GetParError(5))
    print(" Resolution: ",p5_resolution,"+-",p5_resolution_err)
    tot_events += p5_events

    resultPeak1["events"] = p4_events
    resultPeak1["p0"] = peakAr.GetParameter(0)
    resultPeak1["mean"] = peakAr.GetParameter(1)
    resultPeak1["err mean"] = peakAr.GetParError(1)
    resultPeak1["sigma"] = peakAr.GetParameter(2)
    resultPeak1["err sigma"] = peakAr.GetParError(2)
    resultPeak1["resolution"] = p4_resolution
    resultPeak1["err resolution"] = p4_resolution_err
    resultPeak2["events"] = p5_events
    resultPeak2["p3"] = peakAr.GetParameter(3)
    resultPeak2["mean"] = peakAr.GetParameter(4)
    resultPeak2["err mean"] = peakAr.GetParError(4)
    resultPeak2["sigma"] = peakAr.GetParameter(5)
    resultPeak2["err sigma"] = peakAr.GetParError(5)
    resultPeak2["resolution"] = p5_resolution
    resultPeak2["err resolution"] = p5_resolution_err

    return resultPeak1, resultPeak2, tot_events