'''
mobile-app-publish.py
Author: Bartosz Marchewka
Version: 1.0.0
This script automates the process of publishing a mobile application configuration using the MAF-Tool and MAS APIs. It performs the following steps:
1. Parses required command-line arguments for authentication and configuration.
2. Authenticates to the Application Configurator (MAF-Tool) using provided credentials.
3. Retrieves user profile information to extract the workspace ID.
4. Redownloads the latest application definition to ensure local changes are overwritten.
5. Creates a zip archive of customized files from the repository.
6. Uploads the zip file to the Application Configurator.
7. Verifies the publish status in a loop until completion.
Logging is used throughout to provide status updates and error reporting. SSL warnings are disabled for the session. Temporary files are managed in a dedicated directory.
Raises:
	Exception: If any step fails (e.g., authentication, file upload, status check).
Dependencies:
	- argparse
	- requests
	- urllib3
	- os
	- zipfile
	- logging
	- time
    - jmespath
'''

import argparse
import requests
from urllib3.exceptions import InsecureRequestWarning
import os
import zipfile
import logging
import time
import jmespath


# Create a temporary build folder for storing the zip file and logs
build_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
os.makedirs(build_dir, exist_ok=True)
# Define the full path to the log file
log_path = os.path.join(build_dir, "mobile-app-publish.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)

log_format = '%(asctime)s - %(levelname)s - %(message)s'
log_level = logging.INFO

# Configure logging
logging.basicConfig(
    filename=log_path,
    filemode='w',
	level=log_level,
	format=log_format
)

# Add console handler
console = logging.StreamHandler()
console.setLevel(log_level)
formatter = logging.Formatter(log_format)
console.setFormatter(formatter)
logging.getLogger().addHandler(console)


logging.info(f"Build folder: {build_dir}")
logging.info(f"Log file: {log_path}")

parser = argparse.ArgumentParser(description="Process --maf argument.")
parser.add_argument('--masAuthUrl', type=str, help='MASAUTH argument value')
parser.add_argument('--masApiUrl', type=str, help='MASAPI argument value')
parser.add_argument('--appId', type=str, help='APPID argument value')
parser.add_argument('--appConfigUrl', type=str, help='App Config Url argument value')
parser.add_argument('--appConfigUsername', type=str, help='Username argument value')
parser.add_argument('--appConfigPassword', type=str, help='Password argument value')

args = parser.parse_args()

required_args = {
	'masAuthUrl': args.masAuthUrl,
	'masApiUrl': args.masApiUrl,
	'appId': args.appId,
	'appConfigUrl': args.appConfigUrl,
	'appConfigUsername': args.appConfigUsername,
	'appConfigPassword': args.appConfigPassword
}

missing = [name for name, value in required_args.items() if not value]
if missing:
	parser.error(f"The following required arguments are missing: {', '.join(missing)}")

mas_auth_url = args.masAuthUrl
mas_api_url = args.masApiUrl
app_id = args.appId
app_config_url = args.appConfigUrl
app_config_username = args.appConfigUsername
app_config_password = args.appConfigPassword

logging.info(f"Application Configuration: {app_config_url}")
logging.info(f"MAS Api: {mas_api_url}")
logging.info(f"MAS Auth: {mas_auth_url}")
logging.info(f"Application ID: {app_id}")

# Disable SSL warnings globally
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
session = requests.Session()
session.verify = False


def authenticate():
    maf_tool_login_response = session.get(app_config_url)
    logging.info(f"Application configuration page status code: {maf_tool_login_response.status_code}")
    if maf_tool_login_response.status_code != 200:
        logging.error(f"Failed to connect to application configuration (MAF-Tool): {maf_tool_login_response.status_code} - {maf_tool_login_response.text}")
        raise Exception(f"Failed to connect to application configuration (MAF-Tool): {maf_tool_login_response.status_code}")
    auth_url = f"{mas_auth_url}/js/j_security_check"
    auth_data = {
        "j_username": app_config_username,
        "j_password": app_config_password
    }
    auth_response = session.post(auth_url, data=auth_data)
    logging.info(f"Auth response status code: {auth_response.status_code}")
    if auth_response.status_code != 200:
        logging.error(f"Authentication failed: {auth_response.status_code} - {auth_response.text}")
        raise Exception(f"Authentication failed: {auth_response.status_code}")

    
def getWorkspaceId():
	profile_url = f"{mas_api_url}/profile"
	profile_response = session.get(profile_url)
	if profile_response.status_code != 200:
		logging.error(f"Failed to fetch profile: {profile_response.status_code} - {profile_response.text}")
		raise Exception(f"Failed to fetch profile: {profile_response.status_code} - {profile_response.text}")
	profile_data = profile_response.json()
	workspace_id = jmespath.search('workspaces[0].metadata.labels."mas.ibm.com/workspaceId"', profile_data)
	return workspace_id

def redownloadApplicationDefinition():
	redownload_url = f"{app_config_url}/config/server/application/{app_id}/check-for-import?userId={app_config_username}&workspaceId={workspace_id}"
	redownload_response = session.post(redownload_url)
	if redownload_response.status_code != 200:
		logging.error(f"Failed to re-download application definition: {redownload_response.status_code} - {redownload_response.text}")
		raise Exception(f"Failed to re-download application definition: {redownload_response.status_code}")

	redownload_response_data = redownload_response.json()
	current_app_version = redownload_response_data.get("currentVersion")
	logging.info(f"Current {app_id} application version: {current_app_version}")

	refresh_app_url = f"{app_config_url}/config/server/application/{app_id}?refresh=true&userId={app_config_username}&workspaceId={workspace_id}"
	refresh_app_response = session.get(refresh_app_url)
	if refresh_app_response.status_code != 200:
		logging.error(f"Failed to refresh application: {refresh_app_response.status_code} - {refresh_app_response.text}")
		raise Exception(f"Failed to refresh application: {refresh_app_response.status_code}")

	refresh_app_data = refresh_app_response.json()
	app_name = refresh_app_data.get("appName")
	download_status = refresh_app_data.get("downloadStatus")
	logging.info(f"Application {app_name} download status: {download_status}")
 
def createZipFileWithCustomisations():
    src_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", f"{app_id}")
    zip_output_path = os.path.join(build_dir, f"{app_id}.zip")
    
    logging.info(f"Zipping contents of {src_folder} into {zip_output_path}")
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(src_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join(app_id, os.path.relpath(file_path, start=src_folder))
                zipf.write(file_path, arcname)
    return zip_output_path

def uploadZipFile():
    upload_url = f"{app_config_url}/config/server/application/{app_id}/upload-files?userId={app_config_username}&workspaceId={workspace_id}"
    with open(zip_output_path, 'rb') as zip_file:
        files = {'file': (os.path.basename(zip_output_path), zip_file, 'application/zip')}
        upload_response = session.post(upload_url, files=files)
        
        if upload_response.status_code != 201:
            logging.error(f"Failed to upload zip file: {upload_response.status_code} - {upload_response.text}")
            raise Exception(f"Failed to upload zip file: {upload_response.status_code}")
        
        logging.info(f"Zip file uploaded successfully: {upload_response.status_code}")
        
def publishApplication():
    publish_url = f"{app_config_url}/config/server/application/{app_id}?userId={app_config_username}&workspaceId={workspace_id}"
    publish_response = session.post(publish_url)
    if publish_response.status_code != 202:
        logging.error(f"Failed to publish application: {publish_response.status_code} - {publish_response.text}")
        raise Exception(f"Failed to publish application: {publish_response.status_code}")
    
    logging.info("Verifying publish status")
    publish_status = "RUNNING"
    status_url = f"{app_config_url}/config/server/application/{app_id}/status?userId={app_config_username}&workspaceId={workspace_id}"
    
    while True:
        status_response = session.get(status_url)
        if status_response.status_code != 200:
            logging.error(f"Failed to get publish status: {status_response.status_code} - {status_response.text}")
            raise Exception(f"Failed to get publish status: {status_response.status_code}")
        status_json = status_response.json()
        publish_status = status_json.get("publishStatus")
        logging.info(f"Current publish status: {publish_status}")
        if publish_status is None or publish_status.upper() == "COMPLETED":
            break
        time.sleep(30)
     
    

# -------------------------------------------------------------------------------------------
# 1. Authenticate to Application Configurator (MAF-TOOL).
# -------------------------------------------------------------------------------------------
logging.info("-01- Authenticate to Application Configurator (MAF-Tool)")
authenticate()

# -------------------------------------------------------------------------------------------
# 2. Get user profile information and extract workspace ID.
# -------------------------------------------------------------------------------------------
logging.info("-02- Fetching user profile information")
workspace_id = getWorkspaceId()
logging.info(f"Workspace ID: {workspace_id}")


# -------------------------------------------------------------------------------------------
# 3. Redownload the application definition.
#    Note: Doing this action tool will secure that any local changes in ./workspace folder
#          in PVC will be overwritten by the latest app version from the server.
#          This step is important before tool will upload zip file with customisations.
# -------------------------------------------------------------------------------------------
logging.info("-03- Redownloading application definition")
redownloadApplicationDefinition()

# -------------------------------------------------------------------------------------------
# 4. Create zip file in tmp directory with the files that were cusomised in the repository
# -------------------------------------------------------------------------------------------
logging.info("-04- Creating zip file with customisations")
zip_output_path = createZipFileWithCustomisations()
logging.info(f"Created zip archive at: {zip_output_path}")

# -------------------------------------------------------------------------------------------
# 5. Upload zip file to Application Configurator (MAF-TOOL).
# -------------------------------------------------------------------------------------------
logging.info("-05- Uploading zip file to Application Configurator (MAF-Tool)")
uploadZipFile()

# -------------------------------------------------------------------------------------------
# 6. Publish changes to MAS Manage
# -------------------------------------------------------------------------------------------
logging.info("-06- Execute publishing process to MAS Manage")
publishApplication()