#! /usr/bin/env python3

import re
import os
import json
import configparser

class MyConfigParser(configparser.ConfigParser): # Solves a bug where ConfigParser turn all upper case letters into lower case.
    def optionxform(self, optionstr):
        return optionstr

class ConfigGenerator():
    def __init__(self, template, output_dir=None, file_type=None):
        self.template = os.path.abspath(template)
        self.output_dir = self._create_output_dir(output_dir) # TODO: create save file function.
        self.file_type = file_type
        self.config = self._load_file(template)

    def _find_file_type(self, template):
        file_type = template.split('.')[-1]
        return file_type

    def _create_output_name(self, output_name=None):
        if output_name is None: output_name = 'new_config'
        # output_name = output_name.split('.') # TODO: Test this
        # output_name = str(*output_name[:-1])
        output_name = self.output_dir + '/' + output_name + '.' + self.file_type
        return output_name

    def _create_output_dir(self, output_dir):
        if output_dir is None: # Use same output dir as template
            output_dir, file_name = os.path.split(self.template)
            return output_dir
        output_dir = os.path.abspath(output_dir)
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        return output_dir

    def _load_conf_file(self, file_path):
        # config = configparser.ConfigParser()
        config = MyConfigParser()
        config.read(file_path)
        file = {s:dict(config.items(s)) for s in config.sections()} # Turn config object into dict.
        return file
    
    def _load_json_file(self, file_path):
        with open(file_path, 'r') as file:
            file = json.load(file)
        return file

    def _load_text_file(self, file_path):
        pass
        
    def _load_file(self, file_path):
        if self.file_type is None: self.file_type = self._find_file_type(file_path)
        if self.file_type == 'conf': return self._load_conf_file(file_path) 
        elif self.file_type == ('json' or 'json5'): return self._load_json_file(file_path)
        raise TypeError("Could not identify file type of config template. Please specify file type. Allowed type: 'json', 'conf'")

    def _region_enabled_to_bin(self, value):
        # The region enabled value are stored as decimale if not forced to bin.
        return f"{value}"

    def _bandgap_to_hex(self, value_list):
        if type(value_list) == str: return value_list
        # The bandgap values are stored as decimale if not forced to hex.
        return f'[{hex(value_list[0])},{hex(value_list[1])},{hex(value_list[2])},{hex(value_list[3])}]'

    def _create_config_object(self):
        # config = configparser.ConfigParser()
        config = MyConfigParser()
        sections = self.config.keys()
        for section in sections:
            config.add_section(section)
            inner_dict = self.config[section]
            fields = inner_dict.keys()
            for field in fields:
                value = inner_dict[field]
                if field == 'REGION_ENABLE': value = self._region_enabled_to_bin(value)
                if field == 'BANDGAP_TRIM': value = self._bandgap_to_hex(value)
                config.set(section, field, str(value))
        return config

    def _save_conf_file(self, file_name):
        config = self._create_config_object()
        with open(file_name, 'w') as file:
            config.write(file)
        return file_name
        
    def _save_json_file(self, file_name):
        with open(file_name, 'w') as file:
            json.dump(self.config, file, indent=4) #, quote_keys=True)
        return file_name

    def save_config(self, file_name=None):
        """Save the config at it's current state in the output directory.

        Args:
            name (string, optional): The name given to the new file. If 'None' new filed is named "new_config".
        """
        file_name = self._create_output_name(file_name)
        if self.file_type == 'conf': file_path = self._save_conf_file(file_name) 
        elif self.file_type == ('json' or 'json5'): file_path = self._save_json_file(file_name)
        # TODO: return path to newly created file. 
        return file_path

    def _find_key_in_nested_dict(self, dict_to_search, key):
        """Search a nested dictionary for a specific key. Returns a list with all sub-dictionaries that containts the given key. This includes the top-level dictionary as well.

        Args:
            key (any): The key to search the nested dict for. TODO: Must the key be a string?

        Returns:
            list: A list containg sub-dictionaries that containt the given key. This includes the top-level dictionary as well.
        """
        output = []
        def search_dict(dict_to_search, key):
            for current_key in dict_to_search.keys():
                if current_key == key: output.append(dict_to_search)
                if not isinstance(dict_to_search[current_key], dict): continue
                search_dict(dict_to_search[current_key], key)
        search_dict(dict_to_search, key)
        return output
    
    def _to_string(self, dictionary):
        return str(dictionary)

    def _to_dict(self, string):
        try:
            return eval(string)
        except NameError:
            return string

    def _substitute(self, pattern, replace, string):
        pattern = re.compile(pattern)
        matches = pattern.findall(string)
        if matches: string = re.sub(pattern, replace, string)
        return string

    def _sanitize_input(self, string):
        pattern = '"'
        replace = '\''
        return self._substitute(pattern, replace, string)

    def _regex_replace(self, pattern, replace, string):
        pattern = self._sanitize_input(pattern)
        replace = self._sanitize_input(replace)
        return self._substitute(pattern, replace, string)
    
    def set_value(self, param, value, *sub_cat):
        """Set a paramters to a specific value in the config. If there are several entries that matches 'param' all of them are set.
        The function works by searching through a nested dictionary representing the config. To limit the search to a specific category use any number of '*sub_cat' to define the start of the search.
        If the paramaters, or sub-categories, don't exits they are created. 

        Args:
            param (string): The name of the entry to write the value to.
            value (any): The value to be written to the config.
            *sub_cat (string): Any number of sub-categories to define the start of the search.
        """
        current_dict = self.config
        for dir in sub_cat:
            if dir not in current_dict: current_dict[dir] = {} # Create sub-category if it don't exits
            current_dict = current_dict[dir]
        dicts = self._find_key_in_nested_dict(current_dict, param)
        if not dicts: # Create the paramter if it don't exits 
            current_dict[param] = {} 
            dicts = [current_dict]
        for _dict in dicts:
            _dict[param] = value

    def get_value(self, param, *sub_cat):
        """Get a paramater from the config. If there are several entires that matches 'param' all of them are returned.
        The functions works by searching through a nested dictionary representing the config. To limit the search to a specific category use any number of '*sub_cat' to define the start of the search.
        If the paramater, or sub-categories, don't exits the function returns an empty list.

        Args:
            param (string): The name of the entry to get the value from.
            *sub_cat (string): Any number of sub-categories to define the start of the search.

        Returns:
            list: A list containing all the values retrived from the config.
        """
        current_dict = self.config
        for dir in sub_cat:
            if dir not in current_dict: current_dict[dir] = {} # Create sub-category if it don't exits
            current_dict = current_dict[dir]
        dicts = self._find_key_in_nested_dict(current_dict, param)
        ret = []
        for _dicts in dicts:
            ret.append(_dicts[param])
        return ret

    def regex_replace(self, pattern, replace, *sub_cat):
        """Uses regular expression to search and replace a pattern in the config.
        The enitre config is load as one string (with no new line char), and the 
        operation is performed on the entire string.
        To limit the search to a specific category use any number of '*sub_cat' to define the start of the search.
        If the sub-category don't exits the functions does nothing.

        Args:
            pattern (string): The pattern to search for.
            replace (string): The replacement for the found pattern.
            *sub_cat (string): Any number of sub-categories to define the start of the search.
        """
        current_dict = self.config
        previous_dict = None
        previous_key = None
        for dir in sub_cat:
            if dir not in current_dict: return # Return if sub-category don't exits.
            previous_key = dir
            previous_dict = current_dict
            current_dict = current_dict[dir]
        string_config = self._to_string(current_dict)
        string_config = self._regex_replace(pattern, replace, string_config)
        dict_config = self._to_dict(string_config)
        if previous_dict: previous_dict[previous_key] = dict_config
        else: self.config = dict_config

