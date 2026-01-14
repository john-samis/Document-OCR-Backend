# Google Cloud Auth and Deployment Notes

Contains Confluence style notes and a reference to authenticating for google cloud. This guide assume previous knowledge of 
Docker, some basic Google Cloud Platform, VSCode, and Linux.

---
## gcloud CLI

Using the `gcloud` CLI is installed implicity in our production and development containers. Their contents cna be found on the 
google cloud documentation on how to correctly install and use the gcloud CLI for GCP projects found [Here](https://docs.cloud.google.com/sdk/docs/install-sdk)

#### Once _Devcontainer_ is rebuilt:

```bash
gcloud --version
```

At this point, a `Google Cloud Project` should be created. For more info, refer to [GCP Guide](https://developers.google.com/workspace/guides/create-project).

We will now authentiate the dev container to the gcloud project.

```console
gcloud init
```
The terminal will prompt you to log in via Google's Auth. Follow the link and steps to accept.

#### IMPORTANT: 

It will prompt you to 'Sign in to the gcloud CLI' and will give you a verification code. It is very important that this 
code is kept secret.

Enter this code back into your terminal as prompet. you should now be autentiacated and can provision resources to the GCP project.


For headless auth, the following command is needed:
```bash
gcloud auth login --no-launch-browser
```


##  Artifact Registry

This is where our GitHub Actions CI will throw our container images. 

From the authenticated environment:
```bash
gcloud artifacts repositories create <REGISTRY_NAME> \
    --repository-format docker \
    --project <GCP_PROJECT_NAME> \
    --location <LOCATION>
```

## CI/CD and Cloud Deployment

Some files are needed to dictate the instructions of our deployment, and how it interacts wth our CI.

Create a file `cloudbuild.yaml`. It's content will dictate to build and push our image to the registry we have just created.
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.prod', '-t', '<LOCATION>-docker.pkg.dev/<GCP_PROJECT_NAME>/<NAME>/<REGISTRY_NAME>:latest', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '<LOCATION>-docker.pkg.dev/<GCP_PROJECT_NAME>/<REGISTRY_NAME>/<REGITRY_NAME>:latest']
```

The glcloud CLI will read this file from this point on.

#### Building via CLI

To build the production container via the CLI, and push it to our _Artifact Registry_ we issue:
```bash
gcloud builds submit --config=cloudbuild.yaml --project <GCP_PROJECT_NAME> .
```


Create a `service.yaml` file with the folowing contents:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: <REGISTRY_NAME>-service
spec:
  template:
    spec:
      containers:
        - image: <LOCATION>-docker.pkg.dev/<GCP_PROJECT_NAME>/<REGISTRY_NAME>/<CONTAINER_NAME>:latest
          env:
          ports:
            - containerPort: 4000
```

Then run 
```bash
gcloud run services replace service.yaml --region northamerica-northeast1
```





The following will instatiate a service from a pushed image: _IMAGE_ from the artifact registry. Where the 'service' rules is dictated in our 
`services.yaml` file. This will 'spin-up' our production container and the like. 

```bash
gcloud run services --region <DEPLOYMENT_REGION>
```
This will create a non-pubicly accessible instance of our container. 

We must create  another file `gcr-service-policy.yaml` to indicate that it is okay if the _public_ (Semantically the Frontend of our backend).

```yaml
bindins:
- members:
  - allUsers
  role: roles/run.invoker
```

Now, once again:

```bash
gcloud run services set-iam-policy <SERICE_NAME> <POLICY_FILE> --region <DEPLOYMENT_REGION>
```

For the identity authentication policy (IAM), if you are confused, don't worry. We wil simply set an authentication in our CI for a 
GCP 'Service Account '. Where 'SERVICE_NAME' is 'document-ocr-service' and POLICY_FILE is 'gcr-service-policy.yaml'

#### GCP Service Account

Navigate to the GCP Console in the project. Make a search for 'service account' and follow service account & IAM and admin. 

Click 'Create a service account', enter the name, account ID, description and related fields, simply click continue on 'Grant this service account access to project'
and 'Grant users access to this service account'. 

Once created navigate to `KEYS` and create a new key wit h'add key'. This will output a json with some metadata and a private key.

#### DO NOT SHARE THIS KEY WITH ANYONE OR ANYTHING, Store it safely in untracked .env and for CI, GitHub repository secrets.


## Creating the GitHub Actions Workflows 

Ran jobs are dictated in `.github/workflows/<WORKFLOW>.yml` files.

Reusable composite actions are found in the `.github/actions/<ACTION>/action.yml`.

Very possible you will run into authentication problems (as I have LOL). My error is with the 
artifact registry and I must then, indicate te scope ofthe service account for the project. This can be found in the Google Cloud Developer Console

```bash
gcloud projects add-iam-policy-binding document-ocr-480202 \
  --member="serviceAccount:<SERVICE_ACCOUNT_EMAIL>" \
  --role="roles/artifactregistry.writer"
```


We also require a few more permission sets:

```bash
gcloud services enable cloudresourcemanager.googleapis.com --project document-ocr-480202
```

```bash
gcloud services enable artifactregistry.googleapis.com run.googleapis.com --project document-ocr-480202
```


There's some oddities in the google cloud console in order to get the right IAM policies for google cloud run. Giving the service account the proper cloud run permissions:


```bash
gcloud projects add-iam-policy-binding document-ocr-480202 \
  --member="serviceAccount:document-ocr-ci@document-ocr-480202.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

as well as:

```bash
gcloud iam service-accounts add-iam-policy-binding RUNTIME_SA_EMAIL \
  --member="serviceAccount:document-ocr-ci@document-ocr-480202.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

```
