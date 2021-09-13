#!/usr/bin/env python3

import yaml
import json
from lib.composegenerator.v0.generate import createComposeConfigFromV0
from lib.composegenerator.v1.generate import createComposeConfigFromV1
from lib.appymlgenerator import convertComposeYMLToAppYML
from lib.validate import findAndValidateApps
from lib.metadata import getAppRegistry, getSimpleAppRegistry
import os
import argparse
import requests
from sys import argv

# Print an error if user is not root
if os.getuid() != 0:
  print('This script must be run as root!')
  exit(1)

# The directory with this script
scriptDir = os.path.dirname(os.path.realpath(__file__))
nodeRoot = os.path.join(scriptDir, "..")
appsDir = os.path.join(nodeRoot, "apps")

parser = argparse.ArgumentParser(description="Manage apps on your Citadel")
parser.add_argument('action', help='What to do with the app database either list, download, update or update-online.')
parser.add_argument('--invoked-by-configure', action='store_true')
args = parser.parse_args()

# Returns a list of every argument after the second one in sys.argv joined into a string by spaces
def getArguments():
    arguments = ""
    for i in range(3, len(argv)):
        arguments += argv[i] + " "
    return arguments

# If no action is specified, the list action is used
if args.action is None:
    args.action = 'list'

def getAppYml(name):
    url = 'https://raw.githubusercontent.com/runcitadel/compose-nonfree/main/apps/' + name + '/' + 'app.yml'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return False

def getAppYmlPath(app):
    return os.path.join(appsDir, app, 'app.yml')

def composeToAppYml(app):
    composeFile = os.path.join(appsDir, app, "docker-compose.yml")
    appYml = os.path.join(appsDir, app, "app.yml")
    # Read the compose file and parse it
    with open(composeFile, "r") as f:
        compose = yaml.safe_load(f)
    registry = os.path.join(appsDir, "registry.json")
    # Load the registry
    with open(registry, "r") as f:
        registryData = json.load(f)
    converted = convertComposeYMLToAppYML(compose, app, registryData)
    # Put converted into the app.yml after encoding it as YAML
    with open(appYml, "w") as f:
        f.write(yaml.dump(converted, sort_keys=False))
    


def update():
    apps = findAndValidateApps(appsDir)
    # The compose generation process updates the registry, so we need to get it set up with the basics before that
    registry = getAppRegistry(apps, appsDir)
    with open(os.path.join(appsDir, "registry.json"), "w") as f:
        json.dump(registry, f, indent=4, sort_keys=True)
    print("Wrote registry to registry.json")

    simpleRegistry = getSimpleAppRegistry(apps, appsDir)
    with open(os.path.join(appsDir, "apps.json"), "w") as f:
        json.dump(simpleRegistry, f, indent=4, sort_keys=True)
    print("Wrote simple registry to apps.json")
    
    # Loop through the apps and generate valid compose files from them, then put these into the app dir
    for app in apps:
        composeFile = os.path.join(appsDir, app, "docker-compose.yml")
        appYml = os.path.join(appsDir, app, "app.yml")
        with open(composeFile, "w") as f:
            appCompose = getApp(appYml, app)
            if(appCompose):
                f.write(yaml.dump(appCompose, sort_keys=False))
    print("Generated configuration successfully")

def download():
    if(args.app is None):
        apps = findAndValidateApps(appsDir)
        for app in apps:
            data = getAppYml(app)
            if data:
                with open(getAppYmlPath(app), 'w') as f:
                    f.write(data)
            else:
                print("Warning: Could not download " + app)
    else:
        data = getAppYml(args.app)
        if data:
            with open(getAppYmlPath(args.app), 'w') as f:
                f.write(data)
        else:
            print("Warning: Could not download " + args.app)

# Loads an app.yml and converts it to a docker-compose.yml
def getApp(appFile: str, appId: str):
    with open(appFile, 'r') as f:
        app = yaml.safe_load(f)

    if not "metadata" in app:
        raise Exception("Error: Could not find metadata in " + appFile)
    app["metadata"]["id"] = appId
                
    if('version' in app and str(app['version']) == "1"):
        return createComposeConfigFromV1(app, nodeRoot)
    else:
        return createComposeConfigFromV0(app)

def compose(app, arguments):
    # Runs a compose command in the app dir
    # Before that, check if a docker-compose.yml exists in the app dir
    composeFile = os.path.join(appsDir, app, "docker-compose.yml")
    if not os.path.isfile(composeFile):
        print("Error: Could not find docker-compose.yml in " + app)
        exit(1)
    # Save the previous working directory and return to it later
    oldDir = os.getcwd()
    os.chdir(os.path.join(nodeRoot, "apps", app))
    os.system("docker compose --env-file '{}' {}".format(os.path.join(nodeRoot, ".env"), arguments))
    os.chdir(oldDir)

if args.action == 'list':
    apps = findAndValidateApps(appsDir)
    for app in apps:
        print(app)
    exit(0)
elif args.action == 'download':
    download()
    exit(0)     
elif args.action == 'update':
    if(args.invoked_by_configure):
        update()
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app_tor")
        os.system("docker compose start app_tor")
        os.system("docker compose stop app_2_tor")
        os.system("docker compose start app_2_tor")
    exit(0)
elif args.action == 'update-online':
    download()
    if(args.invoked_by_configure):
        update()
    else:
        os.system(os.path.join(nodeRoot, "scripts", "configure"))
        os.chdir(nodeRoot)
        os.system("docker compose stop app_tor")
        os.system("docker compose start app_tor")
        os.system("docker compose stop app_2_tor")
        os.system("docker compose start app_2_tor")
    exit(0)
#elif args.action == 'compose-to-app':
    #apps = findApps(appsDir)
    #for app in apps:
        #composeToAppYml(app)
    #exit(0)
else:
    print("Error: Unknown action")
    print("See --help for usage")
    exit(1)
