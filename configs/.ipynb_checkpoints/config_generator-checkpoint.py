import argparse
import configparser

def modify_and_save_vcasb_values(args):
    config = configparser.ConfigParser(allow_no_value=True, delimiters=("=", ":"))
    config.optionxform = str  # 대소문자 구분
    config.read(args.input_conf)

    section = "Producer.MOSSRAISER_0"
    if section in config:
        for key in config[section]:
            if "VCASB" in key:
                config[section][key] = "70"
                print( key )
    #    with open(output_file, "w") as file:
    #        config.write(file, space_around_delimiters=False)
    else:
        print(f"Section [{section}] not found in {args.input_conf}.")

def vcasb2thr(thr_range = range(10, 30, 1)):
    fit_parameters = 
    arr_thr_vcasb = []
    for threshold in thr_range:
        for_each_thr = {}
        for_each_thr['threshold'] = threshold
        for region, value in fit_parameters.items():
            vcasb = (threshold - fit_parameters[region]['intercept']) / fit_parameters[region]['slope']
            for_each_thr[region] = int(vcasb)
        arr_thr_vcasb.append( for_each_thr )
    return arr_thr_vcasb

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modify VCASB values in a .conf file and save to a new file.")
    parser.add_argument(
        "-i", "--input_conf", 
        type=str, 
        default="./templates/template.conf", 
        help="Path to the input_conf file. Default is './templates/template.conf'."
    )
    parser.add_argument(
        "-v", "--vcasb",
        type=str,
        default="../scripts_labtest/vcasb_values.txt",
        help=".txt file for VCASB value."
    )
    parser.add_argument(
        "-o", "--output", 
        type=str, 
        default="default_output.conf", 
        help="Path to the output file. Default is 'default_output.conf'."
    )
    args = parser.parse_args()

    modify_and_save_vcasb_values(args)