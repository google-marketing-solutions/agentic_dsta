# Agentic Dynamic Signal Target Ads (DSTA)

Copyright 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This is not an officially supported Google product. This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security).

## Table of Contents

- [Introduction](#introduction)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Deployment](#deployment)
  - [Local Development](#local-development)
- [Solution Overview](#solution-overview)
- [Architecture](#architecture)
- [Key Components](#key-components)
- [Prerequisites](#prerequisites)
  - [Google Cloud](#google-cloud)
  - [Local Environment](#local-environment)
- [Authentication and Credentials](#authentication-and-credentials)
  - [Google Cloud API Key (for Weather/Pollen APIs)](#google-cloud-api-key-for-weatherpollen-apis)
  - [Google Ads API Credentials (OAuth2 User Flow)](#google-ads-api-credentials-oauth2-user-flow)
- [Installation and Deployment](#installation-and-deployment)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Configure Your Deployment](#step-2-configure-your-deployment)
  - [Step 3: Run the Deployment Script](#step-3-run-the-deployment-script)
  - [Step 4: Grant Service Account Access (Cloud Run)](#step-4-grant-service-account-access-cloud-run)
- [Configuration Reference](#configuration-reference)
- [Data Models and APIs](#data-models-and-apis)
  - [Firestore Data Model](#firestore-data-model)
  - [API Specifications](#api-specifications)
  - [SA360 Integration (via Bulk Sheets)](#sa360-integration-via-bulk-sheets)
- [Extending the Solution with More APIs](#extending-the-solution-with-more-apis)
  - [Step 1: Register Your API in API Hub](#step-1-register-your-api-in-api-hub)
  - [Step 2: Configure API Key Authentication (If Required)](#step-2-configure-api-key-authentication-if-required)
- [Logging](#logging)
  - [Log Format](#log-format)
  - [Configuring Log Level](#configuring-log-level)
  - [Viewing Logs in Cloud Logging](#viewing-logs-in-cloud-logging)
  - [Error Handling](#error-handling)
- [Usage](#usage)
  - [Interactive Web Interface](#interactive-web-interface)
  - [Decision Agent Workflow and Configuration](#decision-agent-workflow-and-configuration)
    - [Automated Execution via Cloud Scheduler](#automated-execution-via-cloud-scheduler)
- [Security Best Practices](#security-best-practices)
  - [Created Service Accounts](#created-service-accounts)
- [Troubleshooting](#troubleshooting)
- [Cost](#cost)
- [Destroying the Infrastructure](#destroying-the-infrastructure)
- [Solution Artifacts](#solution-artifacts)
  - [About Spec Files](#about-spec-files)
  - [Enhancing Specifications](#enhancing-specifications)

## Introduction

The Agentic Dynamic Signal Target Ads (DSTA) solution is a powerful, automated marketing framework designed to help marketers forecast and activate advertising campaigns based on real-time demand signals. It uses an agentic architecture to integrate data from various sources (Google Ads, SA360, Weather, Pollen, etc.) and automate campaign management decisions.

This guide provides all the necessary information for deploying, configuring, and managing the Agentic DSTA infrastructure on Google Cloud Platform.

## Project Structure

*   **`agentic_dsta/`**: Contains the application source code, including agents, tools, and the FastAPI server.
    *   See [agentic_dsta/README.md](agentic_dsta/README.md) for local development instructions.
*   **`infra/`**: Contains the Infrastructure as Code (Terraform) and deployment scripts.
*   **`tests/`**: Contains unit and integration tests for the solution.

## Getting Started

### Deployment

This solution is deployed to Google Cloud Run using Terraform. 

### Local Development

For instructions on running the application locally for development and testing, please refer to the **[Application README](agentic_dsta/README.md)**.

## Solution Overview

The core of this solution is a multi-tool framework built with the Agent Development Kit (ADK). This framework includes several specialized toolsets that are used by the agents to make intelligent marketing decisions:

*   **API Hub Toolset:** This toolset can dynamically discover and call any API registered in your Google Cloud API Hub instance. Its tools allow agents to fetch data from external sources, which is then used for decision-making.
*   **Firestore Toolset:** This toolset acts as the memory and configuration hub. It has tools to read, write, query, and delete documents in Firestore. It is used to store and retrieve business rules, campaign instructions, and location data.
*   **GoogleAds Toolset:** A specialized toolset to directly manage your Google Ads campaigns. Its capabilities include:
    *   **Fetching Campaign Details:** Retrieve a full overview of a campaign's settings and current status.
    *   **Updating Campaign Status:** Programmatically pause or enable campaigns.
    *   **Modifying Campaign Budgets:** Adjust the budget for any campaign.
    *   **Updating Campaign Bidding Strategies:** Change the bidding strategy of a *campaign*. Supported standard strategies include:
        *   `MAXIMIZE_CONVERSIONS` (Optionally with `target_cpa_micros` in `strategy_details`)
        *   `MAXIMIZE_CONVERSION_VALUE` (Optionally with `target_roas` in `strategy_details`)
        *   `MANUAL_CPC` (Optionally with `enhanced_cpc_enabled` in `strategy_details`)
        *   `TARGET_SPEND`
        *   `TARGET_IMPRESSION_SHARE`: Requires `strategy_details` with `location` (e.g., `ANYWHERE_ON_PAGE`) and `location_fraction_micros` (e.g., 500000 for 50%).
        *   `MANUAL_CPM`
        *   `MANUAL_CPV`
        *   `PERCENT_CPC`
        *   `COMMISSION`
        *   Can also switch to a portfolio bidding strategy by providing the resource name.
    *   **Updating Portfolio Bidding Strategies:** Modify an existing *portfolio* bidding strategy's type and parameters using the `update_portfolio_bidding_strategy` tool. Supported types include:
        *   `MAXIMIZE_CONVERSIONS` (Optionally with `target_cpa_micros`)
        *   `TARGET_CPA` (Requires `target_cpa_micros`)
        *   `TARGET_ROAS` (Requires `target_roas`)
        *   `TARGET_SPEND` (Optionally with `cpc_bid_ceiling_micros`)
    *   **Managing Geo-Targeting:** Update the geographic targeting for campaigns and ad groups by adding or removing location IDs.
    *   **Searching for Geo-Targets:** Look up geo-target constants by location name (e.g., "New York City") to find the correct IDs for targeting.
    *   **Listing Shared Budgets:** Retrieve a list of all explicitly shared budgets in the account that are currently enabled.
    *   **Updating Shared Budgets:** Modify the amount of an existing explicitly shared budget using its resource name.
*   **SA360 Toolset:** This toolset is designed for Search Ads 360 management. It uses the SA360 Reporting API for fetching real-time data and a Google Sheet as an intermediary for bulk updates.
    *   **Fetching Campaign Details:** Retrieve a full overview of a campaign's settings and current status directly from SA360.
    *   **Updating Campaign Status:** Programmatically pause or enable campaigns in Google Sheet.
    *   **Modifying Campaign Budgets:** Adjust the budget for any campaign in Google Sheet.
    *   **Updating Geo-Targeting:** Add a geolocation to the list of locations of the campaign in Google Sheet.
    *   **Negative Geo-Targeting:** Remove a geolocation from the list of locations of the campaign in Google Sheet.
    *   **Fetching Campaign Details - Google Sheet:** Retrieve a full overview of a campaign's settings and current status from user managed Google Sheet.
*   **Decision Agent:** This is the orchestrator agent responsible for automated execution. It takes a high-level goal (e.g., from the Cloud Scheduler job), uses the toolsets to gather data, and then delegates campaign management tasks based on the retrieved information and business rules.
*   **Marketing Agent:** This is the interactive agent that is used to perform complex tasks and act on campaigns in a conversational manner. It is intended for interactive use through the ADK web UI.

The entire solution is deployed as a containerized application on Google Cloud Run and is managed through Infrastructure as Code (IaC) with Terraform.

## Architecture

The following diagram illustrates the architecture of the Agentic Dynamic Signal Target Ads solution:

```
[User/Scheduler] -> [Cloud Run (FastAPI)] -> [Marketing Agent / Decision Agent]
                                                       |
            +---------------------+----------------------------------------------+---------------------+
            |                     |                                              |                     |
    [Google Ads Toolset]    [SA360 Toolset]----------------+          [Firestore Toolset]    [API Hub Toolset]
            |                     |                        |                     |                     |
      [Google Ads API]      [Google Sheet]           [Reporting API]        [Firestore DB]      [External APIs]
                                   | (manual upload)        |                                 (e.g., Weather, Pollen)
                                   v               (For campaign details)
                                [SA360]<--------------------+
```

**Workflow Details:**

*   **Google Ads:** The `Google Ads Toolset` allows the agent to interact directly with the Google Ads API to manage campaigns.
*   **SA360:** The `SA360 Toolset` allows the agent to interact with SA360 Reporting API to get campaign details & update a Google Sheet with campaign changes. The user is responsible for uploading this sheet to SA360.


## Key Components

*   **Google Cloud Run:** Hosts the containerized FastAPI application that serves the agent endpoints.
*   **Google Cloud Firestore:** Stores business rules, campaign settings, and other configuration data.
*   **Google Cloud Secret Manager:** Securely stores all API keys, tokens, and other sensitive credentials.
*   **Google Cloud API Hub:** Acts as a central registry for all external APIs used by the solution.
*   **Google Cloud Build & Artifact Registry:** Automates the process of building and storing the application's container image.
*   **Terraform:** Manages the entire Google Cloud infrastructure as code, enabling repeatable, one-click deployments.

## Prerequisites

### Google Cloud

*   A Google Cloud project with billing enabled.
*   The **gcloud CLI** installed and authenticated:
    ```bash
    gcloud auth login
    gcloud config set project [YOUR_PROJECT_ID]
    ```

*   The user or principal running the `deploy.sh` script for the *first time* needs sufficient permissions to create and configure service accounts, IAM policies, and other project resources. The `roles/owner` and `roles/iam.serviceAccountTokenCreator` role is the simplest way to ensure this.
*   The `deploy.sh` script creates a dedicated service account (`<resource_prefix>-deployer@<project_id>.iam.gserviceaccount.com`) and grants it a specific set of roles required to deploy and manage the application infrastructure. These roles include, but are not limited to:
    *   `roles/viewer`
    *   `roles/serviceusage.serviceUsageAdmin`
    *   `roles/storage.admin`
    *   `roles/cloudbuild.builds.editor`
    *   `roles/artifactregistry.admin`
    *   `roles/run.admin`
    *   `roles/iam.serviceAccountUser`
    *   `roles/iam.serviceAccountTokenCreator`
    *   `roles/secretmanager.admin`
    *   `roles/cloudscheduler.admin`
    *   `roles/firebase.admin`
    *   `roles/apihub.admin`
    *   And others as defined in `infra/deploy.sh`.
*   Subsequent runs of `deploy.sh` use this service account's permissions via impersonation.

*   **Enable/Provision the following APIs in your project if not already enabled:**
    *   [Compute Engine API](https://console.cloud.google.com/apis/library/compute.googleapis.com)
    *   [Provision Google Cloud API Hub API](https://docs.cloud.google.com/apigee/docs/apihub/provision) (Ensure "Enable Semantic search capability" is checked)
    *   [Spreadsheets API](https://console.cloud.google.com/marketplace/product/google/sheets.googleapis.com)
    *   [SA360 Reporting API](https://console.cloud.google.com/marketplace/product/google/searchads360.googleapis.com)
    *   [Google Ads API](https://console.cloud.google.com/marketplace/product/google/googleads.googleapis.com)
    *   [Pollen API](https://console.cloud.google.com/marketplace/product/google/pollen.googleapis.com)
    *   [AirQuality API](https://console.cloud.google.com/marketplace/product/google/airquality.googleapis.com)
    *   [Weather API](https://console.cloud.google.com/marketplace/product/google/weather.googleapis.com)

### Local Environment

*   **Terraform:** Version 1.14.2 or later.
*   **Python:** Version 3.10 or later.
*   **Git:** For cloning the repository.

## Authentication and Credentials

This solution requires several credentials to access Google Cloud and Google Ads APIs. Follow these steps to generate and collect them before proceeding with the deployment.

### Google Cloud API Key (for Weather/Pollen APIs)

This solution uses public Google APIs (Weather, Pollen, AirQuality) which require a standard Google API Key.

2.  **Create API Key:**
    *   Go to the [Credentials page](https://console.cloud.google.com/apis/credentials) in your Google Cloud Console.
    *   Click **Create Credentials** > **API key**.
    *   Restrict the API key to only the APIs you intend to use (e.g., Weather API, Pollen API, AirQuality API).
3.  **Save Key:**
    *   Copy the key and save it. You will need to provide this as a secret named `GOOGLE_API_KEY` during deployment.

### User Credentials for Google Ads & SA360 (OAuth2 User Flow)

The application uses OAuth 2.0 credentials for a *user account* to interact with the Google Ads and Search Ads 360 APIs. These credentials (client ID, client secret, and refresh token) are securely stored in Google Secret Manager and accessed at runtime. This method is used when Application Default Credentials of the Cloud Run service account are insufficient or when forced via environment variables.

**User Credential Secrets:**

The following secrets are used for user-based OAuth 2.0 authentication:

*   `USER_CLIENT_ID`: The OAuth 2.0 Client ID obtained from your Google Cloud Console.
*   `USER_CLIENT_SECRET`: The OAuth 2.0 Client Secret.
*   `USER_REFRESH_TOKEN`: The OAuth 2.0 Refresh Token for the authorized user.

These secrets will be created or updated in Google Secret Manager when you run the `infra/deploy.sh` script. You will be prompted to enter the values interactively. Follow the steps below to obtain the necessary values *before* running the deployment script.

Follow the steps below to obtain your Developer Token, and generate the credentials to store in Secret Manager.

1.  **Developer Token:**
    *   Apply for a developer token through your Google Ads manager account. Follow the instructions at [Get a Developer Token](https://developers.google.com/google-ads/api/docs/first-call/dev-token).

2.  **OAuth2 Client ID and Client Secret:**
    *   Configure an [OAuth2 consent screen](https://console.cloud.google.com/apis/credentials/consent) (If not already existing) and create credentials for a **Web app**. This will provide you with a client ID and client secret. Follow the guide at [Create a Client ID and Client Secret](https://developers.google.com/google-ads/api/docs/oauth/cloud-project#create_a_client_id_and_client_secret).
    *   **Important:** On your OAuth consent screen [configuration](https://console.cloud.google.com/auth/scopes), you must add the following scopes:
    *   `https://www.googleapis.com/auth/adwords` (for Google Ads)
    *   `https://www.googleapis.com/auth/doubleclicksearch` (for SA360)
    *   `https://www.googleapis.com/auth/spreadsheets` (for Google Sheets)
    *   `https://www.googleapis.com/auth/cloud-platform` (for Google Cloud)
    *   Create OAuth2 Client ID and Client Secret for Web Application. 
        *   Make sure to add `http://127.0.0.1:8080` to the list of **Authorized redirect URIs**. The `generate_user_credentials.py` script uses this URI to capture the authorization response. Failure to add this will result in a `redirect_uri_mismatch` error.

3.  **Generate Refresh Token:**
    *   To generate the refresh token, you will use a helper script. This script automates the OAuth2 flow to get the necessary refresh token.
    *   **Prerequisites:**
        *   Ensure you have Python3 installed.
        *   Install the Google Ads Python library:
            ```bash
            pip3 install google-ads
            ```
    *   **Download the script:** Provide a link to the script or include it in your repository. For example, if you've adapted `generate_user_credentials.py`:
        *   You can find the example script here: [`generate_user_credentials.py`](https://github.com/googleads/google-ads-python/blob/main/examples/authentication/generate_user_credentials.py)
    *   **Run the script:** Execute the script, providing your Client ID and Client Secret obtained in the previous step:
        ```bash
        python3 generate_user_credentials.py --client_secrets_path YOUR_CLIENT_SECRET_JSON_PATH
        ```
    *   **Authorization:** The script will output a URL. Copy this URL and open it in your web browser.
    *   Log in with the Google account that has access to the Google Ads account you want to manage.
    *   Grant the requested permissions (it should include the `adwords` scope).
    *   After granting permissions, you'll be redirected to a page on `127.0.0.1:8080` (or an error page if the redirect URI wasn't set up correctly). The script will capture the authorization code from the redirect.
    *   **Result:** The script will then exchange the authorization code for a refresh token and an access token, and print the refresh token to the console. It might also save the credentials to a `google-ads.yaml` file in your home directory.
    *   **Copy Credentials:** Securely copy the Client ID, Client Secret, and the generated Refresh Token. You will need these values when running the `infra/deploy.sh` script.

4.  **Review Collected Credentials:**
    *   Ensure you have the following list ready:
        *   Google Ads Developer Token
        *   OAuth2 Client ID
        *   OAuth2 Client Secret
        *   OAuth2 Refresh Token
        *   Google API Key (for Weather/Pollen etc.)

You will be prompted for all these secret values (USER_CLIENT_ID, USER_CLIENT_SECRET, USER_REFRESH_TOKEN, GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_API_KEY, etc.) when running the `infra/deploy.sh` script in a later step.

### Service Account vs. User Credentials

The application can authenticate to Google Ads, SA360 Reporting API and Google Sheet using two methods:

1.  **Service Account Credentials (Default for Cloud Run):**
    *   When deployed on Google Cloud Run, the application uses the assigned service account's Application Default Credentials (`[resource_prefix]-runner@[project_id].iam.gserviceaccount.com`).
    *   This is the recommended method for automated workflows running on GCP.
    *   Requires granting this service account appropriate access within your Google Ads and SA360 accounts and the Google Sheet used for bulk uploads.

2.  **User Credentials (OAuth2):**
    *   This method uses the OAuth2 credentials (Client ID, Client Secret, Refresh Token) of a specific user.
    *   It's primarily intended for:
        *   **Local Development:** When running the agent locally, where service account credentials are not available.
        *   **Permission Issues:** If the Cloud Run service account lacks specific permissions that the user account has.
    *   The `generate_user_credentials.py` script helps you obtain the `USER_REFRESH_TOKEN`.
    *   To force the use of User Credentials even when on Cloud Run, you can set the following environment variables to `True`:
        *   `GOOGLE_ADS_FORCE_USER_CREDS=True`
        *   `SA360_FORCE_USER_CREDS=True`

The `agentic_dsta/tools/auth_utils.py` module contains the logic to automatically select the appropriate credentials based on the environment and these force flags.


## Installation and Deployment

The deployment process is fully automated with a one-click script.

### Step 1: Clone the Repository

Clone this repository to your local machine:

```bash
git clone [REPOSITORY_URL]
cd gta-solutions/infra
```

### Step 2: Configure Your Deployment

All deployment parameters are managed in the `config.yaml` file.

1.  Use the provided example file as a template:
    ```bash
    cp config/app/config.yaml.example config/app/config.yaml
    ```

2.  **Edit the configuration:**
    Open `config/app/config.yaml`.
    *   Fill in the non-sensitive values.
    *   **Advanced Secrets:** If you need to inject additional secrets like `GOOGLE_API_KEY`, add them to the `additional_secrets` section:
        ```yaml
        additional_secrets: ["GOOGLE_API_KEY"]
        ```
    *   Do **not** put the actual secret values in this file. You will be prompted for them during deployment.

### Step 3: Run the Deployment Script

Execute the `deploy.sh` script from the `infra` directory:

```bash
bash deploy.sh
```

When you run this script, Terraform will prompt you to enter the values for your secrets (defined in `config.yaml` and default secrets like `GOOGLE_ADS_DEVELOPER_TOKEN`).

**Important:** You must enter these values in a specific **Map format** when prompted for `var.secret_values`.
Format: `{"SECRET_NAME_1"="value1", "SECRET_NAME_2"="value2", ...}`

Example input:
`{"GOOGLE_ADS_DEVELOPER_TOKEN"="ReplaceWithToken", "GOOGLE_API_KEY"="ReplaceWithApiKey", "USER_CLIENT_ID"="ReplaceWithClientId", "USER_CLIENT_SECRET"="ReplaceWithClientSecret", "USER_REFRESH_TOKEN"="ReplaceWithRefreshToken"}`

The script matches these keys to the `additional_secrets` in your config and the default required secrets.

This script will:
1.  Check for the required secrets in Google Secret Manager and create them if they don't exist (this is the interactive part).
2.  Build the application's Docker image.
3.  Push the image to Google Artifact Registry.
4.  Generate a `terraform.tfvars` file from your `config.yaml`.
5.  Initialize and apply the Terraform configuration to deploy all the necessary infrastructure.

The deployment will take several minutes to complete.

### Step 4: Grant Service Account Access (Cloud Run)

The solution runs on Google Cloud Run and uses a dedicated Service Account for its identity. To allow the agent to manage your Google Ads campaigns, you must add this Service Account to your Google Ads account.

1.  **Identify the Service Account Email:**
    After deployment (or based on your config), the Service Account email will be:
    `[resource_prefix]-runner@[project_id].iam.gserviceaccount.com`
    *   Example: `dsta-runner@my-project-id.iam.gserviceaccount.com`

2.  **Add to Google Ads:**
    *   Log in to your Google Ads account.
    *   Navigate to **Admin** > **Access and security**.
    *   Click the **+** button to add a user.
    *   Enter the **Service Account email** address.
    *   Select **Standard** (or Admin) access level.
    *   Click **Send invitation**.
    *   *Note: Service Accounts typically accept the invitation automatically or do not require acceptance steps if within the same organization context.*

## Configuration Reference

The following table describes each parameter in the `config.yaml` file:

| Parameter                      | Description                                                                                             | Example                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `project_id`                   | **Required.** Your Google Cloud Project ID.                                                              | `"[YOUR_PROJECT_ID]"`                        |
| `region`                       | The primary Google Cloud region for deploying resources.                                                | `"us-central1"`                               |
| `resource_prefix`              | A prefix for all resource names (Service Accounts, Buckets, etc.).                                      | `"gta-demo"`                                  |
| `allow_unauthenticated`        | If `true`, the Cloud Run service will be publicly accessible. Set to `false` for production.           | `false`                                       |
| `firestore_database_type`      | The type of Firestore database to create (`FIRESTORE_NATIVE` or `DATASTORE_MODE`).                        | `"FIRESTORE_NATIVE"`                          |
| `additional_secrets`           | List of extra secrets to manage (e.g., `GOOGLE_API_KEY`).                                               | `["GOOGLE_API_KEY"]`                          |
| `googleads_scheduler_schedule` | The cron schedule for triggering the Google Ads agent.                                                  | `"0 0 * * *"`                                 |
| `sa360_scheduler_schedule`     | The cron schedule for triggering the SA360 agent.                                                       | `"0 0 * * *"`                                 |
| `googleads_customer_id`        | The Google Ads Customer ID for the scheduler job payload.                                               | `"1234567890"`                                |
| `sa360_customer_id`            | The SA360 Customer ID for the scheduler job payload.                                                    | `"1234567890"`                                |

## Data Models and APIs

### Firestore Data Model

The solution uses Google Cloud Firestore to store business rules and campaign configurations. The primary collections are `GoogleAdsConfig`, `SA360Config`, and `CustomerInstructions`.

**Collection: `GoogleAdsConfig`**

Each document in this collection represents a Google Ads customer account. The document ID should be the `customer_id`.

**Document Schema:**

*   **`customerId`** (Number): The Google Ads customer ID.
*   **`campaigns`** (Array): An array of campaign objects.
    *   **`campaignId`** (Number): The ID of the Google Ads campaign.
    *   **`instruction`** (String): The natural language instruction for the agent to follow (e.g., "If the pollen count is high, pause the campaign.").
*   **`locations`** (Array): An array of location objects used for targeting. Each object contains details like city, state, latitude, and longitude.

**Collection: `SA360Config`**

Each document in this collection represents a SA360 customer account. The document ID should be the `customer_id`.

**Document Schema:**

*   **`customerId`** (Number): The SA360 customer ID.
*   **`SheetId`** (String): The Google Sheet ID.
*   **`SheetName`** (String): The Google Sheet name.
*   **`campaigns`** (Array): An array of campaign objects.
    *   **`campaignId`** (Number): The ID of the Google Ads campaign.
    *   **`instruction`** (String): The natural language instruction for the agent to follow (e.g., "If the pollen count is high, pause the campaign.").

**Collection: `CustomerInstructions`**

Each document in this collection represents the workflow instructions for a specific customer. The document ID should be the `customer_id`.

**Document Schema:**

*   **`instruction`** (String): A detailed natural language description of the optimization workflow the agent should execute for this customer. This includes steps for fetching data, evaluating campaigns, and logging decisions. Use this to provide guardrails for the agent.

### API Specifications

The solution leverages external APIs registered in Google Cloud API Hub to gather real-time data for decision-making. The following APIs are included by default:

**Note:** The OpenAPI specification files provided in this solution are samples. You should customize them or add new ones based on the specific functionalities you want to expose to the agentic framework.

**Google Pollen API**

*   **Description:** Provides pollen forecast data for a specified location.
*   **Endpoint:** `/v1/forecast:lookup`
*   **Key Parameters:**
    *   `location.latitude`
    *   `location.longitude`
    *   `days`
*   **Usage:** The Marketing Agent uses this API to fetch pollen count data, which can be used as a demand signal for products like allergy medication.

**Google Air Quality API**

*   **Description:** Provides air quality forecast data for a specified location.
*   **Endpoint:** `/v1/forecast:lookup`
*   **Key Parameters:**
    *   `location.latitude`
    *   `location.longitude`
    *   `dateTime`
    *   `extraComputations` (e.g., `HEALTH_RECOMMENDATIONS`)
*   **Usage:** The Marketing Agent uses air quality data (AQI, pollutants, health recommendations) to inform campaigns for products like air purifiers or masks.

**Google Weather API**

*   **Description:** Provides daily weather forecasts, including temperature, precipitation, and wind conditions.
*   **Endpoint:** `/v1/forecast/days:lookup`
*   **Key Parameters:**
    *   `location.latitude`
    *   `location.longitude`
    *   `days`
*   **Usage:** The Marketing Agent uses weather data to inform campaign decisions for weather-sensitive products (e.g., activating campaigns for raincoats if rain is forecasted).

### SA360 Integration (via Bulk Sheets)

For managing Search Ads 360 campaigns, this solution uses a Google Sheet-based bulk upload workflow. This allows for a transparent and auditable record of all automated changes.

**Workflow Overview:**

1.  **User Creates a Google Sheet:** You, the user, will create and maintain a Google Sheet that lists all the SA360 campaigns to be managed by the Agentic DSTA solution.
2.  **Google Sheet template:** The Google Sheet used for bulk upload should contain a set of columns and can be downloaded from SA360 web console by folllowing these steps:
    *   Login to your SA360 account
    *   Navigate to Bulk Actions
    *   Inside Bulk Actions, go to Uploads
    *   Click on + icon (Upload file button)
    *   Click on Download button (right next to Download template (Optional) text)
3.  **Additional Column:** Add an additional column named `Associated Campaign ID` to the Google sheet for Negative targeting (removing) of locations.
4.  **Update Firestore config:** Add `SheetId` and `SheetName` to the firestore collection `SA360Config` for the Google Sheet with customer id as the document id.
5.  **Share the Sheet:** You MUST share the Google Sheet with the Cloud Run service account: `[resource_prefix]-runner@[project_id].iam.gserviceaccount.com` (e.g., `dsta-runner@my-project-id.iam.gserviceaccount.com`) giving it at least **Editor** permissions. This allows the application to read and write to the sheet.
5.  **Data sync validation:** As a prerequisite, an automated process validates the sheets data and compares it with the latest data from SA360 before making any updates in the Sheet. Following columns are validated in the process:
    *   Campaign ID
    *   Campaign Name
    *   Campaign Status
    *   Campaign Type
    *   Budget
    *   Bid Strategy Type
    *   End Date
6.  **Agent Updates the Sheet:** When the Marketing Agent decides to change the status, budget, geo-targeting of a campaign (e.g., pause it due to low demand), it will update the `Status`, `Budget`, `Location` columns respectively in your Google Sheet for the corresponding campaign.
7.  **Agent Inserts in Sheet:** For Negative geo-targeting, agent will insert a new record in the Sheet with: 
    *   `Row Type`: excluded location name,
    *   `Action`: "deactivate",
    *   `Customer ID`: Customer ID,
    *   `Campaign`: Name of Campaign,
    *   `Location`: location to be removed,
    *   `EU political ads`: EU political ads flag (True/False),
    *   `Associated Campaign ID`: Campaign ID,
    The user should remove all negative geo-targeting records manually from the sheet to maintain clarity in campaign data.
7.  **User Schedules Upload:** You are responsible for taking the updated sheet and uploading it into the Search Ads 360 UI at a regular interval. This can be done manually or by setting up a scheduled upload within the SA360 platform (Bulk Actions > Uploads > Schedules).

**Sheet Format:**

The Google Sheet must contain at least the following columns:

| Column Name | Description                                     | Example         |
|-------------|-------------------------------------------------|-----------------|
| `Campaign`  | The exact name of the SA360 campaign.           | `"Summer Sale"` |
| `Status`    | The status of the campaign (`Active` or `Paused`). | `"Active"`      |

The agent will find the campaign by its ID and update the `Status`, `Budget`, and `Location` columns based on its decision logic and campaign instruction.

## Extending the Solution with More APIs

A key feature of this solution is its ability to dynamically load new APIs at runtime without requiring any code changes or redeployments. If you have an API with an OpenAPI specification, you can make it available to the agent by following these steps.

### Step 1: Register Your API in API Hub

Follow the Google Cloud documentation to [register an API](https://cloud.google.com/api-hub/docs/manage-apis-register) in your project's API Hub instance. You will need to provide the OpenAPI spec for your API.

### Step 2: Configure API Key Authentication (If Required)

When the agent discovers your new API, it automatically attempts to find an API key for it by checking for secrets (environment variables) in a specific order of preference:

1.  A specific key for your API: `[YOUR_API_DISPLAY_NAME]_API_KEY`
2.  A generic, fallback key: `GOOGLE_API_KEY`

This gives you two flexible options for managing credentials.

#### Option A: Use the Existing `GOOGLE_API_KEY`

If your new API can use the same generic `GOOGLE_API_KEY` that the Pollen, Air Quality and Weather APIs use, no infrastructure changes are needed.

1.  **Register your API in API Hub.**
2.  **Restart your Cloud Run service.** You can do this from the Google Cloud Console. A restart is sufficient for the agent to re-initialize and discover the new API.

The agent will discover the API, fail to find a specific key, and automatically fall back to using the `GOOGLE_API_KEY` that is already available to it.

#### Option B: Provide a New, Dedicated API Key

If your new API requires its own unique key for security or tracking purposes, you can securely provision it with a quick infrastructure update.

1.  **Register your API in API Hub.**
2.  **Determine the Secret Name:** The agent will look for a secret matching your API's display name. For example, if the display name is "My Stock Service", the required secret name is `MY_STOCK_SERVICE_API_KEY`.
3.  **Add the Secret Name to `config.yaml`:**
    Open your `infra/config.yaml` file and add this secret name to the `additional_secrets` list.
    ```yaml
    additional_secrets: ["MY_STOCK_SERVICE_API_KEY"]
    ```
4.  **Run the Deployment Script to Provision the Secret:**
    Execute the `deploy.sh` script again. This step **does not rebuild or redeploy your application code**. It performs a quick infrastructure update to:
    *   Prompt you for the new secret's value.
    *   Store it securely in Secret Manager.
    *   Grant your Cloud Run service permission to access it.
    *   Update the Cloud Run service to mount the secret.

    ```bash
    bash deploy.sh
    ```
    Because you added a new secret name, the script will interactively guide you through the one-time setup for that secret.

Once the script completes, the agent will have immediate access to the new key and will dynamically load the new API on its next run.

## Logging

The solution uses a centralized logging system configured in `agentic_dsta/core/logging_config.py`. Logs are output as JSON objects to standard output, making them suitable for ingestion and analysis in Google Cloud Logging.

### Log Format

Each log entry is a JSON object with the following keys:

-   `timestamp`: ISO 8601 format UTC timestamp.
-   `severity`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
-   `message`: The log message.
-   `logger_name`: Name of the logger instance (e.g., `agentic_dsta.tools.google_ads.google_ads_getter`).
-   `code_function`: Function name where the log was emitted.
-   `code_line`: Line number where the log was emitted.
-   `exception`: Stack trace if an exception occurred.
-   Additional context fields passed via `extra` in logger calls (e.g., `customer_id`, `campaign_id`).

### Configuring Log Level

The log level can be configured using the `LOG_LEVEL` environment variable. Default is `INFO`.
Example: `LOG_LEVEL=DEBUG`

### Viewing Logs in Cloud Logging

When deployed on Cloud Run, these JSON logs will be automatically parsed by Cloud Logging. You can view and query them in the Logs Explorer. The JSON fields will be under the `jsonPayload` field.

Example Query:
```
resource.type="cloud_run_revision"
resource.labels.service_name="[YOUR_SERVICE_NAME]"
jsonPayload.severity="ERROR"
jsonPayload.customer_id="1234567890"
```

### Error Handling

-   Errors within the agent tools, especially those involving API calls like the Google Ads API, are generally caught.
-   Detailed error information is logged in the JSON format mentioned above, typically with `severity: ERROR`.
-   For Google Ads API errors, the `exception` field in the log will often contain the stack trace, and the log message will include specific error codes and messages from the API (e.g., `error.error_code.name`, `error.message`).
-   The tools return a dictionary. On failure, this dictionary usually contains an `error` key with a descriptive message and sometimes a `details` key with more specific error information (like the list of errors from a `GoogleAdsException`).
-   Internal Refactoring: The logic for applying bidding strategy details has been centralized into a helper function `_apply_bidding_strategy_details` within `google_ads_updater.py` for better maintainability.

## Usage

This deployment provides two primary ways to interact with the agentic framework:

### Interactive Web Interface

Once the deployment is complete, you can interact with all the individual agents (Google Ads, SA360, Firestore, API Hub) through a web interface provided by the Agent Development Kit (ADK). This is useful for testing, debugging, and performing one-off tasks.

The URL for your Cloud Run service will be printed at the end of the deployment script. Navigate to this URL in your browser to access the ADK web server.

> [!NOTE]
> The Agent Development Kit (ADK) is an evolving framework. The Web UI's availability, features, and appearance are subject to change and are not guaranteed to remain consistent in future versions. As noted in the [official ADK documentation](https://google.github.io/adk-docs/get-started/streaming/quickstart-streaming/#try-the-agent-with-adk-web:~:text=Caution%3A%20ADK%20Web,debugging%20purposes%20only), the ADK Web interface is intended for testing and debugging purposes only.

### Decision Agent Workflow and Configuration

The Decision Agent is the core automated component of the DSTA solution. It's triggered by Cloud Scheduler to periodically evaluate and manage campaigns based on pre-configured instructions and real-time signals.

**Workflow:**

#### Automated Execution via Cloud Scheduler

The core of the solution is the automated execution of the **Decision Agent**, which acts as the primary decision-maker.

A Google Cloud Scheduler job is deployed by Terraform to trigger this agent at a regular frequency (defined by the `googleads_scheduler_schedule` and `sa360_scheduler_schedule` parameters in your `config.yaml`). On each run, the scheduler sends a request to the agent with a preset instruction, such as: *"Run daily check based on current demand signals and business rules."*

The Decision Agent then follows its instructions, utilizing the various toolsets described in the [Solution Overview](#solution-overview) to gather data, retrieve rules, make decisions, and execute changes.

This automated workflow allows the solution to manage your campaigns hands-free based on the rules and data sources you have configured.

The agent, when triggered for a specific `customer_id` and `usecase` (e.g., "GoogleAds" or "SA360"):

1.  **Fetches Global Instructions:** Retrieves the overarching strategy and rules for the customer from the `CustomerInstructions` collection in Firestore, using the `customer_id` as the document ID.
2.  **Fetches Campaign Config:** Loads the campaign-specific details from either the `GoogleAdsConfig` or `SA360Config` collection in Firestore, again using the `customer_id`. This document contains a list of campaigns to be managed.
3.  **Iterates Through Campaigns:** Loops through each campaign defined in the configuration.
4.  **Creates Isolated Agent Instance:** For each campaign, a new, ephemeral agent instance is created. This instance is provided with a combined instruction set:
    *   The global instructions from `CustomerInstructions`.
    *   The specific instructions for the current `campaignId` from the `GoogleAdsConfig` or `SA360Config`.
5.  **Analyzes and Acts:** The campaign-specific agent instance uses the available toolsets (as detailed in the [Solution Overview](#solution-overview)) to interact with external APIs, Firestore, Google Ads, and SA360.
6.  **Logs Outcomes:** The agent's decisions and actions are logged.

**Required Firestore Configuration:**

For the Decision Agent to function correctly, you must configure the `CustomerInstructions`, `GoogleAdsConfig`, and `SA360Config` collections in your Firestore database as described in the [Firestore Data Model](#firestore-data-model) section.

**Example Instruction:**

An instruction in Firestore might look like: "If the Pollen API for the campaign's target locations shows a 'high' pollen count for 'grass' in the next 2 days, increase the bid for this campaign by 15%. If the weather forecast predicts rain, pause the campaign."

The clarity and specificity of the natural language instructions provided in Firestore are crucial for the agent to make the desired automated decisions.

## Security Best Practices

*   **IAM & Least Privilege:** The Terraform scripts create dedicated service accounts with the minimum necessary permissions for each component.
*   **Secret Management:** All sensitive information is stored in Google Cloud Secret Manager and securely injected into the Cloud Run service as environment variables.
*   **Network Security:** By default, the Cloud Run service is deployed as private (`allow_unauthenticated: false`). Access should be managed through IAM or IAP for production environments.

### Created Service Accounts

The automated deployment script ensures the principle of least privilege by creating specific Service Accounts (SAs) for different lifecycle stages:

| Service Account Name | ID Pattern | Purpose |
| :--- | :--- | :--- |
| **Deployer SA** | `[prefix]-deployer` | **Deployment Authority:** Created by `deploy.sh`. Used temporarily to execute Terraform, build containers, and set up infrastructure. It requires broad permissions (admin) to provision resources. |
| **Runtime SA** | `[prefix]-runner` | **Application Identity:** Created by Terraform. Used by the Cloud Run application at runtime. It has restricted permissions, limited to accessing secrets, writing to Firestore, and invoking needed APIs. **This is the account you add to Google Ads.** |

*   `[prefix]` corresponds to the `resource_prefix` value defined in your `config.yaml`.
*   Note: The **Compute Engine default service account** is also temporarily granted `objectViewer` permission to fetch source code for Cloud Build.

## Troubleshooting

*   **Permissions Errors:** If the deployment fails with a permissions error, ensure the user or service account running the script has the required IAM roles listed in the **Prerequisites** section.
*   **API Not Enabled:** If you see errors related to a specific service, you may need to manually enable the corresponding API in the Google Cloud Console.

## Cost

This solution uses billable Google Cloud services. The primary cost drivers are:

*   **Cloud Run:** Billed based on CPU and memory consumption.
*   **Firestore:** Billed based on storage and read/write operations.
*   **Cloud Build & Artifact Registry:** Billed for build time and storage.

To estimate the cost, use the [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator).

## Destroying the Infrastructure

To tear down all the resources created by this deployment, it is recommended to use the `destroy.sh` script from the `infra` directory. This script handles the necessary authentication setup and ensures a cleaner teardown process:

```bash
cd infra
bash destroy.sh
```

The script will prompt for confirmation before destroying the resources. This will remove all the Google Cloud resources managed by Terraform in this solution.

**Note on Firestore:**
The default behavior for the Firestore database resources is to **not** be deleted when you run `destroy.sh` (deletion policy is `ABANDON`). This prevents accidental data loss. If you wish to delete the database, you must do so manually in the Google Cloud Console.

**Persisted Resources:**
The following resources are **NOT** deleted by `destroy.sh` and may require manual cleanup if you wish to completely wipe the project:
*   **Google Cloud APIs:** APIs enabled during deployment (e.g., Cloud Run API, Vertex AI API) remain enabled.
*   **Deployer Service Account:** The service account used to run the deployment script (`[prefix]-deployer`) is created by the shell script and is not managed by Terraform.
*   **Terraform State Bucket:** The Google Cloud Storage bucket containing the Terraform state file is preserved to maintain state history.
*   **Artifact Registry:** The repository itself is not deleted, as Terraform only reads it as a data source.
*   **API Hub Registrations:** APIs registered in API Hub are not automatically unregistered.


## Solution Artifacts

The following table lists the key configuration samples and API specifications included in the repository:

| Category | File Path | Description |
| :--- | :--- | :--- |
| **Configuration** | [`infra/config/app/config.yaml`](infra/config/app/config.yaml) | Main configuration file for deployment. |
| **Samples** | [`infra/config/samples/firestore_config.json`](infra/config/samples/firestore_config.json) | Example Firestore configuration for campaigns and rules. |
| **API Specs** | [`infra/config/specs/`](infra/config/specs/) | OpenAPI specifications for external tools (Weather, Pollen, Air Quality). |

### About Spec Files

The files in the `infra/config/specs/` directory are **OpenAPI 3.0 specification files** (formerly known as Swagger). These YAML files define the interface for the external APIs that the agent can interacts with. They describe:

*   **Endpoints:** The available URL paths (e.g., `/v1/forecast:lookup`).
*   **Operations:** The HTTP methods supported (GET, POST, etc.).
*   **Parameters:** The input data required for each operation.
*   **Schemas:** The structure of the request and response bodies.

These specifications are critical because the **API Hub Toolset** uses them to "teach" the agent how to construct valid API requests.

### Enhancing Specifications

You can modify these files or add new ones to expose more functionality to the agent. The provided specs are often subsets of the full API capabilities, tailored for the agent's specific needs.

To enhance a specification:

1.  **Consult the Official API Documentation:** Refer to the official documentation for the API (e.g., [Google Maps Platform documentation](https://developers.google.com/maps/documentation)) to identify other endpoints or parameters you want to add.
2.  **Edit the YAML File:** Update the corresponding `.yaml` file in `infra/config/specs/` following the [OpenAPI 3.0 Specification](https://spec.openapis.org/oas/v3.0.3) standard.
    *   *Example:* If you want the Weather API to return hourly data instead of just daily, you might add the `hourly` parameter to the `parameters` list in `weather-api-openapi.yaml`.
3.  **Redeploy:** After modifying the spec file, you must re-register the API version in API Hub. If you are using the automated `deploy.sh` script, simply re-running it will update the API Hub registry with your changes.