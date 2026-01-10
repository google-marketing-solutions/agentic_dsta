# Implementation Guide: Agentic Dynamic Signal Target Ads

**Disclaimer:** This is not an officially supported Google product.

## 1. Introduction

The Agentic Dynamic Signal Target Ads solution is a powerful, automated marketing framework designed to help marketers forecast and activate advertising campaigns based on real-time demand signals. By integrating data from a variety of sources, including Google Ads, SA360, and third-party APIs, this solution provides an intelligent, automated approach to campaign management.

This guide provides all the necessary information for deploying, configuring, and managing the Agentic DSTA infrastructure on Google Cloud Platform.

## 2. Solution Overview

The core of this solution is a multi-agent framework built with the Application Development Kit (ADK). This framework includes several specialized toolsets that are used by the agents to make intelligent marketing decisions:

*   **API Hub Toolset:** This toolset can dynamically discover and call any API registered in your Google Cloud API Hub instance. Its tools allow agents to fetch data from external sources, which is then used for decision-making.
*   **Firestore Toolset:** This toolset acts as the memory and configuration hub. It has tools to read, write, query, and delete documents in Firestore. It is used to store and retrieve business rules, campaign instructions, and location data.
*   **Google Ads Toolset:** A specialized toolset to directly manage your Google Ads campaigns. Its capabilities include:
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
*   **SA360 Toolset:** This toolset is designed for Search Ads 360 management. It uses a Google Sheet as an intermediary for bulk updates. Its tools can modify this sheet to change campaign statuses, which are then uploaded by the user to SA360.
    *   **Fetching Campaign Details:** Retrieve a full overview of a campaign's settings and current status from SA360.
    *   **Updating Campaign Status:** Programmatically pause or enable campaigns in Google Sheet.
    *   **Modifying Campaign Budgets:** Adjust the budget for any campaign in Google Sheet.
    *   **Updating Geo-Targeting:** Add a geolocation to the list of locations of the campaign in Google Sheet.
    *   **Negative Geo-Targeting:** Remove a geolocation from the list of locations of the campaign in Google Sheet.
    *   **Fetching Campaign Details - Google Sheet:** Retrieve a full overview of a campaign's settings and current status from user managed Google Sheet.
*   **Decision Agent:** This is the orchestrator agent responsible for automated execution. It takes a high-level goal (e.g., from the Cloud Scheduler job), uses the toolsets to gather data, and then delegates campaign management tasks based on the retrieved information and business rules.
*   **Marketing Agent:** This is the interactive agent that is used to perform complex tasks and act on campaigns in a conversational manner. It is intended for interactive use through the ADK web UI.

The entire solution is deployed as a containerized application on Google Cloud Run and is managed through Infrastructure as Code (IaC) with Terraform.

## 3. Architecture

The following diagram illustrates the architecture of the Agentic Dynamic Signal Target Ads solution:

```
[User/Scheduler] -> [Cloud Run (FastAPI)] -> [Marketing Agent / Decision Agent]
                                                       |
            +---------------------+--------------------+---------------------+
            |                     |                    |                     |
    [Google Ads Toolset]    [SA360 Toolset]    [Firestore Toolset]    [API Hub Toolset]
            |                     |                    |                     |
      [Google Ads API]      [Google Sheet]     [Firestore DB]      [External APIs]
                                  | (manual upload)                        (e.g., Weather, Pollen)
                                  v
                               [SA360]
```

**Workflow Details:**

*   **Google Ads:** The `Google Ads Toolset` allows the agent to interact directly with the Google Ads API to manage campaigns.
*   **SA360:** The `SA360 Toolset` allows the agent to interact with SA360 Reporting API to get campaign details & update a Google Sheet with campaign changes. The user is responsible for uploading this sheet to SA360.


## 4. Key Components

*   **Google Cloud Run:** Hosts the containerized FastAPI application that serves the agent endpoints.
*   **Google Cloud Firestore:** Stores business rules, campaign settings, and other configuration data.
*   **Google Cloud Secret Manager:** Securely stores all API keys, tokens, and other sensitive credentials.
*   **Google Cloud API Hub:** Acts as a central registry for all external APIs used by the solution.
*   **Google Cloud Build & Artifact Registry:** Automates the process of building and storing the application's container image.
*   **Terraform:** Manages the entire Google Cloud infrastructure as code, enabling repeatable, one-click deployments.

