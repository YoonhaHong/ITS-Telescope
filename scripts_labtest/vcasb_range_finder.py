#!/usr/bin/python3.12
"""
Script developed by Maurice Donner (REF: maurice.calvin.donner@cern.ch)
It will automatically determine a VCASB range for a given sensor unit
and is developed for testbeam measurements.
"""
import datetime
import logging
import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
import numpy as np
from result import Result
from moss_test.test_system.exit_codes import TestExitCode
from moss_test.test_system.convenience import load_json, write_json
from moss_scans.base_readout_scan import BaseReadoutScan
from moss_scans.fhr_scan import FakeHitRateScan
from moss_scans.thr_scan import ThresholdScan

#sys.path.append(os.path.join(__file__, "../../analyses"))

# pylint: disable=wrong-import-position, wrong-import-order
sys.path.append( "/home/npl/babyMOSS/sw/analyses" )
from fhr_analysis import FakeHitRateAnalysis  # noqa: E402
from thr_scan_analysis import ThresholdScanAnalysis  # noqa: E402


def range_finder(  # pylint: disable=too-many-locals
    args: argparse.Namespace, ts_path: str, timestamp: str, conf: dict
) -> None:
    """Script iterates over all regions of all enabled units. It will
    1. Choose a region
    2. Search for that regions FHR_limit, and output the VCASB value
    3. Perform a FHR and Threshold scan there
    4. Substract a user-defined range from VCASB and run the same scans there
    """
    logger = logging.getLogger(__name__)
    out_dict = {}

    for unit in conf["enabled_units"]:
        out_dict[unit] = {}

        # Run first check to see if starting values are ok
        initial_config = create_tmp_config(args, ts_path, unit, 0, args.vcasb_default)
        fhr_result, fhr = run_and_analyse_scan(FakeHitRateScan, timestamp, initial_config, unit)

        if fhr_result.is_err():
            logger.error("Initial scan failed. Try lowering vcasb_initial")
            sys.exit(TestExitCode.TEST_FAILED)

        thr_result, thr = run_and_analyse_scan(ThresholdScan, timestamp, initial_config, unit)

        if not thr_result.is_err():
            logger.info(f"Initial FHR scan successful. FHR: {fhr}")
            logger.info(f"Initial THR scan successful. THR: {thr}")

        out_dict[unit]["VCASB_default"] = args.vcasb_default
        out_dict[unit]["FHR_default"] = fhr
        out_dict[unit]["THR_default"] = thr

    for unit in conf["enabled_units"]:
        for region in tqdm(range(4), desc=f"Unit {unit} regions finished"):

            out_dict[unit][region] = {}

            region_mask = 15
            if "region_readout_enable_masks" in conf.keys():
                if unit[:2] in conf["region_readout_enable_masks"].keys():
                    region_mask = conf["region_readout_enable_masks"][unit[:2]]

            # Don't scan disabled regions
            if (region_mask >> region) & 1 == 0:
                continue

            # Find upper limit for FHR
            tmp_config_path, vcasb_max = find_fhr_limit(
                args=args,
                ts_path=ts_path,
                timestamp=timestamp,
                out_dict=out_dict,
                unit=unit,
                region=region,
            )

            try:
                thr_result, thr = run_and_analyse_scan(ThresholdScan, timestamp, tmp_config_path, unit)
            except Exception as e:
                logger.error(f"{e}: Initial configuration is above FHR limit! Aborting...")
                sys.exit(TestExitCode.TEST_FAILED)

            out_dict[unit][region]["THR_max"] = thr[region]
            logger.info(f"THR of {unit} r{region} VCASB {vcasb_max}: {thr[region]}")

            # Measure min setting
            vcasb_min = out_dict[unit][region]["VCASB_max"] - args.vcasb_delta
            tmp_config_path = create_tmp_config(args, ts_path, unit, region, vcasb_min)
            fhr_result, fhr = run_and_analyse_scan(FakeHitRateScan, timestamp, tmp_config_path, unit)
            thr_result, thr = run_and_analyse_scan(ThresholdScan, timestamp, tmp_config_path, unit)
            logger.info(f"FHR of {unit} r{region} VCASB {vcasb_min}: {fhr[region]}")
            logger.info(f"THR of {unit} r{region} VCASB {vcasb_min}: {thr[region]}")
            out_dict[unit][region]["VCASB_min"] = vcasb_min
            out_dict[unit][region]["FHR_min"] = fhr[region]
            out_dict[unit][region]["THR_min"] = thr[region]

        write_json(args.output_dir_path + f"/results_{unit}.json", out_dict)


