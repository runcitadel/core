# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lib.composegenerator.v3.types import App, AppStage2, AppStage3, Container
from lib.citadelutils import parse_dotenv
import json
from os import path
import random
from lib.composegenerator.v1.networking import assignIp, assignPort


def getMainContainer(app: App) -> Container:
    if len(app.containers) == 1:
        return app.containers[0]
    else:
        for container in app.containers:
            # Main is recommended, support web for easier porting from Umbrel
            if container.name == 'main' or container.name == 'web':
                return container
        for container in app.containers:
            # Also allow names to start with main
            if container.name.startswith("main") and not container.ignored:
                return container
    # Fallback to first container
    return app.containers[0]


def configureMainPort(app: AppStage2, nodeRoot: str) -> AppStage3:
    registryFile = path.join(nodeRoot, "apps", "registry.json")
    portsFile = path.join(nodeRoot, "apps", "ports.json")
    envFile = path.join(nodeRoot, ".env")
    registry: list = []
    ports = {}
    if path.isfile(registryFile):
        with open(registryFile, 'r') as f:
            registry = json.load(f)
    else:
        raise Exception("Registry file not found")
    if path.isfile(portsFile):
        with open(portsFile, 'r') as f:
            ports = json.load(f)
    else:
        raise Exception("Ports file not found")

    mainContainer = getMainContainer(app)

    portAsEnvVar = "APP_{}_{}_PORT".format(
        app.metadata.id.upper().replace("-", "_"),
        mainContainer.name.upper().replace("-", "_")
    )
    portToAppend = portAsEnvVar

    mainPort = False
    containerPort = False

    if mainContainer.port:
        portToAppend = "${{{}}}:{}".format(portAsEnvVar, mainContainer.port)
        mainPort = mainContainer.port
        for port in ports[app.metadata.id][mainContainer.name]:
            if str(port["internalPort"]) == str(mainPort):
                containerPort = port["publicPort"]
        del mainContainer.port
    elif not mainContainer.requiredPorts:
        for port in ports[app.metadata.id][mainContainer.name]:
            if port["dynamic"]:
                mainPort = port["internalPort"]
                containerPort = port["publicPort"]
        portToAppend = "${{{}}}:${{{}}}".format(portAsEnvVar, portAsEnvVar)

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
            registry[registry.index(registryApp)]['port'] = containerPort
            registry[registry.index(registryApp)]['internalPort'] = app.metadata.internalPort
            break

    with open(registryFile, 'w') as f:
        json.dump(registry, f, indent=4, sort_keys=True)

    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(portAsEnvVar, app.metadata.port))
    return app

