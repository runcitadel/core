# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import re
import shutil
import stat
import subprocess
import threading
from sys import argv
from typing import List

import yaml
from lib.citadelutils import parse_dotenv
from lib.entropy import deriveEntropy

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..", "..")
appsDir = os.path.join(nodeRoot, "apps")
appSystemDir = os.path.join(nodeRoot, "app")
appDataDir = os.path.join(nodeRoot, "app-data")
userFile = os.path.join(nodeRoot, "db", "user.json")
with open(os.path.join(nodeRoot, "db", "dependencies.yml"), "r") as file: 
  dependencies = yaml.safe_load(file)

dotenv = {}

def get_var_safe(var_name):
    dotenv = parse_dotenv(os.path.join(nodeRoot, ".env"))
    if var_name in dotenv:
        return str(dotenv[var_name])
    else:
        print("Error: {} is not defined!".format(var_name))
        return False

def get_var(var_name):
    var_value = get_var_safe(var_name)
    if var_value:
        return var_value
    else:
        print("Error: {} is not defined!".format(var_name))
        exit(1)

# Converts a string to uppercase, also replaces all - with _
def convert_to_upper(string):
  return string.upper().replace('-', '_')

# Put variables in the config file. A config file accesses an env var $EXAMPLE_VARIABLE by containing <example-variable>
# in the config file. Check for such occurences and replace them with the actual variable
def replace_vars(file_content: str):
  return re.sub(r'<(.*?)>', lambda m: get_var(convert_to_upper(m.group(1))), file_content)

def update():
    os.system("docker run --rm -v {}:/citadel -u 1000:1000 --add-host=host.docker.internal:host-gateway {} /app-cli convert /citadel --caddy-url http://host.docker.internal:2019/".format(nodeRoot, dependencies['app-cli']))
    print("Generated configuration successfully")

def downloadNew():
    os.system("docker run --rm -v {}:/citadel -u 1000:1000 --add-host=host.docker.internal:host-gateway {} /app-cli download-new /citadel".format(nodeRoot, dependencies['app-cli']))
    print("Generated configuration successfully")

def downloadAll():
    os.system("docker run --rm -v {}:/citadel -u 1000:1000 --add-host=host.docker.internal:host-gateway {} /app-cli download-apps /citadel".format(nodeRoot, dependencies['app-cli']))
    print("Generated configuration successfully")

def download(app_id):
    os.system("docker run --rm -v {}:/citadel -u 1000:1000 --add-host=host.docker.internal:host-gateway {} /app-cli download {} --citadel-root /citadel".format(nodeRoot, dependencies['app-cli'], app_id))
    print("Generated configuration successfully")

def getAvailableUpdates():
    os.system("docker run --rm -v {}:/citadel -u 1000:1000 --add-host=host.docker.internal:host-gateway {} /app-cli check-updates /citadel".format(nodeRoot, dependencies['app-cli']))
    print("Generated configuration successfully")

def getUserData():
    userData = {}
    if os.path.isfile(userFile):
        with open(userFile, "r") as f:
            userData = json.load(f)
    return userData