## 5. Prerequisites

### 5.1. Google Cloud

*   A Google Cloud project with billing enabled.
*   The **gcloud CLI** installed and authenticated:
    ```bash
    gcloud auth login
    gcloud config set project [YOUR_PROJECT_ID]
    ```

*   The user or principal running the `deploy.sh` script for the *first time* needs sufficient permissions to create and configure service accounts, IAM policies, and other project resources. The `roles/owner` role is the simplest way to ensure this. Alternatively, a combination of roles like `roles/editor`, `roles/resourcemanager.projectIamAdmin`, `roles/iam.serviceAccountAdmin`, `roles/serviceusage.serviceUsageAdmin`, etc., would be required.
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

### 5.1.1 API Hub Setup

This solution relies on Google Cloud API Hub. Please perform the following one-time setup in your Google Cloud Project:

1.  **Enable API Hub API:**
    ```bash
    gcloud services enable apihub.googleapis.com --project [YOUR_PROJECT_ID]
    ```

2.  **Register Host Project:** This links API Hub to your project. This only needs to be done once per project and region.
    ```bash
    gcloud api-hub host-project-registrations create [YOUR_PROJECT_ID] --location=[YOUR_REGION] --project=[YOUR_PROJECT_ID]
    ```
    *Replace `[YOUR_PROJECT_ID]` and `[YOUR_REGION]` accordingly.*

3.  **Create API Hub Instance:** Currently, only an instance named `default` is supported by the agent.
    ```bash
    gcloud api-hub api-hub-instances create default --location=[YOUR_REGION] --project=[YOUR_PROJECT_ID]
    ```
    *This command may not yet be available in gcloud. You may need to create the instance via the Cloud Console or API. Navigate to the API Hub section in the Google Cloud Console and create an instance named `default` in your chosen region.*

### 5.2. Local Environment

*   **Terraform:** Version 1.14.2 or later.
*   **Python:** Version 3.10 or later.
*   **Git:** For cloning the repository.

## 6. Generating Required Credentials

This solution requires several credentials to access Google Cloud and Google Ads APIs. Follow these steps to generate and collect them before proceeding with the deployment.

### 6.1. Google API Key (for Pollen & Weather APIs)

1.  Navigate to the [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials) page in the Google Cloud Console.
2.  Click **+ CREATE CREDENTIALS** and select **API key**.
3.  The API key will be created. Copy it and save it for your `config.yaml` file.
4.  **Important:** It is highly recommended to restrict the API key to only the services it will be used for (Pollen API and Weather API). Click on the newly created key, and under **API restrictions**, select **Restrict key** and add the **Pollen API** and **Weather API** to the list.

### 6.2. Google Ads API Credentials (OAuth2 User Flow)

Follow the official Google Ads API documentation to obtain your developer token, OAuth2 client ID, client secret, and refresh token.

