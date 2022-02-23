#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import stat
import sys
import tempfile
import threading
from typing import List
from sys import argv
import os
import requests
import shutil
import json
import yaml
import subprocess
try:
    import semver
except Exception:
    print("Semver for python isn't installed")
    print("On Debian/Ubuntu, you can install it using")
    print("    sudo apt install -y python3-semver")
    print("On other systems, please use")
    print("     sudo pip3 install semver")
    print("Continuing anyway, but some features won't be available")
    print("Like checking for app updates")

from lib.composegenerator.v1.generate import createComposeConfigFromV1
from lib.composegenerator.v2.generate import createComposeConfigFromV2
from lib.validate import findAndValidateApps
from lib.metadata import getAppRegistry
from lib.entropy import deriveEntropy

# For an array of threads, join them and wait for them to finish


def joinThreads(threads: List[threading.Thread]):
    for thread in threads:
        thread.join()


# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..", "..")
appsDir = os.path.join(nodeRoot, "apps")
appSystemDir = os.path.join(nodeRoot, "app-system")
sourcesList = os.path.join(appSystemDir, "sources.list")
updateIgnore = os.path.join(appsDir, ".updateignore")
appDataDir = os.path.join(nodeRoot, "app-data")
userFile = os.path.join(nodeRoot, "db", "user.json")
legacyScript = os.path.join(nodeRoot, "scripts", "app")

# Returns a list of every argument after the second one in sys.argv joined into a string by spaces


def getArguments():
    arguments = ""
    for i in range(3, len(argv)):
        arguments += argv[i] + " "
    return arguments


def getAppYml(name):
    with open(os.path.join(appsDir, "sourceMap.json"), "r") as f:
        sourceMap = json.load(f)
    if not name in sourceMap:
        print("Warning: App {} is not in the source map".format(name))
        sourceMap = {
            name: {
                "githubRepo": "runcitadel/core",
                "branch": "v2"
            }
        }
    url = 'https://raw.githubusercontent.com/{}/{}/apps/{}/app.yml'.format(sourceMap[name]["githubRepo"], sourceMap[name]["branch"], name)
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return False

def update(verbose: bool = False):
    apps = findAndValidateApps(appsDir)
    # The compose generation process updates the registry, so we need to get it set up with the basics before that
    registry = getAppRegistry(apps, appsDir)
    with open(os.path.join(appsDir, "registry.json"), "w") as f:
        json.dump(registry, f, sort_keys=True)
    print("Wrote registry to registry.json")

    # Loop through the apps and generate valid compose files from them, then put these into the app dir
    for app in apps:
        composeFile = os.path.join(appsDir, app, "docker-compose.yml")
        appYml = os.path.join(appsDir, app, "app.yml")
        with open(composeFile, "w") as f:
            appCompose = getApp(appYml, app)
            if appCompose:
                f.write(yaml.dump(appCompose, sort_keys=False))
                if verbose:
                    print("Wrote " + app + " to " + composeFile)
    print("Generated configuration successfully")


def download(app: str):
    data = getAppYml(app)
    if data:
        with open(os.path.join(appsDir, app, "app.yml"), 'w') as f:
            f.write(data)
    else:
        print("Warning: Could not download " + app)


def getUserData():
    userData = {}
    if os.path.isfile(userFile):
        with open(userFile, "r") as f:
            userData = json.load(f)
    return userData

def checkUpdateAvailable(name: str) -> bool:
    latestAppYml = yaml.safe_load(getAppYml(name))
    with open(os.path.join(appsDir, name, "app.yml"), "r") as f:
        originalAppYml = yaml.safe_load(f)
    if not "metadata" in latestAppYml or not "version" in latestAppYml["metadata"] or not "metadata" in originalAppYml or not "version" in originalAppYml["metadata"]:
        print("App {} is not valid".format(name))
        return False
    return semver.compare(latestAppYml["metadata"]["version"], originalAppYml["metadata"]["version"]) > 0

def getAvailableUpdates():
    availableUpdates = []
    apps = findAndValidateApps(appsDir)
    for app in apps:
        try:
            if checkUpdateAvailable(app):
                availableUpdates.append(app)
        except Exception:
            print("Warning: Can't check app {} yet".format(app), file=sys.stderr)
    return availableUpdates

def startInstalled():
    # If userfile doesn't exist, just do nothing
    userData = {}
    if os.path.isfile(userFile):
        with open(userFile, "r") as f:
            userData = json.load(f)
    #threads = []
    for app in userData["installedApps"]:
        if not os.path.isdir(os.path.join(appsDir, app)):
            print("Warning: App {} doesn't exist on Citadel".format(app))
            continue
        print("Starting app {}...".format(app))
        # Run compose(args.app, "up --detach") asynchrounously for all apps, then exit(0) when all are finished
        #thread = threading.Thread(target=compose, args=(app, "up --detach"))
        #thread.start()
        #threads.append(thread)
        compose(app, "up --detach")
    #joinThreads(threads)


def stopInstalled():
    # If userfile doesn't exist, just do nothing
    userData = {}
    if os.path.isfile(userFile):
        with open(userFile, "r") as f:
            userData = json.load(f)
    threads = []
    for app in userData["installedApps"]:
        if not os.path.isdir(os.path.join(appsDir, app)):
            print("Warning: App {} doesn't exist on Citadel".format(app))
            continue
        print("Stopping app {}...".format(app))
        # Run compose(args.app, "up --detach") asynchrounously for all apps, then exit(0) when all are finished
        thread = threading.Thread(
            target=compose, args=(app, "rm --force --stop"))
        thread.start()
        threads.append(thread)
    joinThreads(threads)