def find_fhr_limit(  # pylint: disable=too-many-arguments
    *, args: argparse.Namespace, ts_path: str, timestamp: str, out_dict: dict, unit: str, region: int
) -> tuple[str, int]:
    """repeatedly perform FHR scans until the user-defined upper limit has been found"""

    logger = logging.getLogger(__name__)

    # Find Max setting
    vcasb_next, vcasb_previous = args.vcasb_initial, args.vcasb_initial - 1
    failed_once = False
    fhr = [0, 0, 0, 0]
    tmp_config_path = None

    pbar = tqdm(total=args.fhr_limit, desc=f"FHR approaching limit (VCASB={args.vcasb_initial})")
    while fhr[region] < args.fhr_limit:

        logger.info("Running FHR scan for unit {unit} r{region} VCASB {vcasb_next}")
        tmp_config_path = create_tmp_config(args, ts_path, unit, region, vcasb_next)
        result, fhr = run_and_analyse_scan(FakeHitRateScan, timestamp, tmp_config_path, unit)

        if result.is_err():
            failed_once = True
            # If we jumped multiple settings: go one back
            if vcasb_next - vcasb_previous > 1:
                vcasb_next -= 1
            # If not, try one more time
            else:
                logger.info("Trying one more time...")
                result, fhr = run_and_analyse_scan(FakeHitRateScan, timestamp, tmp_config_path, unit)
                if not result.is_err():
                    logger.info("FHR of {unit} r{region} VCASB {vcasb_next}: {fhr[region]}")
                    out_dict[unit][region]["VCASB_max"] = vcasb_next
                    out_dict[unit][region]["FHR_max"] = fhr[region]
                    vcasb_previous = vcasb_next
                    vcasb_next += 1
                    break

                vcasb_next -= 1
                break

        else:
            logger.info(f"FHR of {unit} r{region} VCASB {vcasb_next}: {fhr[region]}")
            out_dict[unit][region]["VCASB_max"] = vcasb_next
            out_dict[unit][region]["FHR_max"] = fhr[region]
            if fhr[region] >= args.fhr_limit:
                break
            if failed_once:
                logger.warning(f"FHR limit not reached. Last successful scan at VCASB {vcasb_next}")
                break

            # for every order of magnitude we are below our limit, move two VCASB up
            if fhr[region] <= 1e-10:  # Handle 0 FHR
                vcasb_step = 10
            else:
                vcasb_step = 2 * int(np.log10(args.fhr_limit / fhr[region]))

            if vcasb_step == 0:
                vcasb_step += 2
            vcasb_previous = vcasb_next
            vcasb_next += vcasb_step

        pbar.set_description(f"FHR approaching limit (VCASB={vcasb_next})")
        pbar.update(fhr[region])

    pbar.close()

    return tmp_config_path, vcasb_next


def create_tmp_config(args: argparse.Namespace, ts_path: str, unit: str, region: int, vcasb: int) -> str:
    """Create a config file for each scan, and save it to the output directory"""

    tmp_config_path = args.output_dir_path + f"/config/{unit}_r{region}_{vcasb}_config.json5"
    tmp_config = load_json(args.scan_config_file)

    # Make ts_config global for all sub scans
    tmp_config["ts_config"] = ts_path

    # Enable only unit that is currently scanned
    tmp_config["enabled_units"] = [unit]

    # Define VCASB list
    vcasb_list = [vcasb if vcasb_list == region else args.vcasb_default for vcasb_list in range(4)]

    # Find where VCASB is defined in tmp_config config file.
    units = list(tmp_config["moss_dac_settings"].keys())
    for key in units:
        if "VCASB" in tmp_config["moss_dac_settings"][key].keys():
            tmp_config["moss_dac_settings"][key]["VCASB"] = vcasb_list  # Write list

    write_json(tmp_config_path, tmp_config)
    return tmp_config_path


