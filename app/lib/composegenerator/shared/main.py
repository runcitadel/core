# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Main functions
from lib.composegenerator.v2.types import App, AppStage3, AppStage2
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
