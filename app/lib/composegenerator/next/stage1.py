from lib.citadelutils import classToDict
from lib.composegenerator.shared.env import validateEnv

from lib.composegenerator.v3.types import App, generateApp
from lib.composegenerator.v3.generate import convertContainerPermissions

def createCleanConfigFromV3(app: dict, nodeRoot: str):
    parsedApp: App = generateApp(app)
    for container in range(len(parsedApp.containers)):
        # TODO: Make this dynamic and not hardcoded
        if parsedApp.containers[container].requires and "c-lightning" in parsedApp.containers[container].requires:
            parsedApp.containers[container] = None
    parsedApp = convertContainerPermissions(parsedApp)
    parsedApp = validateEnv(parsedApp)
    finalApp = classToDict(parsedApp)
    try:
        finalApp['permissions'] = finalApp['metadata']['dependencies']
    except:
        finalApp['permissions'] = []
    finalApp['id'] = finalApp['metadata']['id']
    del finalApp['metadata']
    # Set version of the cache file format
    finalApp['version'] = "1"
    return finalApp