def run_and_analyse_scan(
    scan_class: BaseReadoutScan, timestamp: str, conf: dict, unit: str
) -> tuple[Result, float]:
    """Run and analyse automatically, then return the result"""

    logger = logging.getLogger(__name__)
    runscan: BaseReadoutScan = scan_class(
        conf, intermediate_dir_name=f"Range_finder_{timestamp}/", setup_stream_handler=False
    )
    scan_result = runscan.run()
    print(type(scan_result))

    if scan_class == FakeHitRateScan:
        analysis = FakeHitRateAnalysis(top_scan_dir=Path(runscan.output_dir_path), quiet=True)
        analysis.run()
        analysis_result = load_json(
            os.path.join(runscan.output_dir_path, "analysis", "analysis_result.json5")
        )
        value = analysis_result[unit[:2]]["FakeHitRate"]
    elif scan_class == ThresholdScan:
        analysis = ThresholdScanAnalysis(top_scan_dir=Path(runscan.output_dir_path), quiet=True)
        analysis.run()
        analysis_result = load_json(
            os.path.join(runscan.output_dir_path, "analysis", "analysis_result.json5")
        )
        value = analysis_result[unit[:2]]["Threshold average per region"]
    else:
        logger.error(f"Something went wrong during scan {scan_class.__name__}. Aborting...")
        sys.exit(TestExitCode.TEST_FAILED)

    del runscan, analysis
    return scan_result, value


def main() -> None:
    """Execute range_finder"""
    parser = argparse.ArgumentParser(
        description="Determine VCASB range for a single MOSS unit",
        epilog="Required arguments: -d(efault) -i(nitial) -m(inimum) -c(onfig)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-d",
        "--vcasb_default",
        type=int,
        required=True,
        help="Default VCASB setting for regions that are not currently scanned",
    )
    parser.add_argument(
        "-i",
        "--vcasb_initial",
        type=int,
        required=True,
        help="VCASB at which to start looking for the noise limit",
    )
    parser.add_argument(
        "-m",
        "--vcasb_delta",
        type=int,
        required=True,
        help="Difference wrt the maximum VCASB found (DAC units),\
effectively defining the lower limit for determining the VCASB range.",
    )
    parser.add_argument(
        "-c", "--scan_config_file", type=str, required=True, help="Name or path of the config file"
    )
    parser.add_argument("-f", "--fhr_limit", type=float, default=1e-3, help="FHR limit to look for")

    arguments = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    config = load_json(arguments.scan_config_file)
    top_result_dir = config["top_result_dir"]

    # Make ts_path global for all sub scans
    ts_path = config["ts_config"]
    if not os.path.isabs(ts_path):
        sw_path = os.path.join(__file__, "../../../")
        ts_path = os.path.join(sw_path, config["ts_config"])

    ts_config = load_json(ts_path)
    moss_chip_id = ts_config["moss_chip_id"]

    # Create a working directory with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    local_path = f"{moss_chip_id}/RangeFinder"
    folder = f"{moss_chip_id}_RangeFinder_{timestamp}"
    arguments.output_dir_path = os.path.join(top_result_dir, local_path, folder)
    os.makedirs(arguments.output_dir_path)
    os.makedirs(os.path.join(arguments.output_dir_path, "config"))

    with logging_redirect_tqdm():
        tqdm_logger = logger.handlers[-1]
        tqdm_logger.setFormatter(
            logging.Formatter(
                "[%(asctime)s]    %(levelname)-10s %(name)-55s %(funcName)s:%(lineno)d %(message)s"
            )
        )
        range_finder(arguments, ts_path, timestamp, config)

    print(f"Done. Results written to {arguments.output_dir_path}/results.json")


if __name__ == "__main__":
    main()
