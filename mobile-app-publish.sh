#!/usr/bin/env bash

# IMPORTANT: This is to export local variables as environment variables
APP_ID=$1
IBM_ENTITLEMENT_KEY=$2
ENVIRONMENT=$3
API_KEY=$4
MAFTOOLS_VERSION=$5

IBM_REPOSITORY=cp.icr.io
MAFTOOLS_REPOSITORY=$IBM_REPOSITORY/cp/manage/maf-tools
WORKING_DIRECTORY=$(pwd)
MAFTOOLS_WORKSPACE=$WORKING_DIRECTORY/build
MAFTOOLS_CONTAINER_NAME=maftools-publisher
MAFTOOLS_URL=http://localhost:3001/config/server
REPO_MOBILE_FOLDER=$WORKING_DIRECTORY/src
CURL_RESPONSE=$MAFTOOLS_WORKSPACE/curl-response.json
# Environment variables:
# 1. GRAPHITE_RELEASE parameter to reduce the size of the application package that you publish back to the Maximo® Manage server. 
#    Using this parameter can affect performance of the Maximo Application Framework Configuration application
MAFTOOLS_GRAPHITE_RELEASE=1
# 2. Maximo Manage requires a valid security certificate to retrieve and publish applications from the Maximo Application Framework Configuration
#    application in production environments. In development or demonstration environments, you can use the NODE_TLS_REJECT_UNAUTHORIZED parameter 
#    to bypass system checks for a valid security certificate.
MAFTOOLS_NODE_TLS_REJECT_UNAUTHORIZED=0

if [ -z "$APP_ID" ] || [ -z "$IBM_ENTITLEMENT_KEY" ] || [ -z "$ENVIRONMENT" ] || [ -z "$API_KEY" ] || [ -z "$MAFTOOLS_VERSION" ]; then
    echo "Usage: $0 <appid> <entitlementkey> <environment> <apikey> <maftoolversion>"
    exit 1
fi

echo "# --------------------------------------------------------------"
echo "# Prerequisites - pull maftools image and create container"
echo "# --------------------------------------------------------------"

echo "Logging into IBM Cloud Registry"
docker login $IBM_REPOSITORY \
    --username cp \
    --password $IBM_ENTITLEMENT_KEY

echo "Pulling MAF Tools image"
docker pull $MAFTOOLS_REPOSITORY:$MAFTOOLS_VERSION


echo "Creating workspace: $MAFTOOLS_WORKSPACE"
mkdir -p $MAFTOOLS_WORKSPACE

if [ "$(docker ps -aq -f name=$MAFTOOLS_CONTAINER_NAME)" ]; then
    echo "Container $MAFTOOLS_CONTAINER_NAME already exists. Skipping creation."
else
    echo "Creating container $MAFTOOLS_CONTAINER_NAME"
    docker run -dt --name $MAFTOOLS_CONTAINER_NAME \
        --memory 12g \
        --publish 3001:3001 \
        --publish 3006:3006 \
        --volume $MAFTOOLS_WORKSPACE:/graphite/.workspace \
        --env GRAPHITE_RELEASE=$MAFTOOLS_GRAPHITE_RELEASE \
        --env NODE_TLS_REJECT_UNAUTHORIZED=$MAFTOOLS_NODE_TLS_REJECT_UNAUTHORIZED \
        $MAFTOOLS_REPOSITORY:$MAFTOOLS_VERSION
fi

# Check if the container is running
if docker ps --filter "name=$MAFTOOLS_CONTAINER_NAME" --filter "status=running" | grep $MAFTOOLS_CONTAINER_NAME; then
    echo "Container $MAFTOOLS_CONTAINER_NAME is running."
else
    echo "Container $MAFTOOLS_CONTAINER_NAME failed to start."
    exit 1
fi

# Wait for the MAFTOOL server to start
until docker logs $MAFTOOLS_CONTAINER_NAME 2>&1 | grep -q "Your server is running"; do
    echo "Waiting for the maf-tools server to start..."
    sleep 5
done

echo "# --------------------------------------------------------------"
echo "# This is the main section where the mobile app will be published"
echo "# --------------------------------------------------------------"

echo "Mobile appid: $APP_ID"
echo "Target environment: $ENVIRONMENT"

