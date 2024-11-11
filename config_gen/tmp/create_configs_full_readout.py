#! /usr/bin/env python3

from tools.config_generator_class import ConfigGenerator
from tools.create_eudaq_output_dir import create_output_dir

REGIONS = [0,1,2,3]

def _create_output_name(prefix, default, vcasb):
    if prefix is None: output_name = f"{default}_VCASB{vcasb}"
    else: output_name = f"{prefix}_{default}_VCASB{vcasb}"
    return output_name

def create_eudaq2_configs(eudaq2_template, device_name, vcasb_list, region, vcasb_default, half_unit=None, nevents=None, region_enabled=None, ibias=None, ibiasn=None, idb=None, ireset=None, vshift=None, vcasn=None, bandgap_trim=None, output_dir=None, settings_dir=None, output_name_prefix=None):
    confGen = ConfigGenerator(template=eudaq2_template, output_dir=output_dir, file_type='conf')
    # TODO: Set other paramters as well
    if nevents is not None: confGen.set_value(f'NEVENTS', nevents, 'RunControl')
    #if region_enabled is not None: confGen.set_value('REGION_ENABLE', region_enabled, 'Producer.MOSS_3')
    #if bandgap_trim is not None: confGen.set_value('BANDGAP_TRIM', bandgap_trim, 'Producer.MOSS_3')
    for r in REGIONS: 
        if ibias is not None: confGen.set_value(f'Region{r}_IBIAS', ibias, 'Producer.MOSS_3')
    for r in REGIONS:
        if ibiasn is not None: confGen.set_value(f'Region{r}_IBIASN', ibiasn, 'Producer.MOSS_3')
    for r in REGIONS:
        if idb is not None: confGen.set_value(f'Region{r}_IDB', idb, 'Producer.MOSS_3')
    for r in REGIONS:
        if ireset is not None: confGen.set_value(f'Region{r}_IRESET', ireset, 'Producer.MOSS_3')
    for r in REGIONS:
        if vshift is not None: confGen.set_value(f'Region{r}_VSHIFT', vshift, 'Producer.MOSS_3')
    for r in REGIONS:
        if vcasn is not None: confGen.set_value(f'Region{r}_VCASN', vcasn, 'Producer.MOSS_3')
    
    # Create data directory
    confGen.regex_replace('!!!DEVICE!!!', device_name, 'DataCollector.dc')
    confGen.regex_replace('!!!HALF_UNIT!!!', half_unit, 'DataCollector.dc')
    confGen.regex_replace('!!!SETTINGS_DIR!!!', settings_dir, 'DataCollector.dc')
    confGen.regex_replace('!!!REGION!!!', str(region), 'DataCollector.dc')

    for r in REGIONS:
        confGen.set_value(f'Region{r}_VCASB', vcasb_default, 'Producer.MOSS_3')
        


    for plane in range(7):
        confGen.regex_replace('!!!HALF_UNIT!!!', half_unit, f'Producer.MOSS_{plane}')
    
    confGen.set_value('loc_id', half_unit, 'Producer.MOSS_3')
    confGen.set_value('REGION_ID', region, 'Producer.MOSS_3')

    config_paths = []
    vcasb_prev='!!!VCASB!!!' # This is a quick fix and will be improved later.
    for vcasb in vcasb_list:
        vcasb_name = f'VCASB{vcasb}' # This is a quick fix and will be improved later.
        confGen.regex_replace(vcasb_prev, vcasb_name, 'DataCollector.dc')
        vcasb_prev = vcasb_name # This is a quick fix and will be improved later.
        confGen.set_value('REGVCASB', vcasb ,'Producer.MOSS_3')
        output_name = _create_output_name(prefix=output_name_prefix, default='EUDAQ2_conf', vcasb=vcasb)
        file_path = confGen.save_config(file_name=output_name)
        print(file_path+',',end=' ')
        config_paths.append(file_path)
    return config_paths

def create_moss_testing_configs(moss_testing_template, device_name, vcasb_list, region, vcasb_default, half_unit=None, ts_config_path=None, top_result_dir=None, region_enabled=None, ibias=None, ibiasn=None, idb=None, ireset=None, vshift=None, vcasn=None, bandgap_trim=None, output_dir=None, settings_dir=None, output_name_prefix=None):
    confGen = ConfigGenerator(template=moss_testing_template, output_dir=output_dir, file_type='json')
    
    if half_unit is not None: confGen.regex_replace('<HU>', half_unit)
    if ts_config_path is not None: confGen.set_value('ts_config', ts_config_path)
    if top_result_dir is not None: confGen.set_value('top_result_dir', top_result_dir)
    if region_enabled is not None: confGen.set_value(half_unit, region_enabled, 'region_readout_enable_masks')
    if bandgap_trim is not None: confGen.set_value('Region.TRIM', bandgap_trim, 'override_registers', half_unit)
    if ibias is not None: confGen.set_value('IBIAS', ibias, 'moss_dac_settings', '*')
    if ibiasn is not None: confGen.set_value('IBIASN', ibiasn, 'moss_dac_settings', '*')
    if idb is not None: confGen.set_value('IDB', idb, 'moss_dac_settings', '*')
    if ireset is not None: confGen.set_value('IRESET', ireset, 'moss_dac_settings', '*')
    if vshift is not None: confGen.set_value('VSHIFT', vshift, 'moss_dac_settings', '*')
    if vcasn is not None: confGen.set_value('VCASN', vcasn, 'moss_dac_settings', '*')
    #Not needed
    #confGen.set_value('modified_region', region)
    
    config_paths = []
    vcasb_values = [(vcasb_default)]*4
    #vcasb_values[0] = 60
    for vcasb in vcasb_list:
        vcasb_values[(region)] = vcasb
        confGen.set_value(f'VCASB', vcasb_values, 'moss_dac_settings', '*')
        output_name = _create_output_name(prefix=output_name_prefix, default='moss_testing_conf', vcasb=vcasb)
        file_path = confGen.save_config(file_name=output_name)
        config_paths.append(file_path)
    
    return config_paths
  
