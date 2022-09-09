# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lib.composegenerator.v2.types import App, AppStage2, AppStage4, generateApp
from lib.composegenerator.v2.networking import configureMainPort
from lib.composegenerator.shared.networking import configureHiddenServices, configureIps
from lib.composegenerator.shared.main import convertContainerPermissions, convertContainersToServices
from lib.composegenerator.shared.env import validateEnv
from lib.citadelutils import classToDict
import os

def convertDataDirToVolumeGen2(app: App) -> AppStage2:
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
        if container.bitcoin_mount_dir != None:
            if not 'bitcoind' in container.permissions:
                print("Warning: container {} of app {} defines bitcoin_mount_dir but has no permissions for bitcoind".format(container.name, app.metadata.name))
                # Skip this container
                continue
            # Also skip the container if container.bitcoin_mount_dir contains a :
            if container.bitcoin_mount_dir.find(":") == -1:
                container.volumes.append('${BITCOIN_DATA_DIR}:' + container.bitcoin_mount_dir)
            del container.bitcoin_mount_dir
        if container.lnd_mount_dir != None:
            if not 'lnd' in container.permissions:
                print("Warning: container {} of app {} defines lnd_mount_dir but doesn't request lnd permission".format(container.name, app.metadata.name))
                # Skip this container
                continue
            # Also skip the container if container.lnd_mount_dir contains a :
            if container.lnd_mount_dir.find(":") == -1:
                container.volumes.append('${LND_DATA_DIR}:' + container.lnd_mount_dir)
            del container.lnd_mount_dir
        if container.c_lightning_mount_dir != None:
            if not 'lnd' in container.permissions:
                print("Warning: container {} of app {} defines c_lightning_mount_dir but doesn't request c-lightning permission".format(container.name, app.metadata.name))
                # Skip this container
                continue
            # Also skip the container if container.c_lightning.mount_dir contains a :
            if container.c_lightning_mount_dir.find(":") == -1:
                container.volumes.append('${C_LIGHTNING_DATA_DIR}:' + container.c_lightning_mount_dir)
            del container.c_lightning_mount_dir
                
    return app

def createComposeConfigFromV2(app: dict, nodeRoot: str):
    envFile = os.path.join(nodeRoot, ".env")
    networkingFile = os.path.join(nodeRoot, "apps", "networking.json")

    newApp: App = generateApp(app)
    newApp = convertContainerPermissions(newApp)
    newApp = validateEnv(newApp)
    newApp = convertDataDirToVolumeGen2(newApp)
    newApp = configureIps(newApp, networkingFile, envFile)
    newApp = configureMainPort(newApp, nodeRoot)
    newApp = configureHiddenServices(newApp, nodeRoot)
    finalConfig: AppStage4 = convertContainersToServices(newApp)
    newApp = classToDict(finalConfig)
    del newApp['metadata']
    if "version" in newApp:
        del newApp["version"]
    # Set version to 3.8 (current compose file version)
    newApp = {'version': '3.8', **newApp}
    return newApp
