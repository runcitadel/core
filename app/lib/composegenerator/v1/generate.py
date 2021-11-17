# SPDX-FileCopyrightText: 2021 Aaron Dewes <aaron.dewes@protonmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from lib.composegenerator.v1.types import App, AppStage4, generateApp
from lib.composegenerator.v1.networking import configureHiddenServices, configureIps, configureMainPort
from lib.composegenerator.shared.main import convertDataDirToVolume, convertContainerPermissions, convertContainersToServices
from lib.composegenerator.shared.env import validateEnv
from lib.citadelutils import classToDict
import os

def createComposeConfigFromV1(app: dict, nodeRoot: str):
    if "version" in app:
        if str(app['version']) != "1":
            print("Warning: app version is not supported")
            return False
    envFile = os.path.join(nodeRoot, ".env")
    networkingFile = os.path.join(nodeRoot, "apps", "networking.json")

    newApp: App = generateApp(app)
    newApp = convertContainerPermissions(newApp)
    validateEnv(newApp)
    newApp = convertDataDirToVolume(newApp)
    newApp = configureIps(newApp, networkingFile, envFile)
    newApp = configureMainPort(newApp, nodeRoot)
    configureHiddenServices(newApp, nodeRoot)
    finalConfig: AppStage4 = convertContainersToServices(newApp)
    newApp = classToDict(finalConfig)
    del newApp['metadata']
    if "version" in newApp:
        del newApp["version"]
    # Set version to 3.8 (current compose file version)
    newApp = {'version': '3.8', **newApp}
    return newApp
