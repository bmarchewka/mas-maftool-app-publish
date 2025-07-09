![mastool-bitbucket](https://github.com/user-attachments/assets/13e6972a-1337-44e6-80c0-4ae395086e5f)

1. Maximo Application Suite v9.0.x
   - [Bitbucket Pipelines Configuration](#markdown-header-bitbucket-pipline)
   - [Mobile APP publish bash script](#markdown-header-mobile-app-publish)
2. Maximo Application Suite v9.1.x
   - [Bitbucket Pipelines Configuration](#markdown-header-bitbucket-pipline-mas-91)
   - [Mobile APP publish python script](#markdown-header-mobile-app-publish-mas-91)


<a name="markdown-header-bitbucket-pipline"></a>
# Bitbucket Pipelines Configuration (MAS v9.0.x)

This document provides an overview and explanation of the `bitbucket-pipelines.yaml` configuration file used for setting up CI/CD pipelines in Bitbucket.

## Image
```yaml
image: atlassian/default-image:latest
```
Specifies the Docker image to be used for the pipeline. In this case, it uses the default Atlassian image.

## Definitions
### Services
```yaml
services:
  docker:
    memory: 12288
```
Defines the services required for the pipeline. Here, Docker is used with a memory allocation of 12288 MB.

### Steps

#### Publish Step

This step is used for publishing the mobile application.
```yaml
- step: &publish-step
    name: Mobile App Publish
    size: 4x
    max-time: 20
    script:
      - apt-get update && apt-get install -y jq
      - chmod +x ./mobile-app-publish.sh
      - ./mobile-app-publish.sh $APP_ID $ENTITLEMENT_KEY $ENVIRONMENT_URL $API_KEY $MAFTOOLS_VERSION
    services:
      - docker
```

### Services

- **Docker**: The Docker service is used in the pipeline.

## Pipelines

### Custom Pipelines

#### Mobile Publish Dev/Test/Prod

Custom pipeline step is used for publishing the mobile application to the dev/test/prod environments.

Example step for PROD:
```yaml
mobile-publish-prod:
  - variables:
    - name: APP_ID
      default: "TECHMOBILE"
      allowed-values:
        - "TECHMOBILE"
        - "SRMOBILE"
        - "INSPECTION"
        - "IRMOBILE"
  - step:
      <<: *publish-step
      deployment: PROD
```

<a name="markdown-header-mobile-app-publish"></a>
# Mobile App Publish Script (MAS v9.0.x)

This script automates the process of publishing a mobile application to the Maximo Manage server using the Maximo Application Framework (MAF) tools.

## Usage

```bash
./mobile-app-publish.sh <appid> <entitlementkey> <environment> <apikey> <maftoolversion>
```

### Parameters

- `appid`: The ID of the mobile application to be published.
- `entitlementkey`: IBM entitlement key for accessing the IBM Cloud Registry.
- `environment`: The target environment URL.
- `apikey`: API key for authentication.
- `maftoolversion`: Version of the MAF tools to be used.

## Environment Variables

- `GRAPHITE_RELEASE`: Reduces the size of the application package (default: 1).
- `NODE_TLS_REJECT_UNAUTHORIZED`: Bypasses system checks for a valid security certificate in development or demonstration environments (default: 0).

## Script Workflow

1. **Login to IBM Cloud Registry**: Authenticates using the provided entitlement key.
2. **Pull MAF Tools Image**: Downloads the specified version of the MAF tools Docker image.
3. **Create Workspace**: Sets up a temporary workspace for the MAF tools.
4. **Create and Start Container**: Runs the MAF tools container.
5. **Authorize**: Authenticates with the MAF tools server.
6. **Get Application Definition**: Retrieves the application definition and sets up the workspace.
7. **Copy Files**: Copies the custom mobile application files to the workspace.
8. **Remove Build Folder**: Cleans up the workspace by removing the build folder.
9. **Publish Application**: Publishes the application to the Maximo Manage server.
10. **Verify Publish Status**: Checks the status of the publishing process.
11. **Cleanup**: Stops and removes the Docker container and workspace.

## Error Handling

The script includes error handling for various stages, such as authentication failures, container startup issues, and publishing errors. Appropriate messages are displayed, and the script exits with a non-zero status code in case of errors.




<a name="markdown-header-bitbucket-pipline-mas-91"></a>
# Bitbucket Pipelines Configuration (MAS v9.1.x)

This document provides an overview and explanation of the `bitbucket-pipelines-mas-91.yaml` configuration file used for setting up CI/CD pipelines in Bitbucket.

## Image
```yaml
image: python:3.13-slim
```
Specifies the Docker image to be used for the pipeline. In this case, it uses python:3.13-slim image.

## Definitions

### Steps

#### Publish Step

This step is used for publishing the mobile application.
```yaml
- step: &publish-step
    name: Mobile App Publish
    max-time: 20
    script:
      - python -m venv maftool && . maftool/bin/activate
      - pip install requests jmespath
      - python ./mobile-app-publish.py --masAuthUrl $MAS_AUTH_URL --masApiUrl $MAS_API_URL --appId $APP_ID --appConfigUrl $APP_CONFIG_URL --appConfigUsername $APP_CONFIG_USERNAME --appConfigPassword $APP_CONFIG_PASSWORD
    artifacts:
      - build/**
    services:
      - docker
```

### Services

- **Docker**: The Docker service is used in the pipeline.

## Pipelines

### Custom Pipelines

#### Mobile Publish Dev/Test/Prod

Custom pipeline step is used for publishing the mobile application to the dev/test/prod environments.

Example step for PROD:
```yaml
mobile-publish-prod:
  - variables:
    - name: APP_ID
      default: "TECHMOBILE"
      allowed-values:
        - "TECHMOBILE"
        - "SRMOBILE"
        - "INSPECTION"
        - "IRMOBILE"
        - "ICMOBILE"
  - step:
      <<: *publish-step
      deployment: PROD
```

<a name="markdown-header-mobile-app-publish-mas-91"></a>
# Mobile App Publish Script (MAS v9.1.x)

This script automates the process of publishing a mobile application to the Maximo Manage server using the Application Configuration.

## Usage

```bash
./mobile-app-publish.py --masAuthUrl <masAuthUrl> --masApiUrl <masApiUrl> --appId <appId> --appConfigUrl <appConfigUrl> --appConfigUsername <appConfigUsername> --appConfigPassword <appConfigPassword> 
```

### Parameters

- `masAuthUrl`: https://auth.<mas_domain>
- `masApiUrl`: https://api.<mas_domain>
- `appid`: The ID of the mobile application to be published
- `appConfigUrl`: https://appconfig.<mas_domain>
- `appConfigUsername`: Admin user that has access to Application Configuration (appconfig)
- `appConfigPassword`: Password for the user <appConfigUsername>


## Script Workflow

1. Parses required command-line arguments for authentication and configuration.
2. Authenticates to the Application Configuration using provided credentials.
3. Retrieves user profile information to extract the workspace ID.
4. Redownloads the latest application definition to ensure local changes are overwritten.
5. Creates a zip archive of customized files from the repository.
6. Uploads the zip file to the Application Configuration.
7. Verifies the publish status in a loop until completion.

## Error Handling

The script includes error handling for various stages, such as authentication failures and publishing errors. Appropriate messages are displayed.