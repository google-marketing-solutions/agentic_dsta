# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import yaml
import sys

def yaml_to_tfvars(yaml_file, tfvars_file):
    """Converts a YAML file to a Terraform .tfvars file."""
    with open(yaml_file, 'r') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            sys.exit(1)

    with open(tfvars_file, 'w') as f:
        for key, value in data.items():
            if isinstance(value, str):
                f.write(f'{key} = "{value}"\n')
            elif isinstance(value, bool):
                f.write(f'{key} = {str(value).lower()}\n')
            elif isinstance(value, list):
                # Convert list to string and replace single quotes with double quotes for Terraform
                f.write(f'{key} = {str(value).replace("\'" , "\"")}\n')
            else:
                f.write(f'{key} = {value}\n')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_tfvars.py <input.yaml> <output.tfvars>")
        sys.exit(1)

    yaml_to_tfvars(sys.argv[1], sys.argv[2])
