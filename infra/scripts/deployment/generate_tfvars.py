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
"""Converts operator YAML configuration into a validated Terraform .tfvars file."""

import json
import sys
from typing import Any
import yaml

ALLOWED_ENVIRONMENTS = frozenset({"dev", "staging", "prod"})


def validate_and_render_tfvars(raw_config: Any) -> str:
  """Validates security invariants and renders Terraform .tfvars assignments."""
  if raw_config is None:
    config: dict[str, Any] = {}
  elif isinstance(raw_config, dict):
    config = dict(raw_config)
  else:
    raise ValueError("Configuration root must be a YAML mapping.")

  config.setdefault("environment", "prod")
  config.setdefault("allow_unauthenticated", False)

  environment = str(config["environment"]).strip().lower()
  if environment not in ALLOWED_ENVIRONMENTS:
    raise ValueError(
        f"Invalid environment {environment!r}; expected one of "
        f"{sorted(ALLOWED_ENVIRONMENTS)}."
    )

  allow_unauthenticated = config["allow_unauthenticated"]
  if not isinstance(allow_unauthenticated, bool):
    raise ValueError("allow_unauthenticated must be a boolean (true or false).")

  if allow_unauthenticated and environment != "dev":
    raise ValueError(
        "Refusing to set allow_unauthenticated=true when environment is "
        f"{environment!r}. Unauthenticated Cloud Run invocation is prohibited "
        "outside dev environments."
    )

  config["environment"] = environment
  lines: list[str] = []
  for key, value in config.items():
    if isinstance(value, bool):
      lines.append(f"{key} = {str(value).lower()}")
    elif isinstance(value, (str, list, dict, int, float)):
      lines.append(f"{key} = {json.dumps(value)}")
    elif value is None:
      lines.append(f"{key} = null")
    else:
      raise ValueError(f"Unsupported value type for {key!r}: {type(value).__name__}")

  return "\n".join(lines) + "\n"


def yaml_to_tfvars(yaml_file: str, tfvars_file: str) -> None:
  """Reads a YAML config file, validates it, and writes a Terraform .tfvars file."""
  with open(yaml_file, "r", encoding="utf-8") as input_handle:
    data = yaml.safe_load(input_handle)

  rendered = validate_and_render_tfvars(data)

  with open(tfvars_file, "w", encoding="utf-8") as output_handle:
    output_handle.write(rendered)


def main(argv: list[str]) -> int:
  """CLI entrypoint for generate_tfvars.py."""
  if len(argv) != 3:
    print("Usage: python generate_tfvars.py <input.yaml> <output.tfvars>")
    return 1

  try:
    yaml_to_tfvars(argv[1], argv[2])
  except (OSError, yaml.YAMLError, ValueError) as exc:
    print(f"Error generating tfvars: {exc}", file=sys.stderr)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main(sys.argv))
