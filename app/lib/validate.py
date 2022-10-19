# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os

import yaml

scriptDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
nodeRoot = os.path.join(scriptDir, "..")
userFile = os.path.join(nodeRoot, "db", "user.json")
appsDir = os.path.join(nodeRoot, "apps")

with open(os.path.join(nodeRoot, "db", "dependencies.yml"), "r") as file:
    dependencies = yaml.safe_load(file)

def getUserData():
    userData = {}
    if os.path.isfile(userFile):
        with open(userFile, "r") as f:
            userData = json.load(f)
    return userData

def getInstalledVirtualApps():
    installedApps = []
    try:
        with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
            virtual_apps = json.load(f)
        userData = getUserData()
        for virtual_app in virtual_apps.keys():
            for implementation in virtual_apps[virtual_app]:
                if "installedApps" in userData and implementation in userData["installedApps"]:
                    installedApps.append(virtual_app)
    except: pass
    return installedApps


# Lists all folders in a directory and checks if they are valid
# A folder is valid if it contains an app.yml file
# A folder is invalid if it doesn't contain an app.yml file
def findAndValidateApps(dir: str):
    services = ["lnd", "bitcoin"]
    userData = getUserData()
    if not "installedApps" in userData:
        userData["installedApps"] = []
    services.extend(userData["installedApps"])
    services.extend(getInstalledVirtualApps())
    service_str = ",".join(services)
    apps = []
    for subdir in os.scandir(dir):
        if not subdir.is_dir():
            continue
        app_dir = subdir.path
        allowed_app_files = 3
        if os.path.isfile(os.path.join(app_dir, "app.yml.jinja")):
            allowed_app_files += 1
            os.chown(app_dir, 1000, 1000)
            os.system(
                "docker run --rm -v {}:/apps -u 1000:1000 {} /app-cli preprocess --app-name '{}' /apps/{}/app.yml.jinja /apps/{}/app.yml --services '{}'".format(
                    dir, dependencies["app-cli"], subdir.name, subdir.name, subdir.name, service_str
                )
            )
            # App should be re-converted considering this may have changed the app.yml
            if os.path.isfile(os.path.join(app_dir, "result.yml")):
                os.remove(os.path.join(app_dir, "result.yml"))
        for subfile in os.scandir(subdir):
            if allowed_app_files == 0:
                break
            if (
                subfile.is_file()
                and subfile.name.endswith(".jinja")
                and subfile.name != "app.yml.jinja"
            ):
                allowed_app_files -= 1
                os.chown(app_dir, 1000, 1000)
                cmd = "docker run --rm -v {}:/seed -v {}:/.env -v {}:/apps -u 1000:1000 {} /app-cli preprocess-config-file --env-file /.env --app-name '{}' --app-file '/apps/{}/{}' /apps/{}/{} /apps/{}/{} --services '{}' --seed-file /seed".format(
                    os.path.join(nodeRoot, "db", "citadel-seed", "seed"),
                    os.path.join(nodeRoot, ".env"),
                    dir,
                    dependencies["app-cli"],
                    subdir.name,
                    subdir.name,
                    "app.yml",
                    subdir.name,
                    subfile.name,
                    subdir.name,
                    subfile.name[:-6],
                    service_str,
                )
                print(cmd)
                os.system(cmd)

        if not os.path.isfile(os.path.join(app_dir, "app.yml")):
            print("App {} has no app.yml".format(subdir.name))
        else:
            apps.append(subdir.name)
    return apps