# 1. Authorize
echo "1. Authorize"
AUTH_RESPONSE=$(curl \
    --silent \
    --location "$MAFTOOLS_URL/auth" \
    --cookie-jar $MAFTOOLS_WORKSPACE/cookies.txt \
    --header "x-maximo-host-url: $ENVIRONMENT" \
    --header "x-maximo-api-key: $API_KEY" \
    --write-out "%{http_code}" \
    --output $CURL_RESPONSE
)

if [ "$AUTH_RESPONSE" -ne 200 ]; then
    echo "Authorization failed with response code $AUTH_RESPONSE"
    exit 1
fi

echo "Auth response: $AUTH_RESPONSE"

#2. Get application definition - as a consequence of this request,
#   application folder will be created in the workspace
echo "2. Get application definition"
APP_GET_CODE=$(
    curl \
        --silent \
        --location "$MAFTOOLS_URL/application/$APP_ID?refresh=false" \
        --cookie $MAFTOOLS_WORKSPACE/cookies.txt \
        --write-out "%{http_code}" \
        --output $CURL_RESPONSE
    )

if [ "$APP_GET_CODE" -ne 200 ]; then
    echo "Application get method failed with response code $APP_GET_CODE"
    exit 1
fi

APP_NAME=$(jq -r '.appName' $CURL_RESPONSE)
APP_VERSION=$(jq -r '.version' $CURL_RESPONSE)

echo "App Name: $APP_NAME"
echo "App Version: $APP_VERSION"

# Wait untill maf-tool will log "Starting the development server"
until docker logs $MAFTOOLS_CONTAINER_NAME 2>&1 | grep -q "Starting the development server"; do
    echo "Waiting for the maf-tools will starting development server process..."
    sleep 10
done

echo "3. Copy files from prepository to workspace."
ENV_FOLDER=$(ls -d $MAFTOOLS_WORKSPACE/*/ | head -n 1)
ENV_FOLDER_NAME=$(basename $ENV_FOLDER)

echo "Env folder name: $ENV_FOLDER_NAME"
echo "Copy files from $REPO_MOBILE_FOLDER to $MAFTOOLS_WORKSPACE/$ENV_FOLDER_NAME"
cp -r $REPO_MOBILE_FOLDER/* $MAFTOOLS_WORKSPACE/$ENV_FOLDER_NAME

echo "4. Remove app dedicated build folder from workspace"
APP_WORKSPACE_FODLER=$MAFTOOLS_WORKSPACE/$ENV_FOLDER_NAME/$APP_ID/build
echo "Folder path: $APP_WORKSPACE_FODLER"
rm -rf $MAFTOOLS_WORKSPACE/$ENV_FOLDER_NAME/$APP_ID/build

echo "5. Publishing application"

APP_POST_CODE=$(
    curl \
        --location \
        --request POST "$MAFTOOLS_URL/application/$APP_ID" \
        --cookie $MAFTOOLS_WORKSPACE/cookies.txt \
        --write-out "%{http_code}" \
        --output $CURL_RESPONSE
)

if [ "$APP_POST_CODE" -ne 202 ]; then
    echo "Application POST method failed with response code $APP_GET_CODE"
    exit 1
fi

sleep 10

echo "6. Publish status verification"
while true ; do
    APP_STATUS_CODE=$(
        curl \
            --silent \
            --location "$MAFTOOLS_URL/application/$APP_ID/status" \
            --cookie $MAFTOOLS_WORKSPACE/cookies.txt \
            --write-out "%{http_code}" \
            --output $CURL_RESPONSE
    )

    if [ "$APP_STATUS_CODE" -ne 200 ]; then
        echo "Application GET STATUS method failed with response code $APP_STATUS_CODE"
        exit 1
    fi

    CURRENT_STATUS=$(jq -r '.publishStatus' $CURL_RESPONSE)
    echo "App publishStatus: $CURRENT_STATUS"

    if [ "$CURRENT_STATUS" == "completed" ]; then
        echo "App was successfully published"
        break
    fi

    echo "Waiting until app will be successfully published"
    docker logs --tail 3 $MAFTOOLS_CONTAINER_NAME | head -n 1
    sleep 30
done

echo "$APP_ID has been successfully published"

echo "Stopping and removing container $MAFTOOLS_CONTAINER_NAME"
docker stop $MAFTOOLS_CONTAINER_NAME && docker rm $MAFTOOLS_CONTAINER_NAME