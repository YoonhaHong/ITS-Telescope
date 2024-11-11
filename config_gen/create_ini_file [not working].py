    #! /usr/bin/env python3

from tools.create_eudaq_output_dir import create_output_dir
from tools.print_config_list import get_configs
from tools.config_generator_class import ConfigGenerator
import argparse












def create_init_file(template, half_unit=None, ts_config=None, configs=None, output_dir=None):
    configs = get_configs(args.configs)
    confGen = ConfigGenerator(template=template, output_dir=output_dir, file_type='conf')
    if half_unit is not None: confGen.set_value('loc_id', half_unit, 'Producer.MOSS_0')
    if ts_config is not None: confGen.set_value('ts_config_path', ts_config, 'RunControl')
    if configs is not None: confGen.set_value('configs', configs, 'RunControl')

    confGen.save_config(file_name='new_init')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a eudaq2 init file based on a template and a list of config files. Also creates the eudaq2 data output directoires.")
    parser.add_argument('INIT_TEMPLATE', help="eudaq2 init template file.")
    parser.add_argument('--half_unit', '-hu', default=None, help="Half unit to activate. If left empty the value is not changed from the tamplate.")
    parser.add_argument('--ts_config', '-ts', default=None, help="Path to the ts_config.json file to be used with run. If left empty the value is not changed from the tamplate.")
    parser.add_argument('--configs', '-c', nargs='*', default=None, help="Any number of config files, or directories containing config files. The configs will be placed in the order they are passed, from the low VCASB to high. If left empty the value is not changed from the tamplate.")
    parser.add_argument('--output_dir', '-o', default=None, help="Output directory of the .init file. If empty the file is stored at the same location as the tempalte.")
    args = parser.parse_args()

    create_init_file(args.INIT_TEMPLATE, args.half_unit, args.ts_config, args.configs, args.output_dir)