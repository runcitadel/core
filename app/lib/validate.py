# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from re import S
import yaml

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
        allowed_app_files = 3
        if os.path.isfile(os.path.join(app_dir, "app.yml.jinja")):
            allowed_app_files += 1
            os.chown(app_dir, 1000, 1000)
            os.system(
                "docker run --rm -v {}:/apps -u 1000:1000 {} /app-cli preprocess --app-name '{}' /apps/{}/app.yml.jinja /apps/{}/app.yml --services 'lnd'".format(
                    dir, dependencies["app-cli"], subdir.name, subdir.name, subdir.name
                )
            )
        for subfile in os.scandir(subdir):
            if allowed_app_files == 0:
                break
            if (
                subfile.is_file()
                and subfile.name.endswith(".jinja")
                and subfile.name != "app.yml.jinja"
            ):
                allowed_app_files -= 1
                os.chown(subfile.path, 1000, 1000)
                cmd = "docker run --rm -v {}:/seed -v {}:/.env -v {}:/apps -u 1000:1000 {} /app-cli preprocess-config-file --env-file /.env --app-name '{}' --app-file '/apps/{}/{}' /apps/{}/{} /apps/{}/{} --services 'lnd' --seed-file /seed".format(
                    os.path.join(nodeRoot, "citadel-seed", "seed"),
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
                )
                print(cmd)
                os.system(cmd)

        if not os.path.isfile(os.path.join(app_dir, "app.yml")):
            print("App {} has no app.yml".format(subdir.name))
        else:
            apps.append(subdir.name)
    return apps
