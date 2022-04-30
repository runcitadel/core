# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from lib.citadelutils import classToDict
from lib.composegenerator.shared.main import convertDataDirToVolume, convertContainersToServices
from lib.composegenerator.shared.env import validateEnv
from lib.composegenerator.v2.networking import configureIps, configureHiddenServices

from lib.composegenerator.v3.types import App, AppStage2, AppStage4, generateApp
from lib.composegenerator.v3.networking import configureMainPort
from lib.composegenerator.shared.const import permissions


def convertContainerPermissions(app: App) -> App:
    for container in app.containers:
        for permission in app.metadata.dependencies:
            if isinstance(permission, str):
                if permission in permissions():
                    container.environment_allow.extend(permissions()[permission]['environment_allow'])
                    container.volumes.extend(permissions()[permission]['volumes'])
                else:
                    print("Warning: app {} defines unknown permission {}".format(app.metadata.name, permission))
            else:
                for subPermission in permission:
                    if subPermission in permissions():
                        container.environment_allow.extend(permissions()[subPermission]['environment_allow'])
                        container.volumes.extend(permissions()[subPermission]['volumes'])
                    else:
                        print("Warning: app {} defines unknown permission {}".format(app.metadata.name, subPermission))
    return app

def convertDataDirToVolumeGen3(app: App) -> AppStage2:
    for container in app.containers:
        # Loop through data dirs in container.data, if they don't contain a .., add them to container.volumes
        # Also, a datadir shouldn't start with a /
        for dataDir in container.data:
            if dataDir.find("..") == -1 and dataDir[0] != "/":
                container.volumes.append(
                    '${APP_DATA_DIR}/' + dataDir)
            else:
                print("Data dir " + dataDir +
                        " contains invalid characters")
        del container.data
    for container in app.containers:
        if container.mounts:
            if container.mounts.lnd:
                if not 'lnd' in app.metadata.dependencies:
                    print("Warning: container {} of app {} defines lnd mount dir but doesn't request lnd permission".format(container.name, app.metadata.name))
                    # Skip this container
                    continue
                # Also skip the container if container.mounts.lnd contains a :
                if container.mounts.lnd.find(":") == -1:
                    container.volumes.append('${LND_DATA_DIR}:' + container.mounts.lnd)
            if container.mounts.bitcoin:
                if not 'bitcoind' in app.metadata.dependencies:
                    print("Warning: container {} of app {} defines lnd mount dir but doesn't request lnd permission".format(container.name, app.metadata.name))
                    # Skip this container
                    continue
                # Also skip the container if container.lnd_mount_dir contains a :
                if container.mounts.bitcoin.find(":") == -1:
                    container.volumes.append('${BITCOIN_DATA_DIR}:' + container.mounts.bitcoin)
            if container.mounts.c_lightning:
                if not 'c-lightning' in app.metadata.dependencies:
                    print("Warning: container {} of app {} defines lnd mount dir but doesn't request lnd permission".format(container.name, app.metadata.name))
                    # Skip this container
                    continue
                # Also skip the container if container.lnd_mount_dir contains a :
                if container.mounts.c_lightning.find(":") == -1:
                    container.volumes.append('${C_LIGHTNING_DATA_DIR}:' + container.mounts.bitcoin)
            del container.mounts                
    return app

def createComposeConfigFromV3(app: dict, nodeRoot: str):
    envFile = os.path.join(nodeRoot, ".env")
    networkingFile = os.path.join(nodeRoot, "apps", "networking.json")
    ignoredContainers = []
    newApp: App = generateApp(app)
    newApp = convertContainerPermissions(newApp)
    newApp = validateEnv(newApp)
    newApp = convertDataDirToVolumeGen3(newApp)
    newApp = configureIps(newApp, networkingFile, envFile)
    # This is validated earlier
    for container in newApp.containers:
        container.ports = container.requiredPorts
        del container.requiredPorts
    newApp = configureMainPort(newApp, nodeRoot)
    for container in newApp.containers:
        # TODO: Make this dynamic and not hardcoded
        if container.requires and "lnd" in container.requires:
            ignoredContainers.append(container.name)
            container.ignored = True
        elif container.requires:
            del container.requires
    newApp = configureHiddenServices(newApp, nodeRoot)
    for container in newApp.containers:
        del container.ignored
    finalConfig: AppStage4 = convertContainersToServices(newApp)
    newApp = classToDict(finalConfig)
    del newApp['metadata']
    for container in ignoredContainers:
        del newApp['services'][container]
    if "version" in newApp:
        del newApp["version"]
    # Set version to 3.8 (current compose file version)
    newApp = {'version': '3.8', **newApp}
    return newApp
