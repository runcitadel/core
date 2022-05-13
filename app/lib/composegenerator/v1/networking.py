# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from dacite import from_dict
from lib.composegenerator.v1.types import AppStage2, AppStage3, ContainerStage2, NetworkConfig
from lib.citadelutils import parse_dotenv
import json
from os import path
import random
from lib.composegenerator.v1.utils.networking import getContainerHiddenService, getFreePort, getHiddenService
import ipaddress


def assignIp(container: ContainerStage2, appId: str, networkingFile: str, envFile: str) -> ContainerStage2:
    ipv6Net = ipaddress.ip_network("fd9e:4a81::/32")
    # Strip leading/trailing whitespace from container.name
    container.name = container.name.strip()
    # If the name still contains a newline, throw an error
    if container.name.find("\n") != -1:
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
    )
    ipv6_env_var = "APP_{}_{}_IP6".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
    )
    # Write a list of used IPs to the usedIpFile as JSON, and read that file to check if an IP
    # can be used
    usedIps = []
    usedIpv6 = []
    # The first 100000 addresses are reserved for Citadel
    ip6Offset = 100000
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)

    if 'ip_addresses' in networkingData:
        usedIps = list(networkingData['ip_addresses'].values())
    else:
        networkingData['ip_addresses'] = {}
    if 'ip6_addresses' in networkingData:
        usedIpv6 = list(networkingData['ip6_addresses'].values())
    else:
        networkingData['ip6_addresses'] = {}
    if 'ip6Offset' in networkingData:
        ip6Offset = int(networkingData['ip6Offset'])
    else:
        networkingData['ip6Offset'] = 100000
    # An IP 10.21.21.xx, with x being a random number above 40 is assigned to the container
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
    if "{}-{}".format(appId, container.name) in networkingData['ip6_addresses']:
        ip6 = networkingData['ip6_addresses']["{}-{}".format(
            appId, container.name)]
    else:
        networkingData['ip6Offset'] += 1
        ip6 = ipv6Net[networkingData['ip6Offset']]
    container.networks = from_dict(data_class=NetworkConfig, data={'default': {
        'ipv4_address': "$" + env_var}, 'ipv6': {
        'ipv6_address': "$" + ipv6_env_var}})

    dotEnv = parse_dotenv(envFile)
    if not (env_var in dotEnv and str(dotEnv[env_var]) == str(ip)):
        # Now append a new line  with APP_{app_name}_{container_name}_IP=${IP} to the envFile
        with open(envFile, 'a') as f:
            f.write("{}={}\n".format(env_var, ip))
        with open(networkingFile, 'w') as f:
            json.dump(networkingData, f)
    if not (ipv6_env_var in dotEnv and str(dotEnv[ipv6_env_var]) == str(ipv6_ip)):
        # Now append a new line  with APP_{app_name}_{container_name}_IP=${IP} to the envFile
        with open(envFile, 'a') as f:
            f.write("{}={}\n".format(ipv6_env_var, ip6))
        with open(networkingFile, 'w') as f:
            json.dump(networkingData, f)
    return container


def assignPort(container: dict, appId: str, networkingFile: str, envFile: str):
    # Strip leading/trailing whitespace from container.name
    container.name = container.name.strip()
    # If the name still contains a newline, throw an error
    if container.name.find("\n") != -1 or container.name.find(" ") != -1:
        raise Exception("Newline or space in container name")

    env_var = "APP_{}_{}_PORT".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
    )

    port = getFreePort(networkingFile, appId)

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(port):
        return {"port": port, "env_var": "${{{}}}".format(env_var)}

    # Now append a new line  with APP_{app_name}_{container_name}_PORT=${PORT} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, port))

    # This is confusing, but {{}} is an escaped version of {} so it is ${{ {} }}
    # where the outer {{ }} will be replaced by {} in the returned string
    return {"port": port, "env_var": "${{{}}}".format(env_var)}


def getMainContainer(app: dict):
    if len(app.containers) == 1:
        return app.containers[0]
    else:
        if not app.metadata.mainContainer:
            app.metadata.mainContainer = 'main'
        for container in app.containers:
            if container.name == app.metadata.mainContainer:
                return container
    raise Exception(
        "No main container found for app {}".format(app.metadata.name))


