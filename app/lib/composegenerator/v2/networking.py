# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lib.composegenerator.v2.types import App, AppStage2, AppStage3, Container
from lib.citadelutils import parse_dotenv
import json
from os import path
import random
from lib.composegenerator.v2.utils.networking import getContainerHiddenService
from lib.composegenerator.v1.networking import assignIp, assignPort


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

        container = assignIp(container, app.metadata.id,
                             networkingFile, envFile)

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