def create_config(template, output_dir=None, output_name=None, replace=None, set_value=None, file_type=None, print_and_exit=False):
    """Creates a config using the ConfigGenerator class. The function can either utilize the regex_replace() method, the set_value() method, or both.

    Args:
        template (string): Path to the template to modify.
        output_dir (string): Output path for the newly created config. If left empty the config is stored in the same directory of as the template.
        replace (list/tuple, optional): A list/tumpe of list/tumpes containing the arguments for the 'regex_replace()' method from the ConfigGenerator class. The arguments must be placed in the correct order. Defaults to None.
        set_value (list/tuple, optional): A list/tumpe of list/tumpes containing the arguments for the 'regex_replace()' method from the ConfigGenerator class. The arguments must be placed in the correct order. Defaults to None.
        print_and_exit (bool, optional): Print the config to terminal then exit without saving the config. Used for testing commands before creating files.
    """
        
    def unpack_arguments(args):
        rest = ()
        first, second, *rest = args
        return first, second, tuple(rest)
    
    confGen = ConfigGenerator(template, output_dir, file_type=file_type)
    if replace:
        for args in replace:
            pattern, _replace, sub_cat = unpack_arguments(args)
            confGen.regex_replace(pattern, _replace, *sub_cat)
    if set_value:
        for args in set_value:
            value, param, sub_cat = unpack_arguments(args)
            confGen.set_value(value, param, *sub_cat)
    if print_and_exit:
        print(json.dumps(confGen.config, indent=4))
        return
    confGen.save_config(output_name)

import argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('TEMPLATE', help='Template file.')
    parser.add_argument('--file_name', '-n')
    parser.add_argument('--output_dir', '-o', default=None, help='Output directory for the newly created config file. If left empty the output direcotyr is the same as the template directory.')
    parser.add_argument('--file_type', '-fp', default=None, help="Specify file type. If empty the program will attempt to identiy file type from file descriptor.")
    args = parser.parse_args()

    # confGen = ConfigGenerator(template=args.TEMPLATE, output_dir=args.output_dir)
    # sub_cat = ['moss_dac_settings', '*']
    # confGen.set_value(10, 'IBIAS', *sub_cat)
    # print(confGen.get_value('IBIAS'))
    # pattern = r"IBIAS"
    # replace = r"TB_PS_Jun_2024"
    # confGen.regex_replace(pattern, replace)
    # print(json.dumps((confGen.config), indent=4))
    set_value = [('Region3_VCASB', 100, 'Producer.MOSS_0')]
    replace = [('!!!VCASB!!!', '75')]
    create_config(args.TEMPLATE, set_value=set_value, replace=replace, output_name='test_natestme', output_dir='deleteme', file_type=args.file_type)