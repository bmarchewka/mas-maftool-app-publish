1. [Bitbucket Pipelines Configuration](#markdown-header-bitbucket-pipline)
2. [Mobile APP publish bash script](#markdown-header-mobile-app-publish)


<a name="markdown-header-bitbucket-pipline"></a>
# Bitbucket Pipelines Configuration

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
# Mobile App Publish Script

This script automates the process of publishing a mobile application to the Maximo Manage server using the Maximo Application Framework (MAF) tools.

## Prerequisites

- Docker installed and running
- IBM Cloud Registry credentials
- Required environment variables

## Usage

```bash
./mobile-app-publish.txt <appid> <entitlementkey> <environment> <apikey> <maftoolversion>
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