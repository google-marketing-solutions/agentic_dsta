## Test your agent locally

1.  **Run the FastAPI server locally with python:**

    1.  **Set up environment variables:** Create a `.env` file by copying the
        `.env.example` template:
        ```bash
        cp .env.example .env
        ```
        Then, open the `.env` file and replace the placeholder values with your
        actual credentials.

    2.  **Load environment variables:** After setting up your `.env` file, load the variables into your current shell session by running:

        ```bash
        export $(grep -v '^#' .env | xargs)
        ```

        This command reads the `.env` file, and the `export` command makes them available to any processes you run in that shell.

    3.  **Install dependencies**
        ```bash
        pip install -r requirements.txt
        ```

    3.  **Run the application:** Navigate to the directory containing `main.py`
        and run the script:

        ```bash
        python3 main.py
        ```

        This will start the FastAPI server, on `http://0.0.0.0:8080`.

## Deploy to Google Cloud Run

**Prerequisites: Enable required APIs**

Before deploying, ensure that you have enabled all the necessary Google Cloud APIs. You can do this by running the following command:

```bash
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  apihub.googleapis.com \
  aiplatform.googleapis.com \
  iap.googleapis.com
```

To deploy this application to Google Cloud Run, follow these steps:

**IAM Roles**

The necessary IAM roles for the Cloud Run service account are automatically applied by the Terraform deployment script. For a complete list of roles, refer to the `implementation_guide.md`.

1.  **Store secrets in Secret Manager:** For each secret in your `.env` file,
        create a corresponding secret in Google Cloud Secret Manager.

        ```bash
        while IFS= read -r line || [[ -n "$line" ]]; do
          if [[ -n "$line" && ! "$line" =~ ^# ]]; then
            key=$(echo "$line" | cut -d '=' -f1)
            value=$(echo "$line" | cut -d '=' -f2-)
            gcloud secrets create "$key" --replication-policy="automatic"
            echo -n "$value" | gcloud secrets versions add "$key" --data-file=-
          fi
        done < .env
        ```

2.  **Grant access to Cloud Run:** Grant the Cloud Run service's service account the "Secret Manager Secret Accessor" role for each secret. Replace `<your-cloud-run-service-name>` with your actual service name.

        ```bash
        SERVICE_NAME="<your-cloud-run-service-name>"
        PROJECT_ID=$(gcloud config get-value project)
        PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
        SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-run.iam.gserviceaccount.com"

        while IFS= read -r line || [[ -n "$line" ]]; do
          if [[ -n "$line" && ! "$line" =~ ^# ]]; then
            key=$(echo "$line" | cut -d '=' -f1)
            gcloud secrets add-iam-policy-binding "$key" \
              --member="serviceAccount:${SERVICE_ACCOUNT}" \
              --role="roles/secretmanager.secretAccessor"
          fi
        done < .env
        ```

3.  **Deploy a private service to Cloud Run:** To use IAP, your service must be private. Deploy it with the `--no-allow-unauthenticated` flag.

        ```bash
        gcloud run deploy agentic-dsta \
        --source .  \
        --region=$GOOGLE_CLOUD_LOCATION \
        --project=$GOOGLE_CLOUD_PROJECT \
        --no-allow-unauthenticated \
        --set-secrets="GOOGLE_API_KEY=GOOGLE_API_KEY:latest,GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest,GOOGLE_CLOUD_LOCATION=GOOGLE_CLOUD_LOCATION:latest,GOOGLE_GENAI_USE_VERTEXAI=GOOGLE_GENAI_USE_VERTEXAI:latest,GOOGLE_ADS_DEVELOPER_TOKEN=GOOGLE_ADS_DEVELOPER_TOKEN:latest,GOOGLE_ADS_CLIENT_ID=GOOGLE_ADS_CLIENT_ID:latest,GOOGLE_ADS_CLIENT_SECRET=GOOGLE_ADS_CLIENT_SECRET:latest,GOOGLE_ADS_REFRESH_TOKEN=GOOGLE_ADS_REFRESH_TOKEN:latest"
    ```

    *   `dsta-agentic-v1`: The name of your Cloud Run service.
    *   `--source .`: Builds and deploys the application from the current
        directory.
    *   `--region $GOOGLE_CLOUD_LOCATION`: Specifies the region for deployment.
    *   `--project $GOOGLE_CLOUD_PROJECT`: Specifies the Google Cloud Project
        ID.
    *   `--set-secrets`: Maps secrets from Secret Manager to environment variables for the Cloud Run service.
    *   `--no-allow-unauthenticated`: Makes the service private, requiring authentication for access. This is essential for IAP.

4.  **Configure IAP access:** Grant user accounts permission to access your service through IAP. Before you begin, ensure you have configured an OAuth consent screen. Then, for each user, run the following command, replacing `<service-name>` and `<your-email@example.com>`:

        ```bash
        gcloud beta services identity create --service=iap.googleapis.com --project=<PROJECT_ID>

        gcloud run services add-iam-policy-binding <SERVICE-NAME> \
          --region=$GOOGLE_CLOUD_LOCATION \
          --member='serviceAccount:service-<PROJECT-NUMBER>@gcp-sa-iap.iam.gserviceaccount.com'  \
          --user='user:username@xyz.com' \
          --role='roles/run.invoker'
        ```

5.  **Verify the deployment:** After deploying, you can verify that the secrets are correctly mounted as environment variables by running the following command. Replace `<service-name>` with your service name.

    ```bash
    gcloud run services describe <service-name> --region=$GOOGLE_CLOUD_LOCATION --project=$GOOGLE_CLOUD_PROJECT --format='yaml(spec.template.spec.containers[0].env)'
    ```

    The output will show a list of environment variables. You should see entries where the `name` corresponds to your secret key (e.g., `GOOGLE_API_KEY`) and the `valueFrom` section indicates that the value is being pulled from Secret Manager. You will not see the actual secret value in this output, which is the expected secure behavior.

## Security best practices

*   **Dependency pinning:** All dependencies in `requirements.txt` are pinned to specific versions. This mitigates the risk of supply chain attacks and ensures that your deployments are predictable. Regularly update your dependencies to patch known vulnerabilities.
*   **Principle of least privilege:** The `Dockerfile` creates a non-root user to run the application, reducing the potential impact of a container compromise. The Cloud Run service account is granted only the "Secret Manager Secret Accessor" and "Cloud Run Invoker" roles, ensuring it has only the permissions it needs to function.
*   **CORS:** For production environments, the `ALLOWED_ORIGINS` in `main.py` should be updated to a more restrictive list of trusted domains.
*   **Secret management:** All secrets are managed through Google Cloud Secret Manager, and the `.env` file is included in `.gitignore` to prevent accidental exposure.

**Important:** Never hardcode sensitive credentials. Using environment variables
ensures these are handled more securely.

**WARNING:** Do not commit `.env` files or hardcode secrets in your code.
It is strongly recommended to use a secret management solution like Google Cloud Secret Manager for production environments.
