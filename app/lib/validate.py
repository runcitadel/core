# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import yaml
import traceback

scriptDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
nodeRoot = os.path.join(scriptDir, "..")

with open(os.path.join(nodeRoot, "db", "dependencies.yml"), "r") as file: 
  dependencies = yaml.safe_load(file)

# Lists all folders in a directory and checks if they are valid
# A folder is valid if it contains an app.yml file
# A folder is invalid if it doesn't contain an app.yml file
def findAndValidateApps(dir: str):
    apps = []
    for subdir in os.scandir(dir):
        if not subdir.is_dir():
            continue
        app_dir = subdir.path
        if os.path.isfile(os.path.join(app_dir, "app.yml.jinja")):
            os.chown(app_dir, 1000, 1000)
            os.system("docker run --rm -v {}:/apps -u 1000:1000 {} /app-cli preprocess --app-name '{}' /apps/{}/app.yml.jinja /apps/{}/app.yml --services 'lnd'".format(dir, dependencies['app-cli'], subdir.name, subdir.name, subdir.name))
        if not os.path.isfile(os.path.join(app_dir, "app.yml")):
            print("App {} has no app.yml".format(subdir.name))

    return apps
