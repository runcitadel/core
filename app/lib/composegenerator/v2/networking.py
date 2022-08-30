# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lib.citadelutils import parse_dotenv
from lib.composegenerator.v2.types import App, AppStage2, AppStage3, Container
import json
from os import path
import os
import random
from lib.composegenerator.shared.networking import assignIp

def getFreePort(networkingFile: str, appId: str):
    # Ports used currently in Citadel
    usedPorts = [
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
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)
    if 'ports' in networkingData:
        usedPorts += list(networkingData['ports'].values())
    else:
        networkingData['ports'] = {}

    if appId in networkingData['ports']:
        return networkingData['ports'][appId]

    while True:
        port = str(random.randint(1024, 49151))
        if port not in usedPorts:
            # Check if anyhing is listening on the specific port
            if os.system("netstat -ntlp | grep " + port + " > /dev/null") != 0:
                networkingData['ports'][appId] = port
                break

    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)

    return port

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


def configureMainPort(app: AppStage2, nodeRoot: str) -> AppStage3:
    registryFile = path.join(nodeRoot, "apps", "registry.json")
    registry: list = []
    if path.isfile(registryFile):
        with open(registryFile, 'r') as f:
            registry = json.load(f)
    else:
        raise Exception("Registry file not found")

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

    if mainContainer.network_mode != "host":
        mainContainer = assignIp(mainContainer, app.metadata.id, path.join(
            nodeRoot, "apps", "networking.json"), path.join(nodeRoot, ".env"))

    # Also set the port in metadata
    app.metadata.port = int(containerPort)
    if mainPort:
        app.metadata.internalPort = int(mainPort)
    else:
        app.metadata.internalPort = int(containerPort)

    for registryApp in registry:
        if registryApp['id'] == app.metadata.id:
            registry[registry.index(registryApp)]['port'] = int(containerPort)
            registry[registry.index(registryApp)]['internalPort'] = app.metadata.internalPort
            break

    with open(registryFile, 'w') as f:
        json.dump(registry, f, indent=4, sort_keys=True)

    return app
