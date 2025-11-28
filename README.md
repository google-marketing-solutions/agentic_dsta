# Agentic Demand Signal & Trend Activation (DSTA)

This is not an officially supported Google product.

## Overview

The Agentic DSTA project is a solution designed to help marketers forecast and
activate advertising campaigns based on real-time demand signals. It integrates
data from Google Search, Google Ads, SA360, Google Cloud Firestore, and
third-party APIs (via Google Cloud API Hub, e.g., Pollen and Weather APIs) to
provide intelligent, automated campaign management capabilities.

The project uses the Application Development Kit (ADK) to build and manage
conversational agents that can interact with these data sources and perform
actions like enabling or pausing advertising campaigns.

## Features

*   **Multi-Agent Framework:** Includes agents for:
    *   **API Hub:** Dynamically discovers and interacts with APIs registered in
        API Hub.
    *   **Firestore:** Reads from and writes to Google Cloud Firestore.
    *   **Google Ads:** Manages Google Ads campaigns (e.g., pause/enable).
    *   **SA360:** Manages Search Ads 360 campaigns (e.g., pause/enable).
    *   **Marketing:** A coordinator agent that uses other agents and data
        sources to make marketing decisions.
*   **Dynamic API Discovery:** The API Hub agent can load API specifications
    dynamically from API Hub, allowing it to use new APIs without
    redeployment.
*   **Demand Forecasting:** Combines signals like weather or pollen count with
    search trends to predict demand fluctuations.
*   **Automated Campaign Activation:** Automatically enables or pauses Google
    Ads / SA360 campaigns based on demand signals and business rules stored in
    Firestore.
*   **FastAPI Backend:** Exposes agent capabilities through a FastAPI interface.
*   **Cloud Run Deployment:** Designed for easy deployment to Google Cloud Run.

## Prerequisites

*   Python 3.12+
*   `pip` and `venv`
*   Git
*   Access to Google Cloud Platform, with a configured project and credentials.
*   Access to Google Ads and/or SA360 with appropriate API credentials.

## Installation and Local Development

This project contains two Python applications: a root application and a nested
application in `agentic_dsta/`. The main application for the agents is in
`agentic_dsta/`.

1.  **Clone the repository:**
    ```bash
    # Ensure you have run gcert if required
    git clone sso://gta-solutions/agentic_dsta
    cd agentic_dsta/agentic_dsta
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install --require-hashes -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Copy the example environment file and fill in your credentials:
    ```bash
    cp .env.example .env
    nano .env
    ```
    *Note: The `.env` file should NOT be committed to version control.*

5.  **Run the application locally:**
    ```bash
    export $(grep -v '^#' .env | xargs)
    python3 main.py
    ```
    The server will start on `http://0.0.0.0:8080`.

## Deployment

This application is designed to be deployed to Google Cloud Run. See
[agentic_dsta/README.md](agentic_dsta/README.md) for detailed deployment
instructions.

## Disclaimer

This is not an officially supported Google product. It is a proof-of-concept
demonstrating the capabilities of agentic systems for marketing activation.
