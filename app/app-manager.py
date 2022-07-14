#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from lib.manage import compose, createDataDir, deleteData, getUserData, setInstalled, setRemoved, startInstalled, stopInstalled, update, deriveEntropy, updateRepos, download, getAvailableUpdates
from lib.validate import findAndValidateApps
import os
import argparse

# Print an error if user is not root
if os.getuid() != 0:
    print('This script must be run as root!')
    exit(1)

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..")
appsDir = os.path.join(nodeRoot, "apps")
appDataDir = os.path.join(nodeRoot, "app-data")
userFile = os.path.join(nodeRoot, "db", "user.json")
legacyScript = os.path.join(nodeRoot, "scripts", "app")

parser = argparse.ArgumentParser(description="Manage apps on your Citadel")
parser.add_argument('action', help='What to do with the app database.', choices=[
                    "list", "download", "generate", "update", "list-updates", "ls-installed", "install", "uninstall", "stop", "start", "compose", "restart", "entropy"])
# Add the --invoked-by-configure option, which is hidden from the user in --help
parser.add_argument('--invoked-by-configure',
                    action='store_true', help=argparse.SUPPRESS)
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument(
    'app', help='Optional, the app to perform an action on. (For install, uninstall, stop, start and compose)', nargs='?')
parser.add_argument(
    'other', help='Anything else (For compose)', nargs="*")
args = parser.parse_args()

# If no action is specified, the list action is used
if args.action is None:
    args.action = 'list'

if args.action == 'list':
    apps = findAndValidateApps(appsDir)
    for app in apps:
        print(app)
    exit(0)
elif args.action == "list-updates":
    availableUpdates = getAvailableUpdates()
    print(json.dumps(availableUpdates))
    exit(0)
elif args.action == 'download':
    updateRepos()
    exit(0)
elif args.action == 'generate':
    if args.invoked_by_configure:
        update(args.app)
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app-tor")
        os.system("docker compose start app-tor")
        os.system("docker compose stop app-2-tor")
        os.system("docker compose start app-2-tor")
        os.system("docker compose stop app-3-tor")
        os.system("docker compose start app-3-tor")
    exit(0)
elif args.action == 'update':
    if args.app is None:
        updateRepos()
        print("Downloaded all updates")
    else:
        download(args.app)
        print("Downloaded latest {} version".format(args.app))
    if args.invoked_by_configure:
        update(args.verbose)
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app-tor")
        os.system("docker compose start app-tor")
        os.system("docker compose stop app-2-tor")
        os.system("docker compose start app-2-tor")
        os.system("docker compose stop app-3-tor")
        os.system("docker compose start app-3-tor")
    exit(0)
elif args.action == 'ls-installed':
    # Load the userFile as JSON, check if installedApps is in it, and if so, print the apps
    with open(userFile, "r") as f:
        userData = json.load(f)
    if "installedApps" in userData:
        print("\n".join(userData["installedApps"]))
    else:
        # To match the behavior of the old script, print a newline if there are no apps installed
        print("\n")
elif args.action == 'install':
    if not args.app:
        print("No app provided")
        exit(1)
    createDataDir(args.app)
    compose(args.app, "pull")
    compose(args.app, "up --detach")
    setInstalled(args.app)
elif args.action == 'uninstall':
    if not args.app:
        print("No app provided")
        exit(1)
    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not installed".format(args.app))
        exit(1)
    print("Stopping app {}...".format(args.app))
    try:
        compose(args.app, "rm --force --stop")
        print("Deleting data...")
        deleteData(args.app)
    except:
        pass
    print("Removing from the list of installed apps...")
    setRemoved(args.app)
elif args.action == 'stop':
    if not args.app:
        print("No app provided")
        exit(1)
    userData = getUserData()
    if args.app == "installed":
        if "installedApps" in userData:
            stopInstalled()
        exit(0)
    print("Stopping app {}...".format(args.app))
    compose(args.app, "rm --force --stop")
elif args.action == 'start':
    if not args.app:
        print("No app provided")
        exit(1)

    userData = getUserData()
    if args.app == "installed":
        if "installedApps" in userData:
            startInstalled()
        exit(0)

    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not yet installed".format(args.app))
        exit(1)
    compose(args.app, "up --detach")

elif args.action == 'restart':
    if not args.app:
        print("No app provided")
        exit(1)
    if args.app == "installed":
        stopInstalled()
        startInstalled()
        exit(0)

    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not yet installed".format(args.app))
        exit(1)
    compose(args.app, "rm --force --stop")
    compose(args.app, "up --detach")

elif args.action == 'compose':
    if not args.app:
        print("No app provided")
        exit(1)
    compose(args.app, " ".join(args.other))

elif args.action == "entropy":
    if args.app == "":
        print("Missing identifier for entropy")
        exit(1)
    print(deriveEntropy(args.app))

else:
    print("Error: Unknown action")
    print("See --help for usage")
    exit(1)
