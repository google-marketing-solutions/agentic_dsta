# Terraform state storage in Google Cloud Storage
terraform {
  backend "gcs" {
    bucket  = "REPLACE-WITH-YOUR-TERRAFORM-STATE-BUCKET-NAME" # <--- !!! CHANGE THIS
    prefix  = "terraform/agentic_dsta/dev"
  }
}