# Loads an app.yml and converts it to a docker-compose.yml


def getApp(appFile: str, appId: str):
    with open(appFile, 'r') as f:
        app = yaml.safe_load(f)

    if not "metadata" in app:
        raise Exception("Error: Could not find metadata in " + appFile)
    app["metadata"]["id"] = appId

    if 'version' in app and str(app['version']) == "1":
        return createComposeConfigFromV1(app, nodeRoot)
    elif 'version' in app and str(app['version']) == "2":
        return createComposeConfigFromV2(app, nodeRoot)
    else:
        raise Exception("Error: Unsupported version of app.yml")


def compose(app, arguments):
    if not os.path.isdir(os.path.join(appsDir, app)):
        print("Warning: App {} doesn't exist on Citadel".format(app))
        return
    # Runs a compose command in the app dir
    # Before that, check if a docker-compose.yml exists in the app dir
    composeFile = os.path.join(appsDir, app, "docker-compose.yml")
    commonComposeFile = os.path.join(appSystemDir, "docker-compose.common.yml")
    os.environ["APP_DOMAIN"] = subprocess.check_output(
        "hostname -s 2>/dev/null || echo 'citadel'", shell=True).decode("utf-8").strip() + ".local"
    os.environ["APP_HIDDEN_SERVICE"] = subprocess.check_output("cat {} 2>/dev/null || echo 'notyetset.onion'".format(
        os.path.join(nodeRoot, "tor", "data", "app-{}/hostname".format(app))), shell=True).decode("utf-8").strip()
    os.environ["APP_SEED"] = deriveEntropy("app-{}-seed".format(app))
    # Allow more app seeds, with random numbers from 1-5 assigned in a loop
    for i in range(1, 6):
        os.environ["APP_SEED_{}".format(i)] = deriveEntropy("app-{}-seed{}".format(app, i))
    os.environ["APP_DATA_DIR"] = os.path.join(appDataDir, app)
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
    os.environ["LND_DATA_DIR"] = os.path.join(nodeRoot, "lnd")
    # List all hidden services for an app and put their hostname in the environment
    hiddenServices: List[str] = getAppHiddenServices(app)
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


def getAppHiddenServices(app: str):
    torDir = os.path.join(nodeRoot, "tor", "data")
    # List all subdirectories of torDir which start with app-${APP}-
    # but return them without the app-${APP}- prefix
    results = []
    for subdir in os.listdir(torDir):
        if subdir.startswith("app-{}-".format(app)):
            results.append(subdir[len("app-{}-".format(app)):])
    return results


# Parse the sources.list repo file, which contains a list of sources in the format
# <git-url> <branch>
# For every line, clone the repo to a temporary dir and checkout the branch
# Then, check that repos apps in the temporary dir/apps and for every app,
# overwrite the current app dir with the contents of the temporary dir/apps/app
# Also, keep a list of apps from every repo, a repo later in the file may not overwrite an app from a repo earlier in the file
def updateRepos():
    # Get the list of repos
    repos = []
    ignoreApps = []
    with open(sourcesList) as f:
        repos = f.readlines()
    try:
        with open(updateIgnore) as f:
            ignoreApps = f.readlines()
    except: pass
    # For each repo, clone the repo to a temporary dir, checkout the branch,
    # and overwrite the current app dir with the contents of the temporary dir/apps/app
    # Set this to ignoreApps. Normally, it keeps track of apps already installed from repos higher in the list,
    # but apps specified in updateignore have the highest priority
    alreadyInstalled = ignoreApps
    # A map of apps to their source repo
    sourceMap = {}
    for repo in repos:
        repo = repo.strip()
        if repo == "":
            continue
        # Also ignore comments
        if repo.startswith("#"):
            continue
        # Split the repo into the git url and the branch
        repo = repo.split(" ")
        if len(repo) != 2:
            print("Error: Invalid repo format in " + sourcesList)
            exit(1)
        gitUrl = repo[0]
        branch = repo[1]
        # Clone the repo to a temporary dir
        tempDir = tempfile.mkdtemp()
        print("Cloning the repository")
        # Git clone with a depth of 1 to avoid cloning the entire repo
        # Don't print anything to stdout, as we don't want to see the git clone output
        subprocess.run("git clone --depth 1 --branch {} {} {}".format(branch, gitUrl, tempDir), shell=True, stdout=subprocess.DEVNULL)
        # Overwrite the current app dir with the contents of the temporary dir/apps/app
        for app in os.listdir(os.path.join(tempDir, "apps")):
            # if the app is already installed, don't overwrite it
            if app in alreadyInstalled:
                continue
            if gitUrl.startswith("https://github.com"):
                sourceMap[app] = {
                    "githubRepo": gitUrl.removeprefix("https://github.com/").removesuffix(".git").removesuffix("/"),
                    "branch": branch,
                }
            if os.path.isdir(os.path.join(appsDir, app)):
                shutil.rmtree(os.path.join(appsDir, app), onerror=remove_readonly)
            if os.path.isdir(os.path.join(tempDir, "apps", app)):
                shutil.copytree(os.path.join(tempDir, "apps", app), os.path.join(appsDir, app),
                                symlinks=False, ignore=shutil.ignore_patterns(".gitignore"))
                alreadyInstalled.append(app)
        # Remove the temporary dir
        shutil.rmtree(tempDir)
    with open(os.path.join(appsDir, "sourceMap.json"), "w") as f:
        json.dump(sourceMap, f)
