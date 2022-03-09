#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from typing import List
import yaml
import os
import argparse

# Print an error if user is not root
if os.getuid() != 0:
    print('This script must be run as root!')
    exit(1)

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..")

parser = argparse.ArgumentParser(description="Manage services on your Citadel")
parser.add_argument('action', help='What to do with the service.', choices=["set", "uninstall", "setup"])
parser.add_argument('--verbose', '-v', action='store_true')
parser.add_argument(
    'service', help='The service to perform an action on.', nargs='?')
parser.add_argument(
    'implementation', help='The service to perform an action on.', nargs='?')
args = parser.parse_args()

# Function to install a service
# To install it, read the service's YAML file (nodeRoot/services/name.yml) and add it to the main compose file (nodeRoot/docker-compose.yml)
def setService(name, implementation):
    # Read the YAML file
    with open(os.path.join(nodeRoot, "services", name, implementation + ".yml"), 'r') as stream:
        service = yaml.safe_load(stream)

    # Read the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'r') as stream:
        compose = yaml.safe_load(stream)

    # Add the service to the main compose file
    compose['services'].update(service)

    # Write the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'w') as stream:
        yaml.dump(compose, stream, sort_keys=False)
    # Save the service name in nodeRoot/services/installed.json, which is a JSON file with a list of installed services
    # If the file doesn't exist, put [] in it, then run the code below
    try:
        with open(os.path.join(nodeRoot, "services", "installed.yaml"), 'r') as stream:
            installed = yaml.safe_load(stream)
    except FileNotFoundError:
        installed = {}
    installed[name] = implementation
    with open(os.path.join(nodeRoot, "services", "installed.yaml"), 'w') as stream:
        yaml.dump(installed, stream, sort_keys=False)


def uninstallService(name):
    # First check if a service yml definition exists to avoid uninstalling something that can't be installed or isn't supposed to be removed
    if not os.path.isdir(os.path.join(nodeRoot, "services", name)):
        print("Service definition not found, cannot uninstall")
        exit(1)
    # Read the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'r') as stream:
        compose = yaml.safe_load(stream)

    # Remove the service from the main compose file
    try:
        del compose['services'][name]
    except KeyError:
        pass

    # Write the main compose file
    with open(os.path.join(nodeRoot, "docker-compose.yml"), 'w') as stream:
        yaml.dump(compose, stream, sort_keys=False)
    # Save the service name in nodeRoot/services/installed.json, which is a JSON file with a list of installed services
    try:
        with open(os.path.join(nodeRoot, "services", "installed.yaml"), 'r') as stream:
            installed = yaml.safe_load(stream)
    except FileNotFoundError:
        installed = {}
    try:
        del installed[name]
    except KeyError:
        pass
    with open(os.path.join(nodeRoot, "services", "installed.yaml"), 'w') as stream:
        yaml.dump(installed, stream, sort_keys=False)

# install all services from installed.json
def installServices():
    try:
        with open(os.path.join(nodeRoot, "services", "installed.json"), 'r') as stream:
            installed: List[str] = yaml.safe_load(stream)
    except FileNotFoundError:
        installed: List[str] = []
    for service in installed:
        installService(service)
    


if args.action == "set":
    setService(args.service, args.implementation)
elif args.action == "uninstall":
    uninstallService(args.service)
elif args.action == "setup":
    installServices()
    