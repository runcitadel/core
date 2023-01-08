#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import json
import os
import time

from lib.manage import (compose, convert_to_upper, createDataDir, deleteData,
                        download, downloadAll, downloadNew, get_var_safe,
                        getAvailableUpdates, getUserData, setInstalled,
                        setRemoved, update, getAppRegistryEntry)

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
torDataDir = os.path.join(nodeRoot, "tor", "data")

parser = argparse.ArgumentParser(description="Manage apps on your Citadel")
parser.add_argument('action', help='What to do with the app database.', choices=[
                    "download", "generate", "update", "list-updates", "ls-installed", "install", "uninstall", "stop", "start", "compose", "restart", "get-ip", "get-implementation"])
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument(
    'app', help='Optional, the app to perform an action on. (For install, uninstall, stop, start and compose)', nargs='?')
parser.add_argument(
    'other', help='Anything else (For compose)', nargs="*")
args = parser.parse_args()

# If no action is specified, the list action is used
if args.action is None:
    args.action = 'list'

if args.action == "list-updates":
    getAvailableUpdates()
    exit(0)
elif args.action == 'download':
    downloadAll()
    exit(0)
elif args.action == 'download-new':
    downloadNew()
    exit(0)
elif args.action == 'generate':
    update()
    exit(0)
elif args.action == 'update':
    if args.app is None:
        downloadAll()
        print("Downloaded all updates")
    else:
        download(args.app)
        print("Downloaded latest {} version".format(args.app))
    update()
    exit(0)
elif args.action == 'ls-installed':
    # Load the userFile as JSON, check if installedApps is in it, and if so, print the apps
    with open(userFile, "r") as f:
        userData = json.load(f)
    if "installedApps" in userData:
        with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
            virtual_apps = json.load(f)
        # Print the apps
        # Filter out virtual apps (virtual_apps.keys())
        for app in userData["installedApps"]:
            if app not in virtual_apps.keys():
                print(app)
    else:
        # To match the behavior of the old script, print a newline if there are no apps installed
        print("\n")
elif args.action == 'install':
    if not args.app:
        print("No app provided")
        exit(1)
    registryEntry = getAppRegistryEntry(args.app)
    # If registryEntry is None, fail
    if registryEntry is None:
        print("App {} does not seem to exist".format(args.app))
        exit(1)
    if isinstance(registryEntry['hiddenServices'], list):
        for entry in registryEntry['hiddenServices']:
            if not os.path.exists(os.path.join(torDataDir, entry, "hostname")):
                print("Restarting Tor containers...")
                try:
                    os.system("docker restart app-tor app-2-tor app-3-tor")
                except:
                    print("Failed to restart Tor containers")
                    exit(1)
                print("Waiting for Tor containers to restart...")
                for i in range(60):
                    if os.path.exists(os.path.join(torDataDir, entry, "hostname")):
                        break
                    time.sleep(1)
                else:
                    print("Tor containers did not restart in time")
                    exit(1)
    update()
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    userData = getUserData()
    implements_service = False
    for virtual_app in virtual_apps.keys():
        implementations = virtual_apps[virtual_app]
        if args.app in implementations:
            for implementation in implementations:
                if "installedApps" in userData and implementation in userData["installedApps"]:
                    print("Another implementation of {} is already installed: {}. Uninstall it first to install this app.".format(virtual_app, implementation))
                    exit(1)
            implements_service = virtual_app
    createDataDir(args.app)
    compose(args.app, "pull")
    compose(args.app, "up --detach")
    setInstalled(args.app)
    if implements_service:
        setInstalled(implements_service)
    update()

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
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    implements_service = False
    for virtual_app in virtual_apps.keys():
        implementations = virtual_apps[virtual_app]
        if args.app in implementations:
            setRemoved(virtual_app)
    update()

elif args.action == 'stop':
    if not args.app:
        print("No app provided")
        exit(1)
    userData = getUserData()
    print("Stopping app {}...".format(args.app))
    compose(args.app, "rm --force --stop")
elif args.action == 'start':
    if not args.app:
        print("No app provided")
        exit(1)

    userData = getUserData()
    if not "installedApps" in userData or args.app not in userData["installedApps"]:
        print("App {} is not yet installed".format(args.app))
        exit(1)
    compose(args.app, "up --detach")

elif args.action == 'restart':
    if not args.app:
        print("No app provided")
        exit(1)

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

elif args.action == "get-ip":
    if args.app == "":
        print("Missing app")
        exit(1)
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    userData = getUserData()
    implements_service = False
    if args.app in virtual_apps:
        for implementation in virtual_apps[args.app]:
            if "installedApps" in userData and implementation in userData["installedApps"]:
                print(get_var_safe("APP_{}_SERVICE_IP".format(convert_to_upper(implementation))))
                exit(0)
    else:
        print("Not an virtual app")
        exit(1)

elif args.action == "get-implementation":
    if args.app == "":
        print("Missing app")
        exit(1)
    with open(os.path.join(appsDir, "virtual-apps.json"), "r") as f:
        virtual_apps = json.load(f)
    userData = getUserData()
    implements_service = False
    if args.app in virtual_apps:
        for implementation in virtual_apps[args.app]:
            if "installedApps" in userData and implementation in userData["installedApps"]:
                print(implementation)
                exit(0)
    else:
        print("Not an virtual app")
        exit(1)
    print("Virtual app not found")
    exit(1)
