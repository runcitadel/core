# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from os import path
import random
from lib.composegenerator.shared.utils.networking import getContainerHiddenService
from lib.composegenerator.v2.types import AppStage2, AppStage3, ContainerStage2, NetworkConfig, App, Container
from lib.citadelutils import parse_dotenv
from dacite import from_dict

def getMainContainer(app: App) -> Container:
    if len(app.containers) == 1:
        return app.containers[0]
    else:
        for container in app.containers:
            # Main is recommended, support web for easier porting from Umbrel
            if container.name == 'main' or container.name == 'web':
                return container
    # Fallback to first container
    return app.containers[0]

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

def assignIp(container: ContainerStage2, appId: str) -> ContainerStage2:
    scriptDir = path.dirname(path.realpath(__file__))
    nodeRoot = path.join(scriptDir, "..", "..", "..", "..")
    networkingFile = path.join(nodeRoot, "apps", "networking.json")
    envFile = path.join(nodeRoot, ".env")
    # Strip leading/trailing whitespace from container.name
    container.name = container.name.strip()
    # If the name still contains a newline, throw an error
    if container.name.find("\n") != -1:
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
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

    if "{}-{}".format(appId, container.name) in networkingData['ip_addresses']:
        ip = networkingData['ip_addresses']["{}-{}".format(
            appId, container.name)]
    else:
        while True:
            ip = "10.21.21." + str(random.randint(20, 255))
            if ip not in usedIps:
                networkingData['ip_addresses']["{}-{}".format(
                    appId, container.name)] = ip
                break
    container.networks = from_dict(data_class=NetworkConfig, data={'default': {
        'ipv4_address': "$" + env_var}})

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(ip):
        return container

    # Now append a new line  with APP_{app_name}_{container_name}_IP=${IP} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, ip))
    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)
    return container

def configureIps(app: AppStage2, networkingFile: str, envFile: str):
    for container in app.containers:
        if container.network_mode and container.network_mode == "host":
            continue
        if container.noNetwork:
            # Check if port is defined for the container
            if container.port:
                raise Exception("Port defined for container without network")
            if getMainContainer(app).name == container.name:
                raise Exception("Main container without network")
            # Skip this iteration of the loop
            continue

        container = assignIp(container, app.metadata.id)

    return app

def configureHiddenServices(app: AppStage3, nodeRoot: str) -> AppStage3:
    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))
    hiddenServices = ""

    mainContainer = getMainContainer(app)

    for container in app.containers:
        if container.network_mode and container.network_mode == "host":
            continue
        env_var = "APP_{}_{}_IP".format(
            app.metadata.id.upper().replace("-", "_"),
            container.name.upper().replace("-", "_")
        )
        hiddenServices += getContainerHiddenService(
            app.metadata, container, dotEnv[env_var], container.name == mainContainer.name)
        if container.hiddenServicePorts:
            del container.hiddenServicePorts

    torDaemons = ["torrc-apps", "torrc-apps-2", "torrc-apps-3"]
    torFileToAppend = torDaemons[random.randint(0, len(torDaemons) - 1)]
    with open(path.join(nodeRoot, "tor", torFileToAppend), 'a') as f:
        f.write(hiddenServices)
    return app