1.  **Developer Token:**
    *   Apply for a developer token through your Google Ads manager account. Follow the instructions at [Get a Developer Token](https://developers.google.com/google-ads/api/docs/first-call/dev-token).

2.  **Google API Key (for Weather/Pollen APIs):**
    *   This solution uses public Google APIs (Weather, Pollen) which require a standard Google API Key.
    *   Go to the [Credentials page](https://console.cloud.google.com/apis/credentials) in your Google Cloud Console.
    *   Click **Create Credentials** > **API key**.
    *   Copy the key and save it. You will need to provide this as a secret named `GOOGLE_API_KEY` during deployment.

3.  **OAuth2 Client ID and Client Secret:**
    *   Configure an OAuth2 consent screen and create credentials for a **Desktop app**. This will provide you with a client ID and client secret. Follow the guide at [Create a Client ID and Client Secret](https://developers.google.com/google-ads/api/docs/oauth/cloud-project#create_a_client_id_and_client_secret).
    *   **Important:** On your OAuth consent screen configuration, you must add the Google Ads API scope: `https://www.googleapis.com/auth/adwords`.
    *   When creating your OAuth2 Client ID, make sure to add `http://127.0.0.1:8080` to the list of **Authorized redirect URIs**. The `generate_user_credentials.py` script uses this URI to capture the authorization response. Failure to add this will result in a `redirect_uri_mismatch` error.

3.  **Generate Refresh Token:**
    *   To generate the refresh token, you will use a helper script. This script automates the OAuth2 flow to get the necessary refresh token.
    *   **Prerequisites:**
        *   Ensure you have Python installed.
        *   Install the Google Ads Python library:
            ```bash
            pip install google-ads
            ```
    *   **Download the script:** Provide a link to the script or include it in your repository. For example, if you've adapted `generate_user_credentials.py`:
        *   You can find the example script here: [`generate_user_credentials.py`](https://github.com/googleads/google-ads-python/blob/main/examples/authentication/generate_user_credentials.py)
    *   **Run the script:** Execute the script, providing your Client ID and Client Secret obtained in the previous step:
        ```bash
        python generate_user_credentials.py --client_id=YOUR_CLIENT_ID --client_secret=YOUR_CLIENT_SECRET
        ```
    *   **Authorization:** The script will output a URL. Copy this URL and open it in your web browser.
    *   Log in with the Google account that has access to the Google Ads account you want to manage.
    *   Grant the requested permissions (it should include the `adwords` scope).
    *   After granting permissions, you'll be redirected to a page on `127.0.0.1:8080` (or an error page if the redirect URI wasn't set up correctly). The script will capture the authorization code from the redirect.
    *   **Result:** The script will then exchange the authorization code for a refresh token and an access token, and print the refresh token to the console. It might also save the credentials to a `google-ads.yaml` file in your home directory.
    *   **Copy the Refresh Token:** Securely copy the displayed refresh token. You will need this for your `config.yaml`.

6.  **Review Collected Credentials:**
    *   Ensure you have the following list ready:
        *   Google Ads Developer Token
        *   OAuth2 Client ID
        *   OAuth2 Client Secret
        *   OAuth2 Refresh Token
        *   Google API Key

Once you have collected all these credentials, have them ready. You will be prompted to enter them securely during the first run of the deployment script. You do **not** need to put them in any file.

### 6.3. Google Ads API Credentials (Service Account Flow) - TBD

_This section is a placeholder for future implementation._

For production and automated environments, it is recommended to use a service account for authentication instead of a user-based OAuth2 flow. This section will provide instructions on how to:

*   **TBD:** Create a service account with the necessary permissions.
*   **TBD:** Configure domain-wide delegation for the service account.
*   **TBD:** Generate a private key for the service account.
*   **TBD:** Update the configuration to use the service account credentials.

## 7. Installation and Deployment

The deployment process is fully automated with a one-click script.

### Step 1: Clone the Repository

Clone this repository to your local machine:

```bash
git clone [REPOSITORY_URL]
cd gta-solutions/infra
```

### Step 2: Configure Your Deployment

All deployment parameters are managed in the `config.yaml` file.

    Use the provided example file as a template:
    ```bash
    cp config/app/config.yaml.example config/app/config.yaml
    ```

2.  **Edit the configuration:**
    Open `config/app/config.yaml`.
    *   Fill in the non-sensitive values like `project_id`.
    *   **Advanced Secrets:** If you need to inject the `GOOGLE_API_KEY`, uncomment the `additional_secrets` section:
        ```yaml
        additional_secrets:
          - "GOOGLE_API_KEY"
        ```
    *   Do **not** put the actual secret values in this file. You will be prompted for them during deployment.

### Step 3: Run the Deployment Script

Execute the `deploy.sh` script from the `infra` directory:

```bash
bash deploy.sh
```

**First-Time Setup:** The first time you run this script, it will detect that your secret credentials are not yet stored. It will securely prompt you to enter each required credential one by one. These are the credentials you collected in the "Generating Required Credentials" step.

This script will:
1.  Check for the required secrets in Google Secret Manager and create them if they don't exist (this is the interactive part).
2.  Build the application's Docker image.
3.  Push the image to Google Artifact Registry.
4.  Generate a `terraform.tfvars` file from your `config.yaml`.
5.  Initialize and apply the Terraform configuration to deploy all the necessary infrastructure.

On subsequent runs, the script will see that the secrets already exist and will skip straight to the deployment, making it fully automatable.

The deployment will take several minutes to complete.

## 8. Configuration Parameters

The following table describes each parameter in the `config.yaml` file:

| Parameter                      | Description                                                                                             | Example                                       |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `project_id`                   | **Required.** Your Google Cloud Project ID.                                                              | `"[YOUR_PROJECT_ID]"`                        |
| `region`                       | The primary Google Cloud region for deploying resources.                                                | `"us-central1"`                               |
| `service_name`                 | The name for your Cloud Run service.                                                                    | `"cloud-run-dsta-tf"`                         |
| `allow_unauthenticated`        | If `true`, the Cloud Run service will be publicly accessible. Set to `false` for production.           | `false`                                       |
| `firestore_database_name`      | The name for your Firestore database instance.                                                          | `"dsta-agentic-firestore-tf"`                 |
| `firestore_location_id`        | The location for your Firestore database (e.g., `nam5` for North America).                              | `"nam5"`                                      |
| `firestore_location_id`        | The location for your Firestore database (e.g., `nam5` for North America).                              | `"nam5"`                                      |
| `firestore_database_type`      | The type of Firestore database to create (`FIRESTORE_NATIVE` or `DATASTORE_MODE`).                        | `"FIRESTORE_NATIVE"`                          |
| `additional_secrets`           | List of extra secrets to manage (e.g., `GOOGLE_API_KEY`).                                               | `["GOOGLE_API_KEY"]`                          |
| `artifact_repository_id`       | The name for your Artifact Registry repository.                                                         | `"agentic-dsta-repo"`                         |
| `apihub_instance_id`           | The ID for your API Hub instance.                                                                       | `"default-instance"`                          |
| `scheduler_cron`               | The cron schedule for triggering the marketing automation agent.                                        | `"0 0 * * *"`                                 |

## 9. Data Models and APIs

### 9.1. Firestore Data Model

The solution uses Google Cloud Firestore to store business rules and campaign configurations. The primary collections are `GoogleAdsConfig` and `SA360Config`.

**Collection: `GoogleAdsConfig`**

Each document in this collection represents a Google Ads customer account. The document ID should be the `customer_id`.

**Document Schema:**

*   **`customerId`** (Number): The Google Ads customer ID.
*   **`campaigns`** (Map): A map of campaign configurations, where each key is a `campaignId`.
    *   **`campaignId`** (Number): The ID of the Google Ads campaign.
    *   **`instruction`** (String): The natural language instruction for the agent to follow (e.g., "If the pollen count is high, pause the campaign.").
*   **`locations`** (Array): An array of location objects used for targeting. Each object contains details like city, state, latitude, and longitude.

**Collection: `SA360Config`**

Each document in this collection represents a SA360 customer account. The document ID should be the `customer_id`.

**Document Schema:**

*   **`customerId`** (Number): The SA360 customer ID.
*   **`SheetId`** (String): The Google Sheet ID.
*   **`SheetName`** (String): The Google Sheet name.
*   **`campaigns`** (Map): A map of campaign configurations, where each key is a `campaignId`.
    *   **`campaignId`** (Number): The ID of the Google Ads campaign.
    *   **`instruction`** (String): The natural language instruction for the agent to follow (e.g., "If the pollen count is high, pause the campaign.").

### 9.2. API Specifications

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

**Google Weather API**

*   **Description:** Provides daily weather forecasts, including temperature, precipitation, and wind conditions.
*   **Endpoint:** `/v1/forecast/days:lookup`
*   **Key Parameters:**
    *   `location.latitude`
    *   `location.longitude`
    *   `days`
*   **Usage:** The Marketing Agent uses weather data to inform campaign decisions for weather-sensitive products (e.g., activating campaigns for raincoats if rain is forecasted).

### 9.3. SA360 Integration (via Bulk Sheets)

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
5.  **Agent Updates the Sheet:** When the Marketing Agent decides to change the status, budget, geo-targeting of a campaign (e.g., pause it due to low demand), it will update the `Status`, `Budget`, `Location` columns respectively in your Google Sheet for the corresponding campaign.
6.  **Agent Inserts in Sheet:** For Negative geo-targeting, agent will insert a new record in the Sheet with: 
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

## 10. Extending the Solution with More APIs

A key feature of this solution is its ability to dynamically load new APIs at runtime without requiring any code changes or redeployments. If you have an API with an OpenAPI specification, you can make it available to the agent by following these steps.

### Step 1: Register Your API in API Hub

Follow the Google Cloud documentation to [register an API](https://cloud.google.com/api-hub/docs/manage-apis-register) in your project's API Hub instance. You will need to provide the OpenAPI spec for your API.

### Step 2: Configure API Key Authentication (If Required)

When the agent discovers your new API, it automatically attempts to find an API key for it by checking for secrets (environment variables) in a specific order of preference:

1.  A specific key for your API: `[YOUR_API_DISPLAY_NAME]_API_KEY`
2.  A generic, fallback key: `GOOGLE_API_KEY`

This gives you two flexible options for managing credentials.

#### Option A: Use the Existing `GOOGLE_API_KEY`

If your new API can use the same generic `GOOGLE_API_KEY` that the Pollen and Weather APIs use, no infrastructure changes are needed.

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
    additional_secrets:
      - MY_STOCK_SERVICE_API_KEY
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

## 11. Logging

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

## 12. Usage

This deployment provides two primary ways to interact with the agentic framework:

### 10.1. Interactive Web Interface

Once the deployment is complete, you can interact with all the individual agents (Google Ads, SA360, Firestore, API Hub) through a web interface provided by the Application Development Kit (ADK). This is useful for testing, debugging, and performing one-off tasks.

The URL for your Cloud Run service will be printed at the end of the deployment script. Navigate to this URL in your browser to access the ADK web server.

> [!NOTE]
> The Application Development Kit (ADK) is an evolving framework. The Web UI's availability, features, and appearance are subject to change and are not guaranteed to remain consistent in future versions. As noted in the [official ADK documentation](https://google.github.io/adk-docs/get-started/streaming/quickstart-streaming/#try-the-agent-with-adk-web:~:text=Caution%3A%20ADK%20Web,debugging%20purposes%20only), the ADK Web interface is intended for testing and debugging purposes only.

### 10.2. Automated Execution via Cloud Scheduler

The core of the solution is the automated execution of the **Decision Agent**, which acts as the primary decision-maker.

A Google Cloud Scheduler job is deployed by Terraform to trigger this agent at a regular frequency (defined by the `scheduler_cron` parameter in your `config.yaml`). On each run, the scheduler sends a request to the agent with a preset instruction, such as: *"Run daily check based on current demand signals and business rules."*

The Decision Agent then follows its instructions to:
1.  Fetch real-time data using the **API Hub Toolset**.
2.  Retrieve business rules from the **Firestore Toolset**.
3.  Make a decision on what changes to make to the campaigns.
4.  Delegate the execution of these changes to the **Google Ads Toolset** or **SA360 Toolset**.

This automated workflow allows the solution to manage your campaigns hands-free based on the rules and data sources you have configured.

## 11. Security Best Practices

*   **IAM & Least Privilege:** The Terraform scripts create dedicated service accounts with the minimum necessary permissions for each component.
*   **Secret Management:** All sensitive information is stored in Google Cloud Secret Manager and securely injected into the Cloud Run service as environment variables.
*   **Network Security:** By default, the Cloud Run service is deployed as private (`allow_unauthenticated: false`). Access should be managed through IAM or IAP for production environments.

## 12. Troubleshooting

*   **Permissions Errors:** If the deployment fails with a permissions error, ensure the user or service account running the script has the required IAM roles listed in the **Prerequisites** section.
*   **API Not Enabled:** If you see errors related to a specific service, you may need to manually enable the corresponding API in the Google Cloud Console.

## 13. Cost

This solution uses billable Google Cloud services. The primary cost drivers are:

*   **Cloud Run:** Billed based on CPU and memory consumption.
*   **Firestore:** Billed based on storage and read/write operations.
*   **Cloud Build & Artifact Registry:** Billed for build time and storage.

To estimate the cost, use the [Google Cloud Pricing Calculator](https://cloud.google.com/products/calculator).

## 14. Destroying the Infrastructure

To tear down all the resources created by this deployment, it is recommended to use the `destroy.sh` script from the `infra` directory. This script handles the necessary authentication setup and ensures a cleaner teardown process:

```bash
cd infra
bash destroy.sh
```

The script will prompt for confirmation before destroying the resources. This will remove all the Google Cloud resources managed by Terraform in this solution.
