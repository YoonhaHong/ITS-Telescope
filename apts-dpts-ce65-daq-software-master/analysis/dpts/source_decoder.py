#!/usr/bin/env python3

#=====================================
#
# IMPORTS
#
#=====================================

#general
from matplotlib import pyplot as plt
import numpy as np
import json
import argparse
import os
from tqdm import tqdm
import pathlib
import copy
import collections

#repository specific
from mlr1daqboard import dpts_decoder as decoder
import landau_creator

#=====================================
#
#FUNCTIONS
#
#=====================================


def match_trains(trains, bad_trains, calib_rising, calib_falling, min_gid_pid_in_calibs, use_dumped_waveforms, debug = False):
    #takes trains and decodes them into hits
    if debug: print("-------------------------")
    #define error codes for no possible matching
    error_odd_n_trains = "ERROR_ODD_N_TRAINS"
    error_0_trains =  "ERROR_0_TRAINS"
    error_possible_train_clash = "ERROR_POSS_TRAIN_CLASH"
    error_matching_event_wo_rep_failed = "ERROR_MATCH_EVENT_WO_REP_FAILED"
    error_matching_event_with_rep_failed = "ERROR_MATCH_EVENT_WITH_REP_FAILED"
    error_bad_train = "ERROR_BAD_TRAIN"
    error_out_of_time = "ERROR_OUT_OF_TIME"

    #will contain information of the matched pixels
    col_lst = []
    row_lst = []
    rising_edge_lst = []
    falling_edge_lst = []

    #list for control plot
    train_combinations = []

    #flags for control plots
    fully_matched = False
    case_directly_matched = False
    case_wo_rep_matched = False
    case_with_rep_matched = False
    case_with_rep_jst_on_rising = False
    case_with_rep_jst_on_falling = False
    case_with_rep_on_both_sides = False

    if debug: print("[DEBUG] len(trains): ", len(trains))

    #------------------------------------------------
    # Try to match events with even number of  trains
    #------------------------------------------------
    if len(trains)>0:
        if (len(trains) % 2) == 0: #Decode even trains with first half rising edge, second half falling edge

            #------------------------------------------------
            # Check for bad_trains
            #------------------------------------------------
            if(len(bad_trains) > 0): return error_bad_train

            #----------------------------------------------------------------------------
            # Check for events out of time (Events with two events in the same waveform)
            #----------------------------------------------------------------------------
            if use_dumped_waveforms:
                if trains[:len(trains)//2][-1][0] > 3000e-9:
                    if debug:
                        print("[DEBUG] Event out of time!")
                        print("      | trains[:len(trains)//2][-1][0]", round(trains[:len(trains)//2][-1][0]*1e9,1))
                        gps = decoder.trains_to_gid_pid(trains)
                        print("      | gps:", [[((round(e[0]*1e9,1)), round(e[1]*1e9,1)) for e in gps]])
                        if debug: print("[DEBUG] Event out of time. Discard.")
                    return error_out_of_time

            elif not use_dumped_waveforms:
                if trains[:len(trains)//2][-1][0] > 1e-6:
                    if debug:
                        print("[DEBUG] Event out of time!")
                        print("      | trains[:len(trains)//2][-1][0]", trains[:len(trains)//2][-1][0])
                        gps = decoder.trains_to_gid_pid(trains)
                        print("      | gps:", [[((round(e[0]*1e9,1)), round(e[1]*1e9,1)) for e in gps]])
                        if debug: print("[DEBUG] Event out of time. Discard.")
                    return error_out_of_time
            else:
                print("[ERROR] In match_trains: use_dumped_waveforms not specified. This should not happen!")
                exit()

            #------------------------------------------------
            # Check for possible train clashes
            #------------------------------------------------
            #define tolerances
            margin_gid = 1*(np.abs(min_gid_pid_in_calibs[2] - min_gid_pid_in_calibs[0]) /32)#distance between max and min GID in *both* calibs (will lead to a slight overestimation)
            margin_pid = 1*(np.abs(min_gid_pid_in_calibs[3] - min_gid_pid_in_calibs[1]) /32)#analogue to above
            #define minimum gid and minimum pid cut
            cut_min_gid = (min_gid_pid_in_calibs[0] - margin_gid)
            cut_min_pid = (min_gid_pid_in_calibs[1] - margin_pid)
            for trn in trains:
                gp = decoder.trains_to_gid_pid([trn])
                #if the gid pids are smaller than the smallest of the decoding calibration (minus margin) its probably a train clash
                if (gp[0][0] < cut_min_gid) or (gp[0][1] < cut_min_pid):
                    if debug: print("[DEBUG] Possible clash of trains. Discard. ")
                    return error_possible_train_clash

            decoded_pixel_lst = [] #will contain the pixels in the correct order (corresponding to train arrival)
            decoded_pixel_lst_nested = decoder.trains_to_pix((calib_rising, calib_falling), trains, bad_trains)
            decoded_px_rising  = decoded_pixel_lst_nested[0]
            decoded_px_falling = decoded_pixel_lst_nested[1]
            decoded_pixel_lst = [x for xs in decoded_pixel_lst_nested for x in xs]#flatten list for further processing

            if debug:
                print("[DEBUG] trains: ", trains)
                print("[DEBUG] bad_trains: ", bad_trains)
                print("[DEBUG] decoded_pixel_lst: ", decoded_pixel_lst)

            #--------------------------------------------------------
            # Get intersection of first and second half of the trains
            #--------------------------------------------------------
            # find intersection of first half (rising edge) and second half (falling edge) of decoded_pixel_lst
            intersection =list(set(decoded_px_rising) & set(decoded_px_falling))

            if debug:
                print("[DEBUG] decoded_px_rising: ", decoded_px_rising)
                print("[DEBUG] decoded_px_falling: ", decoded_px_falling)
                print("[DEBUG] intersection: ", intersection)

            #--------------------------------------
            # Match here just fully matched events
            #--------------------------------------
            if len(intersection) == len(decoded_pixel_lst)/2: #check if pixels in first half of decoded_pixel_lst match pixels in the second half
                col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_pixel_lst, intersection, decoded_px_rising, decoded_px_falling, trains)
                case_directly_matched = True
                fully_matched = True
                if debug: print("[DEBUG] Fully matched.")
                return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations

            #------------------------------------------------
            # Try to match partly matched events
            #------------------------------------------------
            elif len(intersection) < len(decoded_pixel_lst)/2: #sanity check
                decoded_pxs = decoded_px_rising + decoded_px_falling #merge rising and falling lst
                #check if we have a case with or without repetition (e.g two times the same pixel in either the rising or the falling edge part)
                selfintersec_rise =list(set(decoded_px_rising) & set(decoded_px_rising))
                selfintersec_fall =list(set(decoded_px_falling) & set(decoded_px_falling))

                #------------------------------------------------------
                # Handle cases with repetition
                #------------------------------------------------------
                if len(selfintersec_rise)<len(decoded_px_rising) or len(selfintersec_fall)<len(decoded_px_falling):
                    #------------------------------------------------------
                    # Resolve repetitions
                    #------------------------------------------------------
                    #------------------------------------------------------
                    # Handle case with repetition just on rising-edge side
                    #------------------------------------------------------
                    if len(selfintersec_rise)<len(decoded_px_rising) and not len(selfintersec_fall)<len(decoded_px_falling):
                        case_with_rep_jst_on_rising = True
                        if debug: print("[DEBUG] Repetition just on Rising")
                        #get repetitive pixels
                        px_rep = get_rep_pixs(decoded_px_rising)
                        #resolve repetition
                        decoded_px_rising_wo_rep, idx_alr_reev = resolve_repetition(decoded_pxs, trains, bad_trains, calib_rising, calib_falling, rof="rising")
                        decoded_px_wo_rep = decoded_px_rising_wo_rep + decoded_px_falling
                    #-------------------------------------------------------
                    # Handle case with repetition just on falling-edge side
                    #-------------------------------------------------------
                    elif len(selfintersec_fall)<len(decoded_px_falling) and not len(selfintersec_rise)<len(decoded_px_rising):
                        case_with_rep_jst_on_falling = True
                        if debug: print("[DEBUG] Repetition just on Falling")
                        #get repetitive pixels
                        px_rep = get_rep_pixs(decoded_px_falling)
                        #resolve repetition
                        decoded_px_falling_wo_rep, idx_alr_reev = resolve_repetition(decoded_pxs, trains, bad_trains, calib_rising, calib_falling, rof="falling")
                        decoded_px_wo_rep = decoded_px_rising + decoded_px_falling_wo_rep
                    #------------------------------------------------
                    # Handle case with repetition on both sides
                    #------------------------------------------------
                    elif len(selfintersec_fall)<len(decoded_px_falling) and len(selfintersec_rise)<len(decoded_px_rising):
                        case_with_rep_on_both_sides = True
                        if debug: print("[DEBUG] Repetition on Rising & Falling")
                        #get repetitive pixels
                        px_rep_rising = get_rep_pixs(decoded_px_rising)
                        px_rep_falling = get_rep_pixs(decoded_px_falling)
                        px_rep = px_rep_rising + px_rep_falling
                        #resolve repetition
                        decoded_px_rising_wo_rep, idx_alr_reev_rising = resolve_repetition(decoded_pxs, trains, bad_trains, calib_rising, calib_falling, rof="rising")
                        decoded_px_falling_wo_rep, idx_alr_reev_falling = resolve_repetition(decoded_pxs, trains, bad_trains, calib_rising, calib_falling, rof="falling")
                        decoded_px_wo_rep = decoded_px_rising_wo_rep + decoded_px_falling_wo_rep
                        idx_alr_reev = idx_alr_reev_rising + idx_alr_reev_falling
                    else:
                        print("[ERROR] Detected repetition in event, but its neither in rising nor in falling edge. That should not happen!")
                        exit()
                    #--------------------------------------------------------------------------------------------------------
                    # Handle resolved repetitions (different treatment than below since some trains are already reevaluated)
                    #--------------------------------------------------------------------------------------------------------
                    #check if the event matches already after repetition resolution
                    decoded_px_wo_rep_rising = decoded_px_wo_rep[:len(decoded_px_wo_rep)//2]
                    decoded_px_wo_rep_falling = decoded_px_wo_rep[(len(decoded_px_wo_rep)//2):]
                    intersec_wo_rep =list(set(decoded_px_wo_rep_rising) & set(decoded_px_wo_rep_falling))
                    if debug: 
                        print("[DEBUG] px_rep", px_rep)
                        print("[DEBUG] decoded_px_wo_rep", decoded_px_wo_rep)
                    if len(intersec_wo_rep) == len(decoded_px_wo_rep)/2:
                        if debug: print("[DEBUG] Alredy fully matchable after repetition resolution!")
                        col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_px_wo_rep, intersec_wo_rep, decoded_px_wo_rep_rising, decoded_px_wo_rep_falling, trains)
                        fully_matched = True
                        case_with_rep_matched = True
                        if debug: print("[DEBUG] Fully matched.")
                        return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations
                    else:
                        if debug: print("[DEBUG] Still some work to do after repetition resolition.")
                        #find out wich pxs already matched and which ones need to be reevaluated
                        already_matched_trn_idxs, unmatched_trn_idxs =  get_matched_unmatched_indxs_for_non_repetitive_lsts(decoded_px_wo_rep_rising, decoded_px_wo_rep_falling, intersec_wo_rep)
                        #get CoG distances
                        CoG_dists_unm = get_CoG_dists(unmatched_trn_idxs, decoded_px_wo_rep, trains, calib_rising, calib_falling)
                        #get upper half indices from CoG_dist_unm
                        idx_of_trns_to_reevaluate_unchecked = get_idxs_of_trns_sorted_by_CoG_dist(CoG_dists_unm)[(len(CoG_dists_unm)//2):]
                        idx_of_trns_to_reevaluate = [x for x in idx_of_trns_to_reevaluate_unchecked if x not in idx_alr_reev] #dont reevaluate pixels which were already reevaluated
                        
                        #if the list of trns to reevalutate is empty, we have to decide on another pixel
                        if(len(idx_of_trns_to_reevaluate)==0):
                            # decide on another pixel
                            if debug: print("[DEBUG] Pixel to reevaluate already reevaluated. Looking for the next case")
                            idxs_sorted_by_CoG_dist = get_idxs_of_trns_sorted_by_CoG_dist(CoG_dists_unm) #highest distance comes last
                            if debug: print("[DEBUG] CoG_dists_unm", CoG_dists_unm)
                            if debug: print("[DEBUG] idxs_sorted_by_CoG_dist",idxs_sorted_by_CoG_dist)
                            # is this one already in idx_alr_reev? If no, reevaluate, if yes take next one
                            idxs_possible_additional_reevaluations = []
                            for k in range(0,len(idxs_sorted_by_CoG_dist)):
                                if debug:
                                    print("      | .........")
                                    print("      | k", k)
                                    print("      | idxs_sorted_by_CoG_dist[k]", idxs_sorted_by_CoG_dist[k])
                                    print("      | idx_alr_reev", idx_alr_reev)
                                    print("      | decoded_px_wo_rep[idxs_sorted_by_CoG_dist[k]]", decoded_px_wo_rep[idxs_sorted_by_CoG_dist[k]])
                                    print("      | px_rep",px_rep)

                                if idxs_sorted_by_CoG_dist[k] not in idx_alr_reev \
                                    and decoded_px_wo_rep[idxs_sorted_by_CoG_dist[k]] not in px_rep:
                                    idxs_possible_additional_reevaluations.append(idxs_sorted_by_CoG_dist[k])
                                    if debug: print("      | This case will be reevaluated (neither a rep pix nor alr reev)! idx:", idxs_sorted_by_CoG_dist[k])
                                elif debug: print("      | This case will not be reev (either a rep pix nor alr reev)!")
                            if debug: print("[DEBUG] Could additionally reev idx:", idxs_possible_additional_reevaluations)
                            #reevaluate
                            idx_of_trns_to_reevaluate = idxs_possible_additional_reevaluations
                            if debug: print("[DEBUG] idx_of_trns_to_reevaluate", idx_of_trns_to_reevaluate)
                            #continue with this new list

                        #reevaluate
                        decoded_pxs_reev = get_decoded_px_reev(calib_rising, calib_falling, trains, bad_trains, decoded_px_wo_rep, idx_of_trns_to_reevaluate)
                        if debug:
                            print("[DEBUG] idx_of_trns_to_reevaluate_unchecked", idx_of_trns_to_reevaluate_unchecked)
                            print("[DEBUG] idx_alr_reev", idx_alr_reev)
                            print("[DEBUG] decoded_pxs_reev", decoded_pxs_reev)

                        #check if we have now full match, otherwise do further checks
                        decoded_px_rising_reev, decoded_px_falling_reev, intersec_reev = get_intersec(decoded_pxs_reev)

                        if len(intersec_reev) == len(decoded_pxs_reev)/2:
                            if debug: print("[DEBUG] Full match after reevaluation!")
                            col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_pxs_reev, intersec_reev, decoded_px_rising_reev, decoded_px_falling_reev, trains)
                            fully_matched = True
                            case_with_rep_matched = True
                            return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations
                        
                        else:
                            #See if there are just two pixels unmatched, if so match them
                            mat_indxs, unm_indxs = get_matched_unmatched_indxs_for_non_repetitive_lsts(decoded_px_rising_reev, decoded_px_falling_reev, intersec_reev)
                            if debug: print("[DEBUG] Still unmatched: ", unm_indxs)
                            #check if just two pixels unmatched
                            if len(unm_indxs) == 2 and len(decoded_pxs_reev) > 2:
                                #find out which column to pass and match
                                if debug: print("[DEBUG] Matching remaining two pixels")
                                cogdists = get_CoG_dists(unm_indxs, decoded_pxs_reev, trains, calib_rising, calib_falling)
                                cogs_sorted = get_idxs_of_trns_sorted_by_CoG_dist(cogdists) #highest distance comes last
                                good_px_idx = cogs_sorted[0]
                                bad_px_idx = cogs_sorted[-1]
                                #replace now the bad pixel by the good pixel to be able to call match_fully
                                decoded_pxs_reev_replaced = copy.deepcopy(decoded_pxs_reev)
                                decoded_pxs_reev_replaced[bad_px_idx] = decoded_pxs_reev[good_px_idx]
                                if debug: print("[DEBUG] decoded_pxs_reev_replaced", decoded_pxs_reev_replaced)

                                #get rising falling list and intersection before fully matching
                                decoded_pxs_rising_reev_replaced, decoded_pxs_falling_reev_replaced, intersec_reev_replaced = get_intersec(decoded_pxs_reev_replaced)
                                selfintersec_rise_replaced =list(set(decoded_pxs_rising_reev_replaced) & set(decoded_pxs_rising_reev_replaced))
                                selfintersec_fall_replaced =list(set(decoded_pxs_falling_reev_replaced) & set(decoded_pxs_falling_reev_replaced))

                                #check if no repetition is occuring now
                                if len(selfintersec_rise_replaced)==len(decoded_pxs_rising_reev_replaced) and len(selfintersec_fall_replaced)==len(decoded_pxs_falling_reev_replaced):
                                    col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_pxs_reev_replaced, intersec_reev_replaced, decoded_pxs_rising_reev_replaced, decoded_pxs_falling_reev_replaced, trains)
                                    fully_matched = True
                                    case_with_rep_matched = True
                                    if debug: print("[DEBUG] Fully matched the neighbours.")
                                    return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations
                                else:
                                    if debug: print("[DEBUG] Event with repetition could not be matched, even after reevaluation. Discard.")
                                    return error_matching_event_with_rep_failed
                                    
                            else:
                                if debug: print("[DEBUG] Event with repetition could not be matched, even after reevaluation. Discard.")
                                return error_matching_event_with_rep_failed

                #------------------------------------------------
                # Handle case without any repetition
                #------------------------------------------------
                elif len(selfintersec_rise)==len(decoded_px_rising) and len(selfintersec_fall)==len(decoded_px_falling):
                    if debug:
                        print("[DEBUG] Case with no repetition")
                        print("[DEBUG] decoded_pxs", decoded_pxs)

                    #find out wich pxs already matched and which ones need to be reevaluated
                    already_matched_trn_idxs, unmatched_trn_idxs =  get_matched_unmatched_indxs_for_non_repetitive_lsts(decoded_px_rising, decoded_px_falling, intersection)
                    if debug: print("[DEBUG] unmatched_trn_idxs", unmatched_trn_idxs)
                    #get CoG distances
                    CoG_dists_unm = get_CoG_dists(unmatched_trn_idxs, decoded_pxs, trains, calib_rising, calib_falling)
                    if debug: print("[DEBUG] CoG_dists_unm", CoG_dists_unm)
                    #get upper half indices from CoG_dist_unm
                    idx_of_trns_to_reevaluate = get_idxs_of_trns_sorted_by_CoG_dist(CoG_dists_unm)[(len(CoG_dists_unm)//2):]
                    if debug: print("[DEBUG] idx_of_trns_to_reevaluate", idx_of_trns_to_reevaluate)

                    if(len(idx_of_trns_to_reevaluate)==0):
                        print("[WARNING] idx_of_trns_to_reevaluate is empty! For a case without repetition, this should not happen (since there is no pixel already reevaluated or no pixel was repetitive before) ")
                        exit()

                    #reevaluate the upper half indices
                    decoded_pxs_reev = get_decoded_px_reev(calib_rising, calib_falling, trains, bad_trains, decoded_pxs, idx_of_trns_to_reevaluate)
                    if debug: print("[DEBUG] decoded_pxs_reev",decoded_pxs_reev)

                    #check if we have now full match,otherwise trash
                    decoded_px_rising_reev, decoded_px_falling_reev, intersec_reev = get_intersec(decoded_pxs_reev)

                    if len(intersec_reev) == len(decoded_pxs_reev)/2:
                        if debug: print("[DEBUG] Full match after reevaluation.")
                        #count and do the matching!
                        col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_pxs_reev, intersec_reev, decoded_px_rising_reev, decoded_px_falling_reev, trains)
                        fully_matched = True
                        case_wo_rep_matched = True
                        if debug: print("[DEBUG] Fully matched.")
                        return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations

                    else:
                            #See if there are just two pixels unmatched, if so match them
                            mat_indxs, unm_indxs = get_matched_unmatched_indxs_for_non_repetitive_lsts(decoded_px_rising_reev, decoded_px_falling_reev, intersec_reev)
                            if debug: print("[DEBUG] Still unmatched idxs: ", unm_indxs)
                            #check if just two pixels unmatched
                            if len(unm_indxs) == 2 and len(decoded_pxs_reev) > 2:
                            #if just two pixels are left unmatched, match them!
                                if debug: print("[DEBUG]Just two pix are unmatched. They will be matched.")
                                #find out which column to pass and match
                                cogdists = get_CoG_dists(unm_indxs, decoded_pxs_reev, trains, calib_rising, calib_falling)
                                if debug: print("[DEBUG] cogdists", cogdists)
                                cogs_sorted = get_idxs_of_trns_sorted_by_CoG_dist(cogdists) #highest distance comes last
                                good_px_idx = cogs_sorted[0]
                                bad_px_idx = cogs_sorted[-1]
                                if debug: 
                                    print("[DEBUG] good_px_idx", good_px_idx)
                                    print("[DEBUG] bad_px_idx", bad_px_idx)
                                #replace now the bad pixel by the good pixel to be able to call match_fully
                                decoded_pxs_reev_replaced = copy.deepcopy(decoded_pxs_reev)
                                decoded_pxs_reev_replaced[bad_px_idx] = decoded_pxs_reev[good_px_idx]
                                if debug: print("[DEBUG] decoded_pxs_reev_replaced", decoded_pxs_reev_replaced)

                                #get rising falling list and intersection before fully matching
                                decoded_pxs_rising_reev_replaced, decoded_pxs_falling_reev_replaced, intersec_reev_replaced = get_intersec(decoded_pxs_reev_replaced)
                                selfintersec_rise_replaced =list(set(decoded_pxs_rising_reev_replaced) & set(decoded_pxs_rising_reev_replaced))
                                selfintersec_fall_replaced =list(set(decoded_pxs_falling_reev_replaced) & set(decoded_pxs_falling_reev_replaced))

                                #check if no repetition is occuring now
                                if len(selfintersec_rise_replaced)==len(decoded_pxs_rising_reev_replaced) and len(selfintersec_fall_replaced)==len(decoded_pxs_falling_reev_replaced):
                                    col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations = match_fully(decoded_pxs_reev_replaced, intersec_reev_replaced, decoded_pxs_rising_reev_replaced, decoded_pxs_falling_reev_replaced, trains)
                                    fully_matched = True
                                    case_with_rep_matched = True
                                    if debug: print("[DEBUG] Fully matched the remaining two pixels.")
                                    return col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations
                                else:
                                    print("[ERROR] Event without repetition could not be matched, even just two pixels are unmatched. This should not happen!")
                                    return error_matching_event_wo_rep_failed
                                    #exit()
                                    
                                    
                            else:
                                if debug: print("[DEBUG] Event without repetition could not be matched, even after reevaluation. Discard.")
                                return error_matching_event_wo_rep_failed
                else:
                    print("[ERROR] Not able to handle this case as event with or without repetition. That should not happen.")
                    exit()
            else:
                print("[ERROR] Intersection longer than half of the trains. That should never happen.")
                exit()

        else:
            #--------------------------------------------------------
            # Return ERROR for events with no or odd number of trains
            #--------------------------------------------------------
            if debug: print("[WARNING] Odd number of trains. Trains could not be matched to pixels properly. Skipping")
            return error_odd_n_trains
    else:
        if debug: print("[WARNING] No trains. Trains could not be matched to pixels properly. Skipping")
        return error_0_trains







def get_intersec(dec_px):
    #returns rising half, falling half and intersection for the provided list of decoded pixels
    dec_px_rising = dec_px[:len(dec_px)//2]
    dec_px_falling = dec_px[(len(dec_px)//2):]
    intersec =list(set(dec_px_rising) & set(dec_px_falling))
    return dec_px_rising, dec_px_falling, intersec


def get_rep_pixs(decoded_px_r_or_f):
    #returns list of repetitive elements in decoded_px_r_or_f
    selfintersec = list(set(decoded_px_r_or_f) & set(decoded_px_r_or_f)) 
    if len(selfintersec) < len(decoded_px_r_or_f):
        return [item for item, count in collections.Counter(decoded_px_r_or_f).items() if count > 1]
    else:
        print("[ERROR] get_rep_pixs() called for non-repetitive list!")
        exit()


def resolve_repetition(decoded_pxs, trains, bad_trains, calib_rising, calib_falling, rof):
    #take decoded_pxs and specification on which half of thr list to decode
    if rof == "rising":
        decoded_px_r_or_f = decoded_pxs[:(len(decoded_pxs)//2)]
    elif rof == "falling":
        decoded_px_r_or_f = decoded_pxs[(len(decoded_pxs)//2):]
    else:
        print("[ERROR] In resolve_repetition: rof undefined. Choose either \"rising\" or \"falling\" ")
        exit()
    #take list with repetition and corresponding calib
    #find the relative indexed of the repetition in th list
    idx_rep = get_abs_indxs_of_repetive_element_in_lst(decoded_px_r_or_f, rof)
    #get list of CoG-distances of thr repetetive indexes
    dists_rep = get_CoG_dists(idx_rep, decoded_pxs, trains, calib_rising, calib_falling)
    #mark one of the repetetive pixels as good
    idx_goodpix = get_idxs_of_trns_sorted_by_CoG_dist(dists_rep)[0]
    #get idxs of trns to reevaluate
    idx_badpix = []
    for i in idx_rep:
        if not i==idx_goodpix: idx_badpix.append(i) #get absolute indexes
    #reevaluate on the others
    #get_decoded_px_reev returns full list, but we are just interested in rising or falling part
    if rof == "rising":
        dec_px_r_or_f_reev = get_decoded_px_reev(calib_rising, calib_falling, trains, bad_trains, decoded_pxs, idx_badpix)[:(len(decoded_pxs)//2)]
    elif rof == "falling":
        dec_px_r_or_f_reev = get_decoded_px_reev(calib_rising, calib_falling, trains, bad_trains, decoded_pxs, idx_badpix)[(len(decoded_pxs)//2):]
    else:
        print("[ERROR] In resolve_repetition: rof undefined. Choose either \"rising\" or \"falling\" ")
        exit()
    return dec_px_r_or_f_reev, idx_badpix #idx_badpix is needed to keep track which pixel was already reevaluated


def get_abs_indxs_of_repetive_element_in_lst(list, rof):
    #returns the ABSOLUTE indxs (so indx in decoded_pxs) of its repetitive elements in list
    dup_idxs_abs = []                                                                                    
    dup = {x for x in list if list.count(x) > 1} #checks for element occuring more than once in list
    if rof == "rising":
        for i, p in enumerate(list):
            if p in dup: dup_idxs_abs.append(i)
    elif rof == "falling":
        for i, p in enumerate(list):
            if p in dup: dup_idxs_abs.append(i+len(list)) # to get the absolute index
    else:
        print("[ERROR] In get_abs_indxs_of_repetive_element_in_lst: rof undefined. Choose either \"rising\" or \"falling\" ")
        exit()
    return dup_idxs_abs


def match_fully(decoded_pixel_lst, intersection, decoded_px_rising, decoded_px_falling, trains):
    #takes care of matching a fully matchable list

    #define lists which will be returned
    col_lst = []
    row_lst = []
    rising_edge_lst = []
    falling_edge_lst = []
    #list for control plot
    train_combinations = []
    if len(intersection) == len(decoded_pixel_lst)/2: #check if pixels in first half of decoded_pixel_lst match pixels in the second half
        for i_rising, px in enumerate(decoded_px_rising):
            if px in intersection: #sanity check
                col_lst.append(px[0])
                row_lst.append(px[1])
                rising_edge_lst.append(trains[i_rising][0]) #edge of the current pixel from first half of decoded_pixel_lst (rising edge)
                i_falling = decoded_px_falling.index(px) #returns index of corresponding pixel in second half of decoded_pixel_lst (falling edge)
                falling_edge_lst.append(trains[len(decoded_px_rising) + i_falling][0])
                #for investigating the order of the matching trains
                train_combinations.append((i_rising, i_falling))
    else: 
        print("[ERROR] match_fully called for a not-fully matched train!")
        exit()
    return col_lst, row_lst, rising_edge_lst, falling_edge_lst, train_combinations


def get_gps_dist(gps_1, gps_2):
    #calculate distance in GID/PID space
    return np.sqrt((gps_1[0][0]-gps_2[0][0])**2 + (gps_1[0][1]-gps_2[0][1])**2)


def get_dist_to_CoG(calib, train, px):
    #get distance of gid/pid of train to CoG of corresponding calibration
    gps = decoder.trains_to_gid_pid([train])
    #px = decoder.trains_to_pix([train])
    CoG = calib[px[0]][px[1]]
    dist = get_gps_dist([CoG], gps)
    return dist


def reevaluate_calib(calib_rising, calib_falling, trains, bad_trains, pix2mask):
    #print("    [DEBUG] Entering reevaluate_calib()")
    #takes 2nd nearest neighbour
    #mask nearest neighbour in calib (by setting it to infinity)
    calib_rising_cp = copy.deepcopy(calib_rising)
    calib_falling_cp = copy.deepcopy(calib_falling)
    calib_rising_msk=msk_px_in_calib(calib_rising_cp, pix2mask)
    calib_falling_msk=msk_px_in_calib(calib_falling_cp, pix2mask)
    #reevaluate the first half with calib_rising, the second_half with calib_falling
    newpixs_nested = decoder.trains_to_pix((calib_rising_msk, calib_falling_msk), trains, bad_trains)
    newpixs = [x for xs in newpixs_nested for x in xs]#flatten list for further processing
    #print("    [DEBUG] Leaving reevaluate_calib()")
    return newpixs


def msk_px_in_calib(calib,px):
    #masks one pixel in the calibration file
    calib[px[0]][px[1]] = np.inf
    return calib


def get_matched_unmatched_indxs_for_non_repetitive_lsts(decoded_pxs_rising, decoded_pxs_falling, intersection):
    already_matched_trains_idxs = []
    unmatched_train_idxs = []
    #loop over rising list and if px in intersec find corresponding falling one (only works for non-repetetive lists)
    for i_rising, px_rising in enumerate(decoded_pxs_rising):
        if px_rising in intersection: #if px_rising is in intersection, look for the matching px in px_falling
            for i_falling, px_falling in enumerate(decoded_pxs_falling):
                if px_rising == px_falling:#its a match! (warning: it takes the first match, does not matter in case without repetition)
                     already_matched_trains_idxs.append(i_rising)
                     already_matched_trains_idxs.append(len(decoded_pxs_rising) + i_falling)
    #check which indexes remain unmatched
    for i in range(0,len(decoded_pxs_rising + decoded_pxs_falling)):
        if i not in already_matched_trains_idxs:
            unmatched_train_idxs.append(i)
    return already_matched_trains_idxs, unmatched_train_idxs


def is_idx_in_rising_half(idx, decoded_pxs):
    if idx < len(decoded_pxs)/2: return True
    else: return False


def get_CoG_dists(trn_idxs, decoded_pxs, trains, calib_rising, calib_falling):
    #returns a list of CoG-distances corresponding to the train indexes specified(absolute indexes required)
    CoG_dists_unm = []
    for  i_unm in trn_idxs:
        if(is_idx_in_rising_half(i_unm, decoded_pxs)):
            CoG_dists_unm.append((i_unm,get_dist_to_CoG(calib_rising, trains[i_unm], decoded_pxs[i_unm])))
        else:
            CoG_dists_unm.append((i_unm, get_dist_to_CoG(calib_falling, trains[i_unm], decoded_pxs[i_unm])))
    return CoG_dists_unm


def get_idxs_of_trns_sorted_by_CoG_dist(CoG_dists_unm):
    #takes CoG_dists_unm and returns indexes of trains corresponding of CoG-distance sorted (highest distance comes last)
    idxs = []
    CoG_dists_unm.sort(key=lambda tup: tup[1])#sort list of unmatched trains such that highest distance comes last
    for tuple in CoG_dists_unm:
        idxs.append(tuple[0])
    return idxs


def get_decoded_px_reev(calib_rising, calib_falling, trains, bad_trains, decoded_pxs, idx_of_trns_to_reevaluate_abs):
    decoded_pxs_reev = copy.deepcopy(decoded_pxs)
    for i_reev in idx_of_trns_to_reevaluate_abs:
        recal = reevaluate_calib(calib_rising, calib_falling, trains, bad_trains, decoded_pxs[i_reev])
        decoded_pxs_reev[i_reev] = recal[i_reev]
    return decoded_pxs_reev


#-------------------------------------
# Decode source data
#-------------------------------------
def decode_source_data_to_pixels(data, calib_rising, calib_falling, nevents, min_gid_pid_in_calibs, debug=False, use_dumped_waveforms=False):
    #takes source data and calibration files and organizes the data as following:
    # np.array([
    # [event number, col, row, rising edge, falling edge],
    # [...],
    # [...]
    # ])
    # Note: If multiple pixels fire within one trigger event, they will be assigned to the same event number

    source_data = []

    #define errors occuring in match_trains
    error_odd_n_trains = "ERROR_ODD_N_TRAINS"
    error_0_trains =  "ERROR_0_TRAINS"
    error_possible_train_clash = "ERROR_POSS_TRAIN_CLASH"
    error_matching_event_wo_rep_failed = "ERROR_MATCH_EVENT_WO_REP_FAILED"
    error_matching_event_with_rep_failed = "ERROR_MATCH_EVENT_WITH_REP_FAILED"
    error_bad_train = "ERROR_BAD_TRAIN"
    error_out_of_time = "ERROR_OUT_OF_TIME"

    #counters for control plots
    n_match = 0
    n_odd_n_trains = 0
    n_0_n_trains = 0
    n_poss_train_clash = 0
    n_events_total = 0
    n_error_bad_train = 0
    n_fully_matched_events = 0
    n_events_with_1_train = 0
    n_error_matching_event_wo_rep_failed = 0
    n_error_matching_event_with_rep_failed = 0
    n_wo_rep_matched = 0
    n_with_rep_matched = 0
    n_directly_matched = 0
    n_rep_jst_on_rising = 0
    n_rep_jst_on_falling = 0
    n_rep_on_both_sides = 0
    n_error_out_of_time = 0

    #lists for control plots
    n_trains_per_event = []
    n_trains_odd_n_trains = []
    n_trains_0_trains = []
    n_trains_matched = []
    n_trains_fully_matched = []
    n_trains_poss_train_clash = []
    gid_pids_fully_matched = []
    train_combinations_lst =  []
    n_trains_error_bad_train = []
    n_trains_error_matching_event_wo_rep_failed = []
    n_trains_error_matching_event_with_rep_failed = []
    n_trains_error_all_dec_pix_0 = []
    gid_pids_all_dec_px_zero = []
    n_trains_directly_matched = []
    n_trains_matched_after_reev_w_rep = []
    n_trains_matched_after_reev_wo_rep = []
    gid_pids_error_matching_w_rep_failed = []
    gid_pids_error_matching_wo_rep_failed = []
    n_trains_error_out_of_time = []

    #-------------------------------------------------------------------------
    # Loop over events
    #-------------------------------------------------------------------------
    for eventnr in tqdm(range(int(nevents)), desc="[STATUS] Creating source data container"):
        if debug: print("*************************")

        #-------------------------------------------------------------------------
        # Get Trains from source measurement
        #-------------------------------------------------------------------------
        if not (use_dumped_waveforms):
            trains, bad_trains = decoder.zs_to_trains(data[eventnr]) # here, data is interpreted as data_zs

        #-------------------------------------------------------------------------
        # Get Trains from TB data
        #-------------------------------------------------------------------------
        else: trains, bad_trains = data[eventnr]# here, data is interpreted as list of trains, bad trains for ech event e.g. [[trains, bad_trains], [trains, bad_trains], ... ]

        #for control plots:
        n_events_total +=1
        n_trains_per_event.append(len(trains))
        if(len(trains) == 1): n_events_with_1_train+=1

        #-------------------------------------------------------------------------
        # Match Trains
        #-------------------------------------------------------------------------
        matched = match_trains(trains, bad_trains, calib_rising, calib_falling, min_gid_pid_in_calibs, use_dumped_waveforms, debug)
        if debug: print("-------------------------")
        
        #-------------------------------------------------------------------------
        # Handle events with two events in the same waveform
        #-------------------------------------------------------------------------
        if matched == error_out_of_time:
            n_error_out_of_time +=1
            n_trains_error_out_of_time.append(len(trains))
        #-------------------------------------------------------------------------
        # Handle events with odd number of trains for control plots
        #-------------------------------------------------------------------------
        elif matched == error_odd_n_trains:
            n_odd_n_trains +=1
            n_trains_odd_n_trains.append(len(trains))
        #-------------------------------------------------------------------------
        # Handle events with no trains for control plots
        #-------------------------------------------------------------------------
        elif matched == error_0_trains:
            n_0_n_trains +=1
            n_trains_0_trains.append(len(trains))            
        #-------------------------------------------------------------------------
        # Handle events with possible train clash for control plots
        #-------------------------------------------------------------------------
        elif matched == error_possible_train_clash:
            n_poss_train_clash +=1
            n_trains_poss_train_clash.append(len(trains))
        #-------------------------------------------------------------------------
        # Handle events with bad trains for control plots
        #-------------------------------------------------------------------------
        elif matched == error_bad_train:
            n_error_bad_train+=1
            n_trains_error_bad_train.append(len(trains))
        #-------------------------------------------------------------------------
        # Handle events without repetition where matching failed
        #-------------------------------------------------------------------------
        elif matched == error_matching_event_wo_rep_failed:
            n_error_matching_event_wo_rep_failed+=1
            n_trains_error_matching_event_wo_rep_failed.append(len(trains))
            gid_pids_error_matching_wo_rep_failed.append((len(trains),decoder.trains_to_gid_pid(trains)))
        #-------------------------------------------------------------------------
        # Handle events with repetition where matching failed
        #-------------------------------------------------------------------------
        elif matched == error_matching_event_with_rep_failed:
            n_error_matching_event_with_rep_failed+=1
            n_trains_error_matching_event_with_rep_failed.append(len(trains))
            gid_pids_error_matching_w_rep_failed.append((len(trains),decoder.trains_to_gid_pid(trains)))
            # #in order to print out t0s and trains for debugging:
            # print("--")
            # print("pix", decoder.trains_to_pix((calib_rising, calib_falling),trains,bad_trains))
            # print("trains:",[[round(e*1e9,1) for e in t] for t in trains])
            # print("t0s:", [round(t[0]*1e9,1) for t in t0s])
        #-------------------------------------------------------------------------
        # Handle matched events
        #-------------------------------------------------------------------------
        else:
            col_lst, row_lst, rising_edge_lst, falling_edge_lst, fully_matched, case_wo_rep_matched, case_with_rep_matched, case_directly_matched, case_with_rep_jst_on_rising, case_with_rep_jst_on_falling, case_with_rep_on_both_sides, cut_min_gid, cut_min_pid, train_combinations = matched
            
            #counters
            n_match += 1
            n_trains_matched.append(len(trains))
            train_combinations_lst.append(train_combinations)

            #keep track of train matching performance
            if(fully_matched == True):
                n_fully_matched_events +=1
                n_trains_fully_matched.append(len(trains))
                gid_pids_fully_matched.append((len(trains),decoder.trains_to_gid_pid(trains)))
            else:
                print("[ERROR] Event not fully matched but it is considered as such. That should not happen!")
                exit()

            if(case_wo_rep_matched == True):
                n_wo_rep_matched+=1
                n_trains_matched_after_reev_wo_rep.append(len(trains))
            elif(case_with_rep_matched == True):
                n_with_rep_matched+=1
                n_trains_matched_after_reev_w_rep.append(len(trains))
            elif(case_directly_matched == True):
                n_directly_matched+=1
                n_trains_directly_matched.append(len(trains))
            else:
                print("[ERROR] Event considered as fully matched but not considered as direct match, match w rep or match wo rep. This should not happen!")
                exit()

            if(case_with_rep_jst_on_rising == True): n_rep_jst_on_rising+=1
            elif(case_with_rep_jst_on_falling == True):n_rep_jst_on_falling+=1
            elif(case_with_rep_on_both_sides == True): n_rep_on_both_sides+=1
            
            #-------------------------------------------------------------------------
            # Append all matched hits in a event to output source_data
            #-------------------------------------------------------------------------
            for px in range(0,len(col_lst)):
                if debug:
                    print("[DEBUG] eventnr: ", eventnr)
                    print("[DEBUG] px: ", px)
                    print("[DEBUG] col_lst: ", col_lst)
                    print("[DEBUG] row_lst: ", row_lst)
                    print("[DEBUG] rising_edge_lst: ", rising_edge_lst)
                    print("[DEBUG] falling_edge_lst: ", falling_edge_lst)

                event = [eventnr, col_lst[px], row_lst[px], rising_edge_lst[px], falling_edge_lst[px]]
                source_data.append(event)
                if debug: print("[DEBUG] event: ", event)

    source_data = np.array(source_data) #convert list of lists in numpy array

    #create dictionary to return
    dsd = dict([\
        ("source_data",source_data),\
        ("n_trains_per_event",n_trains_per_event),\
        ("n_match",n_match),\
        ("n_trains_odd_n_trains",n_trains_odd_n_trains),\
        ("n_trains_matched",n_trains_matched),\
        ("gid_pids_fully_matched",gid_pids_fully_matched),\
        ("cut_min_gid",cut_min_gid),\
        ("cut_min_pid",cut_min_pid),\
        ("n_poss_train_clash",n_poss_train_clash),\
        ("n_trains_poss_train_clash",n_trains_poss_train_clash),\
        ("n_error_bad_train",n_error_bad_train),\
        ("n_events_total",n_events_total),\
        ("n_fully_matched_events",n_fully_matched_events),\
        ("n_trains_fully_matched",n_trains_fully_matched),\
        ("train_combinations_lst",train_combinations_lst),\
        ("n_events_with_1_train",n_events_with_1_train),\
        ("n_error_matching_event_wo_rep_failed",n_error_matching_event_wo_rep_failed),\
        ("n_error_matching_event_with_rep_failed",n_error_matching_event_with_rep_failed),\
        ("n_wo_rep_matched",n_wo_rep_matched),\
        ("n_with_rep_matched",n_with_rep_matched),\
        ("n_directly_matched",n_directly_matched),\
        ("n_rep_jst_on_rising",n_rep_jst_on_rising),\
        ("n_rep_jst_on_falling",n_rep_jst_on_falling),\
        ("n_rep_on_both_sides",n_rep_on_both_sides),\
        ("n_trains_error_bad_train",n_trains_error_bad_train),\
        ("n_trains_error_matching_event_wo_rep_failed",n_trains_error_matching_event_wo_rep_failed),\
        ("n_trains_error_matching_event_with_rep_failed",n_trains_error_matching_event_with_rep_failed),\
        ("n_trains_error_all_dec_pix_0",n_trains_error_all_dec_pix_0),\
        ("gid_pids_all_dec_px_zero",gid_pids_all_dec_px_zero),\
        ("n_trains_matched_after_reev_w_rep",n_trains_matched_after_reev_w_rep),\
        ("n_trains_matched_after_reev_wo_rep",n_trains_matched_after_reev_wo_rep),\
        ("n_trains_directly_matched",n_trains_directly_matched),\
        ("gid_pids_error_matching_w_rep_failed",gid_pids_error_matching_w_rep_failed),\
        ("gid_pids_error_matching_wo_rep_failed",gid_pids_error_matching_wo_rep_failed),\
        ("n_error_out_of_time",n_error_out_of_time),\
        ("n_trains_error_out_of_time",n_trains_error_out_of_time),\
        ("n_odd_n_trains", n_odd_n_trains),\
        ("n_0_n_trains", n_0_n_trains),\
        ("n_trains_0_trains", n_trains_0_trains)\
    ])

    return dsd


def get_train_list(dumped_waveforms, outdir):
    # returns list with trains and bad trains for each waveform
    # e.g. [[trains, bad_trains], [trains, bad_trains], ... ]
    train_list = []
    waveforms_in_searchwindow = []
    all_gps = []
    for wf in tqdm(dumped_waveforms, desc="[STATUS] Extracting trains from dumped waveforms"):
        trains, bad_trains = landau_creator.get_trains_from_waveformfile(wf)
        train_list.append([trains, bad_trains])

    #     #for monitoring waveforms:
    #     gps = decoder.trains_to_gid_pid(trains)
    #     all_gps.append(gps)
    #     for gp in gps:
    #         if (gp[0] > 0.8*1e-8) and (gp[0] < 1.2*1e-8) and (gp[1] > 0.8*1e-8) and (gp[1] < 1.2*1e-8):
    #             waveforms_in_searchwindow.append(wf)
    # np.savetxt(outdir + "waveforms_in_searchwindow.txt", waveforms_in_searchwindow, fmt="%s")

    return train_list, all_gps


def get_gids_and_pids(train_gid_pid_lst, ntrains= None):
    #maketwo lists out of GID/PID list in order to make a 2D scatterplot
    gids = []
    pids = []
    for train_gid_pid in train_gid_pid_lst:
        for i in range(0, len(train_gid_pid[1])):

            if not (ntrains == None):
                if train_gid_pid[0] == ntrains:
                    gids.append(train_gid_pid[1][i][0])
                    pids.append(train_gid_pid[1][i][1])
            elif (ntrains == None):
                gids.append(train_gid_pid[1][i][0])
                pids.append(train_gid_pid[1][i][1])
            else:
                print("[ERROR] ntrains not correctly specified in: get_gids_and_pids(gid_pid_lst, ntrains= None)")
    return gids, pids


def get_all_gids_pids(all_gps):
    gids_all = []
    pids_all = []
    for element in all_gps:
        for gps in element:
            gids_all.append(gps[0])
            pids_all.append(gps[1])
    return gids_all, pids_all


def get_min_max_gid_pid_from_calib(calib_rising, calib_falling):
    #gets minimum GID/ PID of the calibrations in order to use it for identifying possible train clashes
    #Note: it returns the min pair of both calibrations!
    calibs = [calib_rising, calib_falling]
    gids = np.array([])
    pids = np.array([])
    for calib in calibs:
        for c in range(0, 32):
            for r in range(0,32):
                gids = np.append(gids, calib[c][r][0])
                pids = np.append(pids, calib[c][r][1])

    return gids.min(), pids.min(), gids.max(), pids.max()


def divide_lsts(lst1, lst2):
    #devides list avoiding division by zero
    divided = np.array([])
    if len(lst1) == len(lst2):
        for i in range(0, len(lst1)):
            if not (lst1[i] == 0):
                divided = np.append(divided, lst1[i] / lst2[i])
            else:
                divided = np.append(divided, 0)
    else:
        print("[ERROR] List shape does not match!")
        exit
    return divided


def get_train_combinations(train_combinations_lst):
    #two cases for 2 pixel-cluster
    n_R1R2F1F2 = 0
    n_R1R2F2F1 = 0
    #all permutations (1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), and (3, 2, 1)
    n_R1R2R3F1F2F3 = 0
    n_R1R2R3F1F3F2 = 0
    n_R1R2R3F2F1F3 = 0
    n_R1R2R3F2F3F1 = 0
    n_R1R2R3F3F1F2 = 0
    n_R1R2R3F3F2F1 = 0
    for tc in train_combinations_lst:
        if(len(tc) > 1): #exclude trivial tweo train combinatorics
            if len(tc) == 2:
                if tc[0][1] == 0 and tc[1][1] == 1: #idx 0 rising is matched with idx 0 falling (and 1 rising with 1 falling)
                    n_R1R2F1F2 += 1
                elif tc[0][1] == 1 and tc[1][1] == 0: # idx 0 rising is matched with idx 1 falling (and 1 rising with 0 falling)
                    n_R1R2F2F1 +=1
                else:
                    print("[WARNING] Train was not combinated for control plot. Should be investigated!")
                    print("        | tc: ", tc)
            if len(tc) == 3:
                if tc[0][1] == 0 and tc[1][1] == 1 and tc[2][1] == 2:
                    n_R1R2R3F1F2F3 += 1
                if tc[0][1] == 0 and tc[1][1] == 2 and tc[2][1] == 1:
                    n_R1R2R3F1F3F2 += 1
                if tc[0][1] == 1 and tc[1][1] == 0 and tc[2][1] == 2:
                    n_R1R2R3F2F1F3 += 1
                if tc[0][1] == 1 and tc[1][1] == 2 and tc[2][1] == 0:
                    n_R1R2R3F2F3F1 += 1
                if tc[0][1] == 2 and tc[1][1] == 0 and tc[2][1] == 1:
                    n_R1R2R3F3F1F2 += 1
                if tc[0][1] == 2 and tc[1][1] == 1 and tc[2][1] == 0:
                    n_R1R2R3F3F2F1 += 1

    return n_R1R2F1F2, n_R1R2F2F1, n_R1R2R3F1F2F3, n_R1R2R3F1F3F2, n_R1R2R3F2F1F3, n_R1R2R3F2F3F1, n_R1R2R3F3F1F2, n_R1R2R3F3F2F1


#=====================================
#
#MAIN
#
#=====================================

if __name__=="__main__":
    parser = argparse.ArgumentParser("Script to decode source measuement data to pixel hits.",formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("file", help = ".npy file created by fhr.py or source_measurement.py (or dir with dumped waveforms created by DPTSDump.py if corresponding flag is set)")
    parser.add_argument("calib_rising_edge", help = ".calib file for rising edge created by decoding_calibration.py")
    parser.add_argument("calib_falling_edge", help = ".calib file for the falling edge created by decoding_calibration.py")
    parser.add_argument("--outdir", "-od", help = "Target file to write plot to", default = "./plots")
    parser.add_argument("--use_dumped_waveforms", "-udw", action = 'store_true', help = "Use dumped waveforms (created by DPTSDump.py) as input (necessary for Testbeam data)")
    parser.add_argument("--nevents", "-n", help = "Number of triggers to analyze ", default = -1)
    parser.add_argument("--plots", "-p", action = 'store_true', help = "Plot additional plots")
    parser.add_argument("--debug", "-d", action = 'store_true', help = "Print debug messages")
    args = parser.parse_args()

    print("[INFO] Starting source_decoder.py!")

    # Create outdir if not existing
    if not os.path.exists(args.outdir): os.makedirs(args.outdir)
    
    #Load json file to obtain information on eventsize
    if not (args.use_dumped_waveforms):
        with open(args.file.replace('.npy','.json')) as jf:
            jsonfile = json.load(jf)

        if args.nevents == -1: nevents = jsonfile['ntrg']
        else: nevents = args.nevents
    else:
        nevents = -1

    #Load decoding calibrations
    calib_rising = np.load(args.calib_rising_edge)
    calib_falling = np.load(args.calib_falling_edge)

    #get minimum GID/PID in calibrations to identify possible train clashes
    min_max_gid_pid_in_calibs = get_min_max_gid_pid_from_calib(calib_rising, calib_falling)
    
    #Create source data container 
    if not (args.use_dumped_waveforms):
        path = os.path.join(args.outdir, pathlib.Path(args.file).stem + "_decoded" + ".npy")
        data_zs = np.load(args.file)

        #call decoding function
        dsd = decode_source_data_to_pixels(data_zs, calib_rising, calib_falling, nevents, min_max_gid_pid_in_calibs, args.debug, args.use_dumped_waveforms)

    elif (args.use_dumped_waveforms):
        path = os.path.join(args.outdir+"/decoded_landau_data.npy")
        dumped_waveforms = landau_creator.get_filename_lst(args.file)
        n_files = len(dumped_waveforms)
        print("[INFO] Found ", n_files, "dumped waveform files in ", args.file)
        train_list, all_gps = get_train_list(dumped_waveforms, args.outdir) #get list of trains from dumped_waveforms

        #call decoding function
        dsd= decode_source_data_to_pixels(train_list, calib_rising, calib_falling, n_files, min_max_gid_pid_in_calibs, args.debug, args.use_dumped_waveforms)

    else:
        print('[ERROR] Input file could not be interpreted!')
        exit()

    if args.debug: print("[DEBUG] source_data[:10]: ", dsd['source_data'][:10])
    print("[INFO] Saving source data...")
    np.save(path, dsd['source_data'])
    with open(path.replace('.npy','.json'), 'w') as jf:
            json.dump(jsonfile, jf, indent=4)

    #reporting info about occurance of matched/unmatched trains
    print("[INFO] Rep just on rising: ", dsd['n_rep_jst_on_rising'])
    print("[INFO] Rep just on falling: ", dsd['n_rep_jst_on_falling'])
    print("[INFO] Rep just on both sides: ", dsd['n_rep_on_both_sides'])
    print("[INFO]", dsd['n_events_with_1_train'], " one-train events counted. These are", round(dsd['n_events_with_1_train']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    
    n_err_tot = dsd['n_odd_n_trains'] + dsd['n_poss_train_clash'] + dsd['n_error_matching_event_with_rep_failed'] + dsd['n_error_matching_event_wo_rep_failed']  + dsd['n_error_bad_train'] + dsd['n_error_out_of_time']
    
    print("="*150)
    print("[INFO] Total number of events processed: ", dsd['n_events_total'])
    print("-"*150)
    print("[INFO]",dsd['n_fully_matched_events'], " events were fully matched in total. These are ", round(dsd['n_fully_matched_events']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |",dsd['n_directly_matched'], " events were directly fully matched. These are ", round(dsd['n_directly_matched']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |",dsd['n_wo_rep_matched'], " events without repetition were fully matched after reevaluation. These are ", round(dsd['n_wo_rep_matched']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |",dsd['n_with_rep_matched'], " events with repetition were fully matched after reevaluation. These are ", round(dsd['n_with_rep_matched']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("-"*150)
    print("[INFO] In total ",n_err_tot, " events could not be matched out of", dsd['n_events_total'], "events. These are ", round(n_err_tot/(dsd['n_events_total'])*100, 2), "%" )
    print("     |", dsd['n_0_n_trains'], " events could not be matched due to no trains in event. These are ", round(dsd['n_0_n_trains']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |", dsd['n_odd_n_trains'], " events could not be matched due to odd number of trains. These are ", round(dsd['n_odd_n_trains']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |", dsd['n_error_out_of_time'], " events were discarded due to two events in the same waveform. These are ", round(dsd['n_error_out_of_time']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |", dsd['n_poss_train_clash'], " events were identified as possible train clashes and were therefore not matched. These are ", round(dsd['n_poss_train_clash']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |", dsd['n_error_bad_train'], " events contain at least one bad train and were therefore not matched. These are ", round(dsd['n_error_bad_train']/(dsd['n_events_total'])*100, 2), "%","of all events.")
    print("     |", dsd['n_error_matching_event_with_rep_failed'], " events with repetitive pattern could not be matched even after reevaluation. These are ", round(dsd['n_error_matching_event_with_rep_failed']/(dsd['n_events_total'])*100, 2), "%","of all events." )
    print("     |", dsd['n_error_matching_event_wo_rep_failed'], " events without repetitive pattern could not be matched even after reevaluation. These are ", round(dsd['n_error_matching_event_wo_rep_failed']/(dsd['n_events_total'])*100, 2), "%","of all events." )
    print("="*150)
    
#=====================================
#
#CONTROL PLOTS
#
#=====================================

    if (args.plots):
        print('[INFO] Plotting control plots ...')

        #---------------------------------
        # Histogram of train combinations
        #---------------------------------
        print('     | Plotting histograms of train combinations')
        n_R1R2F1F2, n_R1R2F2F1, n_R1R2R3F1F2F3, n_R1R2R3F1F3F2, n_R1R2R3F2F1F3, n_R1R2R3F2F3F1, n_R1R2R3F3F1F2, n_R1R2R3F3F2F1 = get_train_combinations(dsd['train_combinations_lst'])
        n_comb_tot_4_train = n_R1R2F1F2 + n_R1R2F2F1
        n_comb_tot_6_train = n_R1R2R3F1F2F3 + n_R1R2R3F1F3F2 + n_R1R2R3F2F1F3 + n_R1R2R3F2F3F1 + n_R1R2R3F3F1F2 + n_R1R2R3F3F2F1
        plt.figure()
        x=["R1R2F1F2","R1R2F2F1"]
        plt.ylim([0,1])
        comb_4= [n_R1R2F1F2 / n_comb_tot_4_train,n_R1R2F2F1 / n_comb_tot_4_train]
        plt.bar(x, comb_4, width=1, color="red")
        plt.grid()
        plt.xlabel("Train match pattern of train combination for four train events (fully matched)")
        plt.ylabel("Relative abundance")
        plt.xticks(rotation = 75)
        for i, n in enumerate(comb_4):
            plt.text(i-0.25, n+0.03, "Abs: "+ str(int(n*n_comb_tot_4_train)))
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_train_comb_4_trains"), bbox_inches = 'tight', dpi = 600)
        plt.close()

        plt.figure()
        x=["R1R2R3F1F2F3", "R1R2R3F1F3F2", "R1R2R3F2F1F3", "R1R2R3F2F3F1", "R1R2R3F3F1F2", "R1R2R3F3F2F1"]
        plt.ylim([0,1])
        comb_6_abs = [n_R1R2R3F1F2F3, n_R1R2R3F1F3F2, n_R1R2R3F2F1F3, n_R1R2R3F2F3F1, n_R1R2R3F3F1F2, n_R1R2R3F3F2F1]
        comb_6 = [s/n_comb_tot_6_train for s in comb_6_abs]
        plt.bar(x, comb_6, width=1, color="red")
        plt.grid()
        plt.xlabel("Train match pattern of train combination for six train events (fully matched)")
        plt.ylabel("Relative abundance")
        plt.xticks(rotation = 75)
        for i, n in enumerate(comb_6):
            plt.text(i-0.25, n+0.03, "Abs: "+ str(int(n*n_comb_tot_6_train)))
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_train_comb_6_trains"), bbox_inches = 'tight', dpi = 600)
        plt.close()


        #-----------------------------------------------
        #Histogram of length of the trains (ABSOLUTE)
        #-----------------------------------------------
        print('     | Plotting histogram of n_trains (ABSOLUTE)')
        plt.figure()

        n_trains_max = max(dsd['n_trains_per_event'])
        nbins = n_trains_max + 1
        rmin = -0.5
        rmax = n_trains_max + 0.5

        hist_trains_per_event, bin_edges_trains_per_event = np.histogram(dsd['n_trains_per_event'], bins = nbins, range = (rmin, rmax))
        bincenters = np.array([0.5 * (bin_edges_trains_per_event[i] + bin_edges_trains_per_event[i+1]) for i in range(len(bin_edges_trains_per_event)-1)]) # will be usable for all

        hist_trains_0_trains, bin_edges_trains_0_trains = np.histogram(dsd['n_trains_0_trains'], bins = nbins, range = (rmin, rmax))
        hist_trains_directly_fully_matched, bin_edges_trains_directly_fully_matched = np.histogram(dsd['n_trains_directly_matched'], bins = nbins, range = (rmin, rmax))
        hist_fully_matched_w_rep, bin_edges_fully_matched_w_rep = np.histogram(dsd['n_trains_matched_after_reev_w_rep'], bins = nbins, range = (rmin, rmax))
        hist_fully_matched_wo_rep, bin_edges_fully_matched_wo_rep = np.histogram(dsd['n_trains_matched_after_reev_wo_rep'], bins = nbins, range = (rmin, rmax))
        hist_trains_odd_n_trains, bin_edges_trains_odd_n_trains = np.histogram(dsd['n_trains_odd_n_trains'], bins = nbins, range = (rmin, rmax))
        hist_trains_poss_train_clash, bin_edges_trains_poss_train_clash = np.histogram(dsd['n_trains_poss_train_clash'], bins = nbins, range = (rmin, rmax))
        hist_bad_train, bin_edges_bad_train = np.histogram(dsd['n_trains_error_bad_train'], bins = nbins, range = (rmin, rmax))
        hist_match_w_rep_failed, bin_edges_match_w_rep_failed = np.histogram(dsd['n_trains_error_matching_event_with_rep_failed'], bins = nbins, range = (rmin, rmax))
        hist_match_wo_rep_failed, bin_edges_match_wo_rep_failed = np.histogram(dsd['n_trains_error_matching_event_wo_rep_failed'], bins = nbins, range = (rmin, rmax))
        hist_out_of_time, bin_edges_out_of_time = np.histogram(dsd['n_trains_error_out_of_time'], bins = nbins, range = (rmin, rmax))
        
        plt.bar(bincenters, hist_trains_0_trains, width=bincenters[1] - bincenters[0], color='dimgray', label=r'No trains detected ('+str(round(dsd['n_0_n_trains']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_trains_directly_fully_matched, width=bincenters[1] - bincenters[0], color='g', label=r'Directly fully matched ('+str(round(dsd['n_directly_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_fully_matched_w_rep, bottom=hist_trains_directly_fully_matched, width=bincenters[1] - bincenters[0], color='limegreen', label=r'Matched after reevaluation, initially with repetition ('+str(round(dsd['n_with_rep_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_fully_matched_wo_rep, bottom=hist_trains_directly_fully_matched+hist_fully_matched_w_rep, width=bincenters[1] - bincenters[0], color='lime', label=r'Matched after reevaluation, initially without repetition ('+str(round(dsd['n_wo_rep_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_match_wo_rep_failed, bottom = hist_trains_directly_fully_matched+hist_fully_matched_w_rep+hist_fully_matched_wo_rep,width=bincenters[1] - bincenters[0], color='yellow', label=r'No Matches, reevaluation failed ('+str(round(dsd['n_error_matching_event_wo_rep_failed']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_match_w_rep_failed, bottom = hist_trains_directly_fully_matched+hist_match_wo_rep_failed+hist_fully_matched_w_rep+hist_fully_matched_wo_rep,width=bincenters[1] - bincenters[0], color='orange', label=r'Repetition, reevaluation failed ('+str(round(dsd['n_error_matching_event_with_rep_failed']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_trains_odd_n_trains, bottom=hist_trains_directly_fully_matched+hist_match_wo_rep_failed+hist_match_w_rep_failed+hist_fully_matched_w_rep+hist_fully_matched_wo_rep, width=bincenters[1] - bincenters[0], color='darkgrey', label=r'Odd number of trains ('+str(round(dsd['n_odd_n_trains']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_trains_poss_train_clash, bottom=hist_trains_directly_fully_matched+hist_match_wo_rep_failed+hist_match_w_rep_failed+hist_trains_odd_n_trains+hist_fully_matched_w_rep+hist_fully_matched_wo_rep, width=bincenters[1] - bincenters[0], color='b', label=r'Possible train clash ('+str(round(dsd['n_poss_train_clash']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_bad_train, bottom=hist_trains_directly_fully_matched+hist_match_wo_rep_failed+hist_match_w_rep_failed+hist_trains_odd_n_trains+hist_trains_poss_train_clash+hist_fully_matched_w_rep+hist_fully_matched_wo_rep, width=bincenters[1] - bincenters[0], color='red', label=r'Bad Trains ('+str(round(dsd['n_error_bad_train']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters, hist_out_of_time, bottom=hist_trains_directly_fully_matched+hist_match_wo_rep_failed+hist_match_w_rep_failed+hist_trains_odd_n_trains+hist_trains_poss_train_clash+hist_bad_train+hist_fully_matched_w_rep+hist_fully_matched_wo_rep, width=bincenters[1] - bincenters[0], color='darkred', label=r'Pile-up ('+str(round(dsd['n_error_out_of_time']/(dsd['n_events_total'])*100, 2))+'%)')
        
        plt.xlabel("Number of trains per event")
        plt.ylabel("Absolute occurance")
        plt.xlim([rmin, rmax])
        plt.xticks(np.arange(0, n_trains_max+1))
        plt.legend(loc = (1.01, 0))
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_train_length"), bbox_inches = 'tight', dpi = 600)
        plt.yscale("log")
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_train_length_log"), bbox_inches = 'tight', dpi = 600)
        plt.close()


        #-----------------------------------------------
        #Histogram of length of the trains (RELATIVE)
        #-----------------------------------------------
        print('     | Plotting histogram of n_trains (RELATIVE)')
        plt.figure()
        hist_trains_per_event, bin_edges_trains_per_event = np.histogram(dsd['n_trains_per_event'], bins = nbins, range = (rmin, rmax))
        bincenters = np.array([0.5 * (bin_edges_trains_per_event[i] + bin_edges_trains_per_event[i+1]) for i in range(len(bin_edges_trains_per_event)-1)]) # will be usable for all
        msk_sufficient_stat = (hist_trains_per_event >= 10) #just plot if sufficient trains are in the statistic

        hist_trains_0_trains, bin_edges_0_trains = np.histogram(dsd['n_trains_0_trains'], bins = nbins, range = (rmin, rmax))
        hist_trains_directly_fully_matched, bin_edges_trains_directly_fully_matched = np.histogram(dsd['n_trains_directly_matched'], bins = nbins, range = (rmin, rmax))
        hist_fully_matched_w_rep, bin_edges_fully_matched_w_rep = np.histogram(dsd['n_trains_matched_after_reev_w_rep'], bins = nbins, range = (rmin, rmax))
        hist_fully_matched_wo_rep, bin_edges_fully_matched_wo_rep = np.histogram(dsd['n_trains_matched_after_reev_wo_rep'], bins = nbins, range = (rmin, rmax))
        hist_trains_odd_n_trains, bin_edges_trains_odd_n_trains = np.histogram(dsd['n_trains_odd_n_trains'], bins = nbins, range = (rmin, rmax))
        hist_trains_poss_train_clash, bin_edges_trains_poss_train_clash = np.histogram(dsd['n_trains_poss_train_clash'], bins = nbins, range = (rmin, rmax))
        hist_bad_train, bin_edges_bad_train = np.histogram(dsd['n_trains_error_bad_train'], bins = nbins, range = (rmin, rmax))
        hist_match_w_rep_failed, bin_edges_match_w_rep_failed = np.histogram(dsd['n_trains_error_matching_event_with_rep_failed'], bins = nbins, range = (rmin, rmax))
        hist_match_wo_rep_failed, bin_edges_match_wo_rep_failed = np.histogram(dsd['n_trains_error_matching_event_wo_rep_failed'], bins = nbins, range = (rmin, rmax))
        hist_out_of_time, bin_edges_out_of_time = np.histogram(dsd['n_trains_error_out_of_time'], bins = nbins, range = (rmin, rmax))
        
        hist_trains_0_trains_rel = divide_lsts(hist_trains_0_trains, hist_trains_per_event)[msk_sufficient_stat]
        hist_trains_directly_fully_matched_rel = divide_lsts(hist_trains_directly_fully_matched, hist_trains_per_event)[msk_sufficient_stat]
        hist_fully_matched_w_rep_rel = divide_lsts(hist_fully_matched_w_rep, hist_trains_per_event)[msk_sufficient_stat]
        hist_fully_matched_wo_rep_rel = divide_lsts(hist_fully_matched_wo_rep, hist_trains_per_event)[msk_sufficient_stat]
        hist_trains_odd_n_trains_rel = divide_lsts(hist_trains_odd_n_trains, hist_trains_per_event)[msk_sufficient_stat]
        hist_trains_poss_train_clash_rel = divide_lsts(hist_trains_poss_train_clash, hist_trains_per_event)[msk_sufficient_stat]
        hist_bad_train_rel = divide_lsts(hist_bad_train, hist_trains_per_event)[msk_sufficient_stat]
        hist_match_w_rep_failed_rel = divide_lsts(hist_match_w_rep_failed, hist_trains_per_event)[msk_sufficient_stat]
        hist_match_wo_rep_failed_rel = divide_lsts(hist_match_wo_rep_failed, hist_trains_per_event)[msk_sufficient_stat]
        hist_out_of_time_rel = divide_lsts(hist_out_of_time, hist_trains_per_event)[msk_sufficient_stat]

        plt.bar(bincenters[msk_sufficient_stat], hist_trains_0_trains_rel, width=bincenters[1] - bincenters[0], color='dimgray', label=r'No trains detected ('+str(round(dsd['n_0_n_trains']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_trains_directly_fully_matched_rel, width=bincenters[1] - bincenters[0], color='g', label=r'Directly fully matched ('+str(round(dsd['n_directly_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_fully_matched_w_rep_rel, bottom=hist_trains_directly_fully_matched_rel, width=bincenters[1] - bincenters[0], color='limegreen', label=r'Matched after reevaluation, initially with repetition ('+str(round(dsd['n_with_rep_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_fully_matched_wo_rep_rel, bottom=hist_trains_directly_fully_matched_rel+hist_fully_matched_w_rep_rel, width=bincenters[1] - bincenters[0], color='lime', label=r'Matched after reevaluation, initially without repetition ('+str(round(dsd['n_wo_rep_matched']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_match_wo_rep_failed_rel, bottom = hist_trains_directly_fully_matched_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel,width=bincenters[1] - bincenters[0], color='yellow', label=r'No Matches, reevaluation failed ('+str(round(dsd['n_error_matching_event_wo_rep_failed']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_match_w_rep_failed_rel, bottom = hist_trains_directly_fully_matched_rel+hist_match_wo_rep_failed_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel,width=bincenters[1] - bincenters[0], color='orange', label=r'Repetition, reevaluation failed ('+str(round(dsd['n_error_matching_event_with_rep_failed']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_trains_odd_n_trains_rel, bottom=hist_trains_directly_fully_matched_rel+hist_match_wo_rep_failed_rel+hist_match_w_rep_failed_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel, width=bincenters[1] - bincenters[0], color='darkgrey', label=r'Odd number of trains ('+str(round(dsd['n_odd_n_trains']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_trains_poss_train_clash_rel, bottom=hist_trains_directly_fully_matched_rel+hist_match_wo_rep_failed_rel+hist_match_w_rep_failed_rel+hist_trains_odd_n_trains_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel, width=bincenters[1] - bincenters[0], color='b', label=r'Possible train clash ('+str(round(dsd['n_poss_train_clash']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_bad_train_rel, bottom=hist_trains_directly_fully_matched_rel+hist_match_wo_rep_failed_rel+hist_match_w_rep_failed_rel+hist_trains_odd_n_trains_rel+hist_trains_poss_train_clash_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel, width=bincenters[1] - bincenters[0], color='red', label=r'Bad Trains ('+str(round(dsd['n_error_bad_train']/(dsd['n_events_total'])*100, 2))+'%)')
        plt.bar(bincenters[msk_sufficient_stat], hist_out_of_time_rel, bottom=hist_trains_directly_fully_matched_rel+hist_match_wo_rep_failed_rel+hist_match_w_rep_failed_rel+hist_trains_odd_n_trains_rel+hist_trains_poss_train_clash_rel+hist_bad_train_rel+hist_fully_matched_w_rep_rel+hist_fully_matched_wo_rep_rel, width=bincenters[1] - bincenters[0], color='darkred', label=r'Pile-up ('+str(round(dsd['n_error_out_of_time']/(dsd['n_events_total'])*100, 2))+'%)')
        
        plt.xlabel("Number of trains per event")
        plt.ylabel("Relative occurance")
        plt.xlim([rmin, rmax])
        plt.xticks(np.arange(0, n_trains_max+1))
        plt.legend(loc = (1.01, 0))
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_train_length_relative"), bbox_inches = 'tight', dpi = 600)
        plt.close()


        #-----------------------------------------------
        #Scatterplot of matched/unmatched GIDS/PIDS
        #-----------------------------------------------
        print('     | Scatterplot of GIDS/PID space')
        plt.figure()
        gids_fully_matched, pids_fully_matched = get_gids_and_pids(dsd['gid_pids_fully_matched'])
        gids_matching_w_rep_failed, pids_matching_w_rep_failed = get_gids_and_pids(dsd['gid_pids_error_matching_w_rep_failed'])
        gids_matching_wo_rep_failed, pids_matching_wo_rep_failed = get_gids_and_pids(dsd['gid_pids_error_matching_wo_rep_failed'])
        plt.scatter([x*1e9 for x in gids_fully_matched], [x*1e9 for x in pids_fully_matched], label="Fully matched events", s=1, alpha = 0.5, color="blue")
        plt.scatter([x*1e9 for x in gids_matching_wo_rep_failed], [x*1e9 for x in pids_matching_wo_rep_failed], label="Matching events without repetition failed", s=1, alpha = 0.5, color="green")
        plt.scatter([x*1e9 for x in gids_matching_w_rep_failed], [x*1e9 for x in pids_matching_w_rep_failed], label="Matching events with repetition failed", s=1, alpha = 0.5, color="red")
        plt.axhline(dsd['cut_min_pid']*1e9, color="black", linestyle="--", label="Min GID Cut")
        plt.axvline(dsd['cut_min_gid']*1e9, color="black", linestyle=":", label="Min PID Cut")
        plt.xlabel("GID (s)")
        plt.ylabel("PID (s)")
        plt.legend(loc=(1.04, 0))
        plt.savefig(os.path.join(args.outdir, pathlib.Path(args.file).stem + "_gidpid_space"), bbox_inches = 'tight', dpi = 600)
        # plt.show()
        plt.close()



        print("[INFO] Saved plots to: ", args.outdir)



    print("[INFO] Saved source data container to: ", path)
    print("[DONE] Thank you for using source_decoder.py!")