def configureMainPort(app: AppStage2, nodeRoot: str) -> AppStage3:
    registryFile = path.join(nodeRoot, "apps", "registry.json")
    registry: list = []
    if path.isfile(registryFile):
        with open(registryFile, 'r') as f:
            registry = json.load(f)
    else:
        raise Exception("Registry file not found")

    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))

    mainContainer = getMainContainer(app)

    portDetails = assignPort(mainContainer, app.metadata.id, path.join(
        nodeRoot, "apps", "networking.json"), path.join(nodeRoot, ".env"))
    containerPort = portDetails['port']
    portAsEnvVar = portDetails['env_var']
    portToAppend = portAsEnvVar

    mainPort = False

    if mainContainer.port:
        portToAppend = "{}:{}".format(portAsEnvVar, mainContainer.port)
        mainPort = mainContainer.port
        del mainContainer.port
    else:
        portToAppend = "{}:{}".format(portAsEnvVar, portAsEnvVar)

    if mainContainer.ports:
        mainContainer.ports.append(portToAppend)
        # Set the main port to the first port in the list, if it contains a :, it's the port after the :
        # If it doesn't contain a :, it's the port itself
        if mainPort == False:
            mainPort = mainContainer.ports[0]
            if mainPort.find(":") != -1:
                mainPort = mainPort.split(":")[1]
    else:
        mainContainer.ports = [portToAppend]
        if mainPort == False:
            mainPort = portDetails['port']

    mainContainer = assignIp(mainContainer, app.metadata.id, path.join(
        nodeRoot, "apps", "networking.json"), path.join(nodeRoot, ".env"))

    # If the IP wasn't in dotenv before, now it should be
    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))

    containerIP = dotEnv['APP_{}_{}_IP'.format(app.metadata.id.upper().replace(
        "-", "_"), mainContainer.name.upper().replace("-", "_"))]

    hiddenservice = getHiddenService(
        app.metadata.name, app.metadata.id, containerIP, mainPort)

    torDaemons = ["torrc-apps", "torrc-apps-2", "torrc-apps-3"]
    torFileToAppend = torDaemons[random.randint(0, len(torDaemons) - 1)]
    with open(path.join(nodeRoot, "tor", torFileToAppend), 'a') as f:
        f.write(hiddenservice)

    # Also set the port in metadata
    app.metadata.port = int(containerPort)

    for registryApp in registry:
        if registryApp['id'] == app.metadata.id:
            registry[registry.index(registryApp)]['port'] = int(containerPort)
            break

    with open(registryFile, 'w') as f:
        json.dump(registry, f, indent=4, sort_keys=True)

    return app


def configureIps(app: AppStage2, networkingFile: str, envFile: str):
    for container in app.containers:
        if container.noNetwork:
            # Check if port is defined for the container
            if container.port:
                raise Exception("Port defined for container without network")
            if app.metadata.mainContainer == container.name:
                raise Exception("Main container without network")
            # Skip this iteration of the loop
            continue

        container = assignIp(container, app.metadata.id,
                             networkingFile, envFile)

    return app


def configureHiddenServices(app: dict, nodeRoot: str) -> None:
    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))
    hiddenServices = ""

    if len(app.containers) == 1:
        mainContainer = app.containers[0]
    else:
        mainContainer = None
        if app.metadata.mainContainer == None:
            app.metadata.mainContainer = 'main'
        for container in app.containers:
            if container.name == app.metadata.mainContainer:
                mainContainer = container
                break
        if mainContainer is None:
            raise Exception("No main container found")

    for container in app.containers:
        env_var = "APP_{}_{}_IP".format(
            app.metadata.id.upper().replace("-", "_"),
            container.name.upper().replace("-", "_")
        )
        hiddenServices += getContainerHiddenService(
            app.metadata.name, app.metadata.id, container, dotEnv[env_var], container.name == mainContainer.name)

    torDaemons = ["torrc-apps", "torrc-apps-2", "torrc-apps-3"]
    torFileToAppend = torDaemons[random.randint(0, len(torDaemons) - 1)]
    with open(path.join(nodeRoot, "tor", torFileToAppend), 'a') as f:
        f.write(hiddenServices)
