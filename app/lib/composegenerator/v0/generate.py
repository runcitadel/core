from lib.composegenerator.shared.main import convertDataDirToVolume, convertContainerPermissions, addStopConfig, convertContainersToServices
from lib.composegenerator.shared.env import validateEnv

def convertIpToNetwork(app: dict):
    for container in app['containers']:
        if 'ip' in container:
            container['networks'] = {'default': {
                'ipv4_address': container['ip']}}
            del container['ip']

    return app


def createComposeConfigFromV0(app: dict):
    if("version" in app):
        if(str(app['version']) != "0"):
            print("Warning: app version is not supported")
            return False

    app = convertContainerPermissions(app)
    validateEnv(app)
    app = convertDataDirToVolume(app)
    app = convertIpToNetwork(app)
    app = addStopConfig(app)
    app = convertContainersToServices(app)
    del app['metadata']
    if("version" in app):
        del app["version"]
    # Set version to 3.7 (current compose file version)
    app = {'version': '3.7', **app}
    return app