def create_configs(eudaq2_template, moss_testing_template, device_name, vcasb_range, region, vcasb_default, half_unit=None, ts_config_path=None, nevents=None, top_result_dir=None, region_enabled=None, ibias=None, ibiasn=None, idb=None, ireset=None, vshift=None, vcasn=None, bandgap_trim=None, output_dir=None, settings_dir=None, output_name_prefix=None, create_eudaq_data_dir=True):
    vcasb_list = range(vcasb_range[0], vcasb_range[1], vcasb_range[2])
    if output_dir is None: output_dir = 'output'

    conf_file_paths = create_eudaq2_configs(
        eudaq2_template=eudaq2_template,
        device_name=device_name,
        vcasb_list=vcasb_list,
        region=region,
        vcasb_default=vcasb_default,
        half_unit=half_unit,
        nevents=nevents,
        region_enabled=region_enabled,
        ibias=ibias,
        ibiasn=ibiasn,
        idb=idb,
        ireset=ireset,
        vshift=vshift,
        vcasn=vcasn,
        bandgap_trim=bandgap_trim,
        output_dir=output_dir + '/eudaq2',
        settings_dir=settings_dir,
        output_name_prefix=output_name_prefix
    )
    if create_eudaq_data_dir: create_output_dir(conf_files=conf_file_paths)

    create_moss_testing_configs(
        moss_testing_template=moss_testing_template,
        device_name=device_name,
        vcasb_list=vcasb_list,
        region=region,
        vcasb_default=vcasb_default,
        half_unit=half_unit,
        ts_config_path=ts_config_path,
        top_result_dir=top_result_dir,
        region_enabled=region_enabled,
        ibias=ibias,
        ibiasn=ibiasn,
        idb=idb,
        ireset=ireset,
        vshift=vshift,
        vcasn=vcasn,
        bandgap_trim=bandgap_trim,
        output_dir=output_dir + '/fhr_thr',
        settings_dir=settings_dir,
        output_name_prefix=output_name_prefix,
    )




















# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Generate a set of config files for VCASB scan. Both eudaq2 and moss testing configs are created.")
#     parser.add_argument('EUDAQ2_TEMPLATE', default=None, help="Template file for eudaq2 config. If left empty eudaq2 configs are not created.")
#     parser.add_argument('MOSS_TESTING_TEMPLATE', default=None, help="Template file for moss testing config. If left empty moss testing configs are not created.")
#     parser.add_argument('--vcasb_range', '-vs', type=int, nargs=3, help="Three values used to generating the VCASB range. Syntax: (start, stop, step). NOTE: 'stop' is exclusive.")
#     parser.add_argument('--region', '-r', type=int, help="Region to scan.")
#     parser.add_argument('--vcasb_default', '-vd', type=int, help="Defualt VCASB value to write to all other regions." )
#     parser.add_argument('--half_unit', '-hf', default=None, help="Half unit to specify in the config.")
#     # parser.add_argument('--bandgap_trim', '-rt', help="A string with the bandgap trimming on the following format: [0xFF, 0xFF, 0xFF, 0xFF].")
#     parser.add_argument('--output_dir', '-o', default='output', help='Output directory for newly created configs.')
#     parser.add_argument('--output_name_prefix', '-n', help='Name of the generated files.')
#     args = parser.parse_args()


#     eudaq2_template = args.EUDAQ2_TEMPLATE
#     moss_testing_template = args.MOSS_TESTING_TEMPLATE
#     vcasb_list = list(range(*args.vcasb_range))
#     region = args.region
#     vcasb_default = args.vcasb_default
#     half_unit = args.half_unit
#     # bandgap_trim = args.bandgap_trim
#     output_dir = args.output_dir
#     output_name_prefix = args.output_name_prefix


    # create_eudaq2_configs(eudaq2_template=eudaq2_template,
    #                       vcasb_list=vcasb_list,
    #                       region=region,
    #                       vcasb_default=vcasb_default,
    #                       half_unit=half_unit,
    #                       output_dir=output_dir + '/eudaq2',
    #                       output_name_prefix=output_name_prefix)
    
    # create_moss_testing_configs(moss_testing_template=moss_testing_template,
    #                             vcasb_list=vcasb_list,
    #                             region=region,
    #                             vcasb_default=vcasb_default,
    #                             half_unit=half_unit,
    #                             output_dir=output_dir + '/fhr_thr',
    #                             output_name_prefix=output_name_prefix)
