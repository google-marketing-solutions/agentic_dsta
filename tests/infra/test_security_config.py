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
"""Regression tests for Cloud Run authentication defaults and Terraform guards."""

import importlib.util
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_YAML_EXAMPLE = REPO_ROOT / "infra/config/app/config.yaml.example"
TFVARS_EXAMPLE = REPO_ROOT / "infra/terraform/terraform.tfvars.example"
ROOT_VARIABLES_TF = REPO_ROOT / "infra/terraform/variables.tf"
ROOT_MAIN_TF = REPO_ROOT / "infra/terraform/main.tf"
CLOUD_RUN_VARIABLES_TF = (
    REPO_ROOT / "infra/terraform/modules/cloud_run_service/variables.tf"
)
CLOUD_RUN_MAIN_TF = (
    REPO_ROOT / "infra/terraform/modules/cloud_run_service/main.tf"
)
GENERATE_TFVARS_PATH = REPO_ROOT / "infra/scripts/deployment/generate_tfvars.py"


def _load_generate_tfvars_module():
  spec = importlib.util.spec_from_file_location(
      "generate_tfvars", GENERATE_TFVARS_PATH
  )
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


def test_example_config_defaults_allow_unauthenticated_to_false():
  """Shipped config.yaml.example must require IAM-authenticated invocation."""
  parsed = yaml.safe_load(CONFIG_YAML_EXAMPLE.read_text(encoding="utf-8"))
  assert parsed["allow_unauthenticated"] is False
  assert parsed["environment"] == "prod"


def test_tfvars_example_defaults_allow_unauthenticated_to_false():
  """Shipped terraform.tfvars.example must set allow_unauthenticated = false."""
  contents = TFVARS_EXAMPLE.read_text(encoding="utf-8")
  assert "allow_unauthenticated      = false" in contents
  assert "allow_unauthenticated      = true" not in contents


def test_generate_tfvars_defaults_to_private_prod(tmp_path: Path):
  """generate_tfvars.py defaults allow_unauthenticated=false and environment=prod."""
  generate_tfvars = _load_generate_tfvars_module()
  input_yaml = tmp_path / "config.yaml"
  output_tfvars = tmp_path / "terraform.tfvars"
  input_yaml.write_text(
      yaml.safe_dump({
          "project_id": "demo-project",
          "region": "us-central1",
          "resource_prefix": "adsta",
      }),
      encoding="utf-8",
  )

  assert (
      generate_tfvars.main(
          ["generate_tfvars.py", str(input_yaml), str(output_tfvars)]
      )
      == 0
  )
  rendered = output_tfvars.read_text(encoding="utf-8")
  assert "allow_unauthenticated = false\n" in rendered
  assert 'environment = "prod"\n' in rendered


@pytest.mark.parametrize("environment", ["prod", "staging", "PROD"])
def test_generate_tfvars_rejects_unauthenticated_in_non_dev(
    tmp_path: Path, environment: str
):
  """allow_unauthenticated=true must be rejected outside dev environments."""
  generate_tfvars = _load_generate_tfvars_module()
  input_yaml = tmp_path / "config.yaml"
  output_tfvars = tmp_path / "terraform.tfvars"
  input_yaml.write_text(
      yaml.safe_dump({
          "project_id": "prod-project",
          "region": "us-central1",
          "environment": environment,
          "resource_prefix": "adsta",
          "allow_unauthenticated": True,
      }),
      encoding="utf-8",
  )

  exit_code = generate_tfvars.main(
      ["generate_tfvars.py", str(input_yaml), str(output_tfvars)]
  )
  assert exit_code == 1
  assert not output_tfvars.exists()


def test_generate_tfvars_rejects_default_env_when_unauthenticated():
  """Omitting environment defaults to prod and refuses allow_unauthenticated=true."""
  generate_tfvars = _load_generate_tfvars_module()
  with pytest.raises(ValueError, match="prohibited outside dev environments"):
    generate_tfvars.validate_and_render_tfvars({
        "project_id": "prod-project",
        "allow_unauthenticated": True,
    })


def test_generate_tfvars_permits_unauthenticated_only_in_explicit_dev():
  """Explicit environment='dev' may opt into allow_unauthenticated=true."""
  generate_tfvars = _load_generate_tfvars_module()
  rendered = generate_tfvars.validate_and_render_tfvars({
      "project_id": "sandbox-dev",
      "environment": "dev",
      "allow_unauthenticated": True,
  })
  assert "allow_unauthenticated = true\n" in rendered
  assert 'environment = "dev"\n' in rendered


def test_terraform_enforces_non_dev_precondition_and_oidc_sa_wiring():
  """Terraform module must block allow_unauthenticated=true outside dev and wire SA."""
  root_vars = ROOT_VARIABLES_TF.read_text(encoding="utf-8")
  root_main = ROOT_MAIN_TF.read_text(encoding="utf-8")
  cr_vars = CLOUD_RUN_VARIABLES_TF.read_text(encoding="utf-8")
  cr_main = CLOUD_RUN_MAIN_TF.read_text(encoding="utf-8")

  assert 'variable "environment"' in root_vars
  assert 'variable "environment"' in cr_vars
  assert (
      '!var.allow_unauthenticated || lower(var.environment) == "dev"' in cr_main
  )
  assert (
      "SCHEDULER_SERVICE_ACCOUNT_EMAIL = google_service_account.run_sa.email"
      in root_main
  )
  assert 'resource "google_cloud_run_v2_service_iam_member" "invoker_service_account"' in cr_main
