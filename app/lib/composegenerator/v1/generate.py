from lib.composegenerator.v1.networking import configureIps, configureMainPort
from lib.composegenerator.shared.main import convertDataDirToVolume, convertContainerPermissions, addStopConfig, convertContainersToServices
from lib.composegenerator.shared.env import validateEnv
import os

def createComposeConfigFromV1(app: dict, nodeRoot: str):
    if("version" in app):
        if(str(app['version']) != "1"):
            print("Warning: app version is not supported")
            return False
    envFile = os.path.join(nodeRoot, ".env")
    networkingFile = os.path.join(nodeRoot, "apps", "networking.json")

    app = convertContainerPermissions(app)
    validateEnv(app)
    app = convertDataDirToVolume(app)
    app = configureIps(app, networkingFile, envFile)
    app = configureMainPort(app, nodeRoot)
    app = addStopConfig(app)
    app = convertContainersToServices(app)
    del app['metadata']
    if("version" in app):
        del app["version"]
    # Set version to 3.7 (current compose file version)
    app = {'version': '3.7', **app}
    return app
