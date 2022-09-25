# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import yaml
import traceback

from lib.composegenerator.shared.networking import assignIp, assignIpV4
from lib.composegenerator.v2.types import Container
from lib.entropy import deriveEntropy
from dacite import from_dict

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
def getAppRegistry(apps, app_path, portCache):
    app_metadata = []
    virtual_apps = {}
    appPorts = portCache
    for app in apps:
        app_yml_path = os.path.join(app_path, app, 'app.yml')
        if os.path.isfile(app_yml_path):
            try:
                with open(app_yml_path, 'r') as f:
                    app_yml = yaml.safe_load(f.read())
                version = False
                if 'version' in app_yml:
                    version = int(app_yml['version'])
                elif 'citadel_version' in app_yml:
                    version = int(app_yml['citadel_version'])
                metadata: dict = app_yml['metadata']
                metadata['id'] = app
                metadata['path'] = metadata.get('path', '')
                metadata['defaultPassword'] = metadata.get('defaultPassword', '')
                if metadata['defaultPassword'] == "$APP_SEED":
                    metadata['defaultPassword'] = deriveEntropy("app-{}-seed".format(app))
                if "mainContainer" in metadata:
                    metadata.pop("mainContainer")
                if "implements" in metadata:
                    implements = metadata["implements"]
                    if implements not in virtual_apps:
                        virtual_apps[implements] = []
                    virtual_apps[implements].append(app)
                app_metadata.append(metadata)
                if version == 2:
                    getPortsV2App(app_yml, app)
                elif version == 3:
                    getPortsV3App(app_yml, app)
                elif version == 4:
                    getPortsV4App(app_yml, app)
            except Exception as e:
                print(traceback.format_exc())
                print("App {} is invalid!".format(app))
    appPortsToMap()
    return {
        "virtual_apps": virtual_apps,
        "metadata": app_metadata,
        "ports": appPortMap,
        "portCache": appPorts,
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

def getNewPort(usedPorts, appId, containerName, allowExisting):
    lastPort2 = lastPort
    while lastPort2 in usedPorts.keys() or lastPort2 in citadelPorts:
        if allowExisting and lastPort2 in usedPorts.keys() and usedPorts[lastPort2]["app"] == appId and usedPorts[lastPort2]["container"] == containerName:
            break
        lastPort2 = lastPort2 + 1
    return lastPort2

def validatePort(containerName, appContainer, port, appId, priority: int, isDynamic = False): 
    if port not in appPorts and port not in citadelPorts and port != 0:
        appPorts[port] = {
            "app": appId,
            "port": port,
            "container": containerName,
            "priority": priority,
            "dynamic": isDynamic,
        }
    else:
        if port in citadelPorts or appPorts[port]["app"] != appId or appPorts[port]["container"] != containerName:
            if port in appPorts and priority > appPorts[port]["priority"]:
                #print("Prioritizing app {} over {}".format(appId, appPorts[port]["app"]))
                newPort = getNewPort(appPorts, appPorts[port]["app"], appPorts[port]["container"], False)
                appPorts[newPort] = appPorts[port].copy()
                appPorts[port]  = {
                    "app": appId,
                    "port": port,
                    "container": containerName,
                    "priority": priority,
                    "dynamic": isDynamic,
                }
            else:
                if "requiresPort" in appContainer and appContainer["requiresPort"]:
                    disabledApps.append(appId)
                    print("App {} disabled because of port conflict".format(appId))
                else:
                    newPort = getNewPort(appPorts, appId, containerName, True)
                    #print("Port conflict! Moving app {}'s container {} to port {} (from {})".format(appId, containerName, newPort, port))
                    appPorts[newPort]  = {
                        "app": appId,
                        "port": port,
                        "container": containerName,
                        "priority": priority,
                        "dynamic": isDynamic,
                    }

def getPortsV2App(app, appId):
    for appContainer in app["containers"]:
        if "port" in appContainer:
            validatePort(appContainer["name"], appContainer, appContainer["port"], appId, 0)
        if "ports" in appContainer:
            for port in appContainer["ports"]:
                realPort = int(str(port).split(":")[0])
                validatePort(appContainer["name"], appContainer, realPort, appId, 2)


def getPortsV3App(app, appId):
    for appContainer in app["containers"]:
        containerAsDataClass = from_dict(data_class=Container, data=appContainer)
        assignIp(containerAsDataClass, appId)
        if "port" in appContainer:
            if "preferredOutsidePort" in appContainer and "requiresPort" in appContainer and appContainer["requiresPort"]:
                validatePort(appContainer["name"], appContainer, appContainer["preferredOutsidePort"], appId, 2)
            elif "preferredOutsidePort" in appContainer:
            
                validatePort(appContainer["name"], appContainer, appContainer["preferredOutsidePort"], appId, 1)
            else:
                validatePort(appContainer["name"], appContainer, appContainer["port"], appId, 0)
        elif "requiredPorts" not in appContainer and "requiredUdpPorts" not in appContainer:
                # if the container does not define a port, assume 3000, and pass it to the container as env var
                validatePort(appContainer["name"], appContainer, 3000, appId, 0, True)
        if "requiredPorts" in appContainer:
            for port in appContainer["requiredPorts"]:
                validatePort(appContainer["name"], appContainer, port, appId, 2)
        if "requiredUdpPorts" in appContainer:
            for port in appContainer["requiredUdpPorts"]:
                validatePort(appContainer["name"], appContainer, port, appId, 2)

def getPortsV4App(app, appId):
    for appContainerName in app["services"].keys():
        appContainer = app["services"][appContainerName]
        if "enable_networking" in appContainer and not appContainer["enable_networking"]:
            return
        assignIpV4(appId, appContainerName)
        if "port" in appContainer:
            validatePort(appContainerName, appContainer, appContainer["port"], appId, 0)
        if "required_ports" in appContainer:
            if "tcp" in appContainer["required_ports"]:
                for port in appContainer["required_ports"]["tcp"].keys():
                    validatePort(appContainerName, appContainer, port, appId, 2)
            if "udp" in appContainer["required_ports"]:
                for port in appContainer["required_ports"]["udp"].keys():
                    validatePort(appContainerName, appContainer, port, appId, 2)
