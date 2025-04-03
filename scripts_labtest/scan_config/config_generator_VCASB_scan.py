import json
import os

# Define the range of VCASB values
vcasb_range = [70, 75, 80, 85, 90, 95, 100]  

# Create a folder to save the modified JSON files
output_folder = './VCASB_scan'
os.makedirs(output_folder, exist_ok=True)

# Template for the JSON structure
template_data = {
    "ts_config": "/home/hipex/Telescope/sw/config/tb_configs/ts_config_raiser_3_4_W17E6.json5",
    "enabled_units": ["tb", "bb"],
    "seed": "random",
    "moss_dac_settings": {
        "tb": {
            "IBIAS": 62,
            "IBIASN": 100,
            "IDB": 25,
            "IRESET": 10,
            "VCASN": 104,
            "VSHIFT": 145,
            "VCASB": [70, 70, 70, 70]
        },
        "bb": {
            "IBIAS": 62,
            "IBIASN": 100,
            "IDB": 25,
            "IRESET": 10,
            "VCASN": 104,
            "VSHIFT": 145,
            "VCASB": [70, 70, 70, 70]
        }
    }
}


# Function to modify the VCASB values and generate a new JSON file
def generate_json_with_vcasb(vcasb_value):
    # Create a deep copy of the template data to avoid modifying the original template
    new_data = json.loads(json.dumps(template_data))

    # Modify the VCASB values for both 'tb' and 'bb' units
    new_data['moss_dac_settings']['tb']['VCASB'] = [vcasb_value] * 4
    new_data['moss_dac_settings']['bb']['VCASB'] = [vcasb_value] * 4

    # Generate a unique file name based on the VCASB value
    filename = f"VCASB_{vcasb_value}.json5"
    output_path = os.path.join(output_folder, filename)

    # Write the modified data to the file
    with open(output_path, 'w') as json_file:
        json.dump(new_data, json_file, indent=4)

    print(f"Generated: {output_path}")

# Loop through the VCASB range and generate a file for each value
for vcasb_value in vcasb_range:
    generate_json_with_vcasb(vcasb_value)

