"""Stab scan"""
import time
import datetime
import argparse
from moss_test.test_system.convenience import write_json
from moss_test.moss_unit_if.moss_unit_if import MossUnitIF
from moss_test.moss_unit_if.moss_registers import MossDac, IMuxSelect, VMuxSelect, MossRegion
from moss_test import TestSystem
# Voltages and currents to measure for each region
REF_VOLTAGES_CURRENTS = (
    IMuxSelect.IREF,
    VMuxSelect.VBGR,
    VMuxSelect.VREF,
    VMuxSelect.VDD13,
    VMuxSelect.VDD23,
)

DEFAULT_CFG_PATH = "/home/npl/babyMOSS/sw/config/tb_configs/ts_config_raiser_2_4_W21D4.json5"

def start_logging(args):
    """Starts the logging procedure. Logs the trimming registers and DAC references 
    for every region and half-unit"""
    ts = TestSystem.from_config_file(DEFAULT_CFG_PATH)
    ts.initialize()
    if not ts.get_all_moss_unit_if()[0].is_powered():
        print(f"{ts.moss_chip_id} is not powered on! Power will be supplied, badgaps trimmed and default DACs set.")
        power_ok, _ = ts.get_all_moss_unit_if()[0].power_on()
        assert power_ok, f"Power on of {ts.get_all_moss_unit_if()[0].location()} failed!"
        for moss in ts.get_all_moss_unit_if():
            moss.trim_all_bandgaps()
            #moss.set_default_dacs(MossRegion.ALL_REGIONS)
        
        
        

    for moss in ts.get_all_moss_unit_if():
        all_monitoring_data = []
        for region in range(4):
            monitoring_data = _measure_references(moss, region)
            monitoring_data["Region"] = region
            monitoring_data["TRIM_volt"], monitoring_data["TRIM_curr"] = moss.get_dac_trimming(region)
            all_monitoring_data.append(monitoring_data)
        write_json(
            f"{args.directory}/{ts.moss_chip_id}_{moss.name()}_reference_voltages_currents.json",
            all_monitoring_data,
        )

def _set_moss_monitoring_multiplexer(moss: MossUnitIF, select: MossDac | VMuxSelect | IMuxSelect, region: int
) -> bool:
    """Set the MOSS multiplexer to connect the correct DAC to the monitoring pads.
    Returns True if {dac} is current DAC, False otherwise"""
    if select.name in [item.name for item in IMuxSelect]:
        # self.logger.debug(
        #     f"Current dac - setting IMUX to 0 on all regions and connecting DAC {select.name} "
        #     f"on region {region}"
        # )
        moss.set_monitor_mux(
            MossRegion.ALL_REGIONS
        )  # Disconnect other regions (1 current DAC per unit)
        moss.set_monitor_mux(region, imux=IMuxSelect[select.name])
        return True
    moss.set_monitor_mux(region, vmux=VMuxSelect[select.name])
    return False

def _measure_references(moss: MossUnitIF, region: int) -> dict[str, dict[str, float]]:
    """Measure reference voltages and currents"""
    result_dict = {"Region": region}
    #logger.info(f"Measuring references for unit {moss.location()}, region {region}:")
    for reference in REF_VOLTAGES_CURRENTS:
        is_current_ref = _set_moss_monitoring_multiplexer(moss, reference, region)
        time.sleep(0.25)  # let stabilize
        if is_current_ref:
            mean, stdev = moss.adc.sample_idac(num_samples=10)
            #logger.info(f" ... {reference.name}: {mean} uA")
        else:
            mean, stdev = moss.adc.sample_vdac(region, num_samples=10)
            #logger.info(f" ... {reference.name}: {mean} V")
        result_dict[reference.name] = {"Mean": mean, "Stdev": stdev}
    return result_dict

def main():
    argparser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    argparser.add_argument(
        "directory"
    )
    args = argparser.parse_args()
    start_logging(args)

if __name__ == "__main__":
    main()