def compose(app, arguments):
    if not os.path.isdir(os.path.join(appsDir, app)):
        print("Warning: App {} doesn't exist on this node!".format(app))
        return
    virtual_apps = {}
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    userData = getUserData()
    for virtual_app in virtual_apps.keys():
        implementations = virtual_apps[virtual_app]
        for implementation in implementations:
            if "installedApps" in userData and implementation in userData["installedApps"]:
                if get_var_safe("APP_{}_SERVICE_IP".format(convert_to_upper(implementation))):
                    os.environ["APP_{}_IP".format(convert_to_upper(virtual_app))] = get_var_safe("APP_{}_SERVICE_IP".format(convert_to_upper(implementation)))  # type: ignore
                #if get_var_safe("APP_{}_SERVICE_PORT".format(convert_to_upper(implementation))):
                    #os.environ["APP_{}_PORT".format(virtual_app)] = get_var_safe("APP_{}_SERVICE_PORT".format(convert_to_upper(implementation)))  # type: ignore
                break
    # Runs a compose command in the app dir
    # Before that, check if a docker-compose.yml exists in the app dir
    composeFile = os.path.join(appsDir, app, "docker-compose.yml")
    commonComposeFile = os.path.join(appSystemDir, "docker-compose.common.yml")
    os.environ["APP_DOMAIN"] = subprocess.check_output(
        "hostname -s 2>/dev/null || echo 'citadel'", shell=True).decode("utf-8").strip() + ".local"
    os.environ["APP_HIDDEN_SERVICE"] = subprocess.check_output("cat {} 2>/dev/null || echo 'notyetset.onion'".format(
        os.path.join(nodeRoot, "tor", "data", "app-{}/hostname".format(app))), shell=True).decode("utf-8").strip()
    try:
        os.environ["APP_SEED"] = deriveEntropy("app-{}-seed".format(app))
        # Allow more app seeds, with random numbers from 1-5 assigned in a loop
        for i in range(1, 6):
            os.environ["APP_SEED_{}".format(i)] = deriveEntropy("app-{}-seed{}".format(app, i))
    except: pass
    os.environ["APP_DATA_DIR"] = os.path.join(appDataDir, app)
    os.environ["CITADEL_APP_DATA"] = appDataDir
    # Chown and chmod dataDir to have the owner 1000:1000 and the same permissions as appDir
    subprocess.call("chown -R 1000:1000 {}".format(os.path.join(appDataDir, app)), shell=True)
    try:
        os.chmod(os.path.join(appDataDir, app), os.stat(os.path.join(appsDir, app)).st_mode)
    except Exception:
        pass
    if app == "nextcloud":
        subprocess.call("chown -R 33:33 {}".format(os.path.join(appDataDir, app, "data", "nextcloud")), shell=True)
        subprocess.call("chmod -R 770 {}".format(os.path.join(appDataDir, app, "data", "nextcloud")), shell=True)
    os.environ["BITCOIN_DATA_DIR"] = os.path.join(nodeRoot, "bitcoin")
    # List all hidden services for an app and put their hostname in the environment
    hiddenServices: List[str] = getAppRegistryEntry(app).get("hiddenServices", [])
    for service in hiddenServices:
        appHiddenServiceFile = os.path.join(
            nodeRoot, "tor", "data", "app-{}-{}/hostname".format(app, service))
        os.environ["APP_HIDDEN_SERVICE_{}".format(service.upper().replace("-", "_"))] = subprocess.check_output("cat {} 2>/dev/null || echo 'notyetset.onion'".format(
            appHiddenServiceFile), shell=True).decode("utf-8").strip()

    if not os.path.isfile(composeFile):
        print("Error: Could not find docker-compose.yml in " + app)
        exit(1)
    os.system(
        "docker compose --env-file '{}' --project-name '{}' --file '{}' --file '{}' {}".format(
            os.path.join(nodeRoot, ".env"), app, commonComposeFile, composeFile, arguments))


def remove_readonly(func, path, _):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def deleteData(app: str):
    dataDir = os.path.join(appDataDir, app)
    try:
        shutil.rmtree(dataDir, onerror=remove_readonly)
    except FileNotFoundError:
        pass

def createDataDir(app: str):
    dataDir = os.path.join(appDataDir, app)
    appDir = os.path.join(appsDir, app)
    if os.path.isdir(dataDir):
        deleteData(app)
    # Recursively copy everything from appDir to dataDir while excluding .gitkeep files
    shutil.copytree(appDir, dataDir, symlinks=False,
                    ignore=shutil.ignore_patterns(".gitkeep"))
    # Chown and chmod dataDir to have the owner 1000:1000 and the same permissions as appDir
    subprocess.call("chown -R 1000:1000 {}".format(os.path.join(appDataDir, app)), shell=True)
    os.chmod(dataDir, os.stat(appDir).st_mode)


def setInstalled(app: str):
    userData = getUserData()
    if not "installedApps" in userData:
        userData["installedApps"] = []
    userData["installedApps"].append(app)
    userData["installedApps"] = list(set(userData["installedApps"]))
    with open(userFile, "w") as f:
        json.dump(userData, f)


def setRemoved(app: str):
    userData = getUserData()
    if not "installedApps" in userData:
        return
    userData["installedApps"] = list(set(userData["installedApps"]))
    userData["installedApps"].remove(app)
    with open(userFile, "w") as f:
        json.dump(userData, f)

# Gets the app's registry entry from the registry.json file
# The file is an array of objects, each object is an app's registry entry
# We can filter by the "id" property to get the app's registry entry
def getAppRegistryEntry(app: str):
    with open(os.path.join(appsDir, "registry.json")) as f:
        registry = json.load(f)
    for appRegistryEntry in registry:
        if appRegistryEntry["id"] == app:
            return appRegistryEntry
    return None
