# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import yaml

from lib.composegenerator.next.stage1 import createCleanConfigFromV3
from lib.composegenerator.v2.networking import getMainContainer
from lib.composegenerator.v1.networking import getFreePort
from lib.entropy import deriveEntropy
from typing import List
import json
import random

appPorts = {}
appPortMap = {}
disabledApps = []

def appPortsToMap():
    for port in appPorts:
        appId = appPorts[port]["app"]
        containerId = appPorts[port]["container"]
        realPort = appPorts[port]["port"]
        if not appId in appPortMap:
            appPortMap[appId] = {}
        if not containerId in appPortMap[appId]:
            appPortMap[appId][containerId] = []
        appPortMap[appId][containerId].append({
            "publicPort": port,
            "internalPort": realPort,
            "dynamic": appPorts[port]["dynamic"]
        })
        
# For every app, parse the app.yml in ../apps/[name] and
# check their metadata, and return a list of all app's metadata
# Also check the path and defaultPassword and set them to an empty string if they don't exist
# In addition, set id on the metadata to the name of the app
# Return a list of all app's metadata
def getAppRegistry(apps, app_path):
    app_metadata = []
    for app in apps:
        app_yml_path = os.path.join(app_path, app, 'app.yml')
        app_cache_path = os.path.join(app_path, app, 'app.cache.json')
        if os.path.isfile(app_yml_path):
            try:
                with open(app_yml_path, 'r') as f:
                    app_yml = yaml.safe_load(f.read())
                metadata: dict = app_yml['metadata']
                metadata['id'] = app
                metadata['path'] = metadata.get('path', '')
                metadata['defaultPassword'] = metadata.get('defaultPassword', '')
                if metadata['defaultPassword'] == "$APP_SEED":
                    metadata['defaultPassword'] = deriveEntropy("app-{}-seed".format(app))
                if "mainContainer" in metadata:
                    metadata.pop("mainContainer")
                app_metadata.append(metadata)
                if(app_yml["version"] != 3):
                    getPortsOldApp(app_yml, app)
                else:
                    getPortsV3App(app_yml, app)
                    with open(app_cache_path, 'w') as f:
                        json.dump(createCleanConfigFromV3(app_yml, os.path.dirname(app_path)), f)
            except Exception as e:
                print(e)
                print("App {} is invalid!".format(app))
    appPortsToMap()
    return {
        "metadata": app_metadata,
        "ports": appPortMap
    }

citadelPorts = [
    # Dashboard
    80,
    # Sometimes used by nginx with some setups
    433,
    # Dashboard SSL
    443,
    # Bitcoin Core P2P
    8333,
    # LND gRPC
    10009,
    # LND REST
    8080,
    # Electrum Server
    50001,
    # Tor Proxy
    9050,
]

lastPort = 3000

def getNewPort(usedPorts):
    lastPort2 = lastPort
    while lastPort2 in usedPorts or lastPort2 in citadelPorts:
        lastPort2 = lastPort2 + 1
    return lastPort2

def validatePort(appContainer, port, appId, priority: int, isDynamic = False): 
    if port not in appPorts and port not in citadelPorts and port != 0:
        appPorts[port] = {
            "app": appId,
            "port": port,
            "container": appContainer["name"],
            "priority": priority,
            "dynamic": isDynamic,
        }
    else:
        if port in citadelPorts or appPorts[port]["app"] != appId or appPorts[port]["container"] != appContainer["name"]:
            newPort = getNewPort(appPorts.keys())
            if port in appPorts and priority > appPorts[port]["priority"]:
                #print("Prioritizing app {} over {}".format(appId, appPorts[port]["app"]))
                appPorts[newPort] = appPorts[port].copy()
                appPorts[port]  = {
                    "app": appId,
                    "port": port,
                    "container": appContainer["name"],
                    "priority": priority,
                    "dynamic": isDynamic,
                }
            else:
                if "requiresPort" in appContainer and appContainer["requiresPort"]:
                    disabledApps.append(appId)
                    print("App {} disabled because of port conflict".format(appId))
                else:
                    #print("Port conflict! Moving app {}'s container {} to port {} (from {})".format(appId, appContainer["name"], newPort, port))
                    appPorts[newPort]  = {
                        "app": appId,
                        "port": port,
                        "container": appContainer["name"],
                        "priority": priority,
                        "dynamic": isDynamic,
                    }

def getPortsOldApp(app, appId):
    for appContainer in app["containers"]:
        if "port" in appContainer:
            validatePort(appContainer, appContainer["port"], appId, 0)
        if "ports" in appContainer:
            for port in appContainer["ports"]:
                realPort = int(str(port).split(":")[0])
                validatePort(appContainer, realPort, appId, 2)


def getPortsV3App(app, appId):
    for appContainer in app["containers"]:
        if "port" in appContainer:
            if "preferredOutsidePort" in appContainer and "requiresPort" in appContainer and appContainer["requiresPort"]:
                validatePort(appContainer, appContainer["preferredOutsidePort"], appId, 2)
            elif "preferredOutsidePort" in appContainer:
            
                validatePort(appContainer, appContainer["preferredOutsidePort"], appId, 1)
            else:
                validatePort(appContainer, appContainer["port"], appId, 0)
        elif "requiredPorts" not in appContainer and "requiredUdpPorts" not in appContainer:
                validatePort(appContainer, getNewPort(appPorts.keys()), appId, 0, True)
        if "requiredPorts" in appContainer:
            for port in appContainer["requiredPorts"]:
                validatePort(appContainer, port, appId, 2)
        if "requiredUdpPorts" in appContainer:
            for port in appContainer["requiredUdpPorts"]:
                validatePort(appContainer, port, appId, 2)