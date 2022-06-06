# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Main functions
from lib.composegenerator.v2.types import App, AppStage3, AppStage2, Container
from lib.composegenerator.shared.const import permissions


def convertContainerPermissions(app: App) -> App:
    for container in app.containers:
        for permission in container.permissions:
            if permission in permissions():
                container.environment_allow.extend(permissions()[permission]['environment_allow'])
                container.volumes.extend(permissions()[permission]['volumes'])
            else:
                print("Warning: container {} of app {} defines unknown permission {}".format(container.name, app.metadata.name, permission))
    return app

def convertContainersToServices(app: AppStage3) -> AppStage3:
    services = {}
    for container in app.containers:
        if container.permissions:
            del container.permissions
        services[container.name] = container
        del services[container.name].name
    del app.containers
    app.services = services
    return app

# Converts the data of every container in app.containers to a volume, which is then added to the app
def convertDataDirToVolume(app: App) -> AppStage2:
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
                
    return app
