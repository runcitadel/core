# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import yaml
import traceback

from lib.citadelutils import parse_dotenv
from lib.entropy import deriveEntropy

appPorts = {}
appPortMap = {}
disabledApps = []

def assignIpV4(appId: str, containerName: str):
    scriptDir = path.dirname(path.realpath(__file__))
    nodeRoot = path.join(scriptDir, "..", "..", "..", "..")
    networkingFile = path.join(nodeRoot, "apps", "networking.json")
    envFile = path.join(nodeRoot, ".env")
    cleanContainerName = containerName.strip()
    # If the name still contains a newline, throw an error
    if cleanContainerName.find("\n") != -1:
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        cleanContainerName.upper().replace("-", "_")
    )
    # Write a list of used IPs to the usedIpFile as JSON, and read that file to check if an IP
    # can be used
    usedIps = []
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)

    if 'ip_addresses' in networkingData:
        usedIps = list(networkingData['ip_addresses'].values())
    else:
        networkingData['ip_addresses'] = {}
    # An IP 10.21.21.xx, with x being a random number above 40 is asigned to the container
    # If the IP is already in use, it will be tried again until it's not in use
    # If it's not in use, it will be added to the usedIps list and written to the usedIpFile
    # If the usedIpsFile contains all IPs between  10.21.21.20 and  10.21.21.255 (inclusive),
    # Throw an error, because no more IPs can be used
    if len(usedIps) == 235:
        raise Exception("No more IPs can be used")

    if "{}-{}".format(appId, cleanContainerName) in networkingData['ip_addresses']:
        ip = networkingData['ip_addresses']["{}-{}".format(
            appId, cleanContainerName)]
    else:
        while True:
            ip = "10.21.21." + str(random.randint(20, 255))
            if ip not in usedIps:
                networkingData['ip_addresses']["{}-{}".format(
                    appId, cleanContainerName)] = ip
                break

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(ip):
        return

    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, ip))
    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)

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
                if version == 3:
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
                    internalPort = port
                    if isDynamic:
                        internalPort = newPort
                    #print("Port conflict! Moving app {}'s container {} to port {} (from {})".format(appId, containerName, newPort, port))
                    appPorts[newPort]  = {
                        "app": appId,
                        "port": internalPort,
                        "container": containerName,
                        "priority": priority,
                        "dynamic": isDynamic,
                    }

def getPortsV3App(app, appId):
    for appContainer in app["containers"]:
        assignIp(appId, appContainer["name"])
        if "port" in appContainer:
            if "preferredOutsidePort" in appContainer and "requiresPort" in appContainer and appContainer["requiresPort"]:
                validatePort(appContainer["name"], appContainer, appContainer["preferredOutsidePort"], appId, 2)
            elif "preferredOutsidePort" in appContainer:
            
                validatePort(appContainer["name"], appContainer, appContainer["preferredOutsidePort"], appId, 1)
            else:
                validatePort(appContainer["name"], appContainer, appContainer["port"], appId, 0)
        else:
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
        else:
            # if the container does not define a port, assume 3000, and pass it to the container as env var
            validatePort(appContainerName, appContainer, 3000, appId, 0, True)
        if "required_ports" in appContainer:
            if "tcp" in appContainer["required_ports"] and appContainer["required_ports"]["tcp"] != None:
                for port in appContainer["required_ports"]["tcp"].keys():
                    validatePort(appContainerName, appContainer, port, appId, 2)
            if "udp" in appContainer["required_ports"] and appContainer["required_ports"]["udp"] != None:
                for port in appContainer["required_ports"]["udp"].keys():
                    validatePort(appContainerName, appContainer, port, appId, 2)
