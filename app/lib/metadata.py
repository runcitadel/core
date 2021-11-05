# SPDX-FileCopyrightText: 2021 Aaron Dewes <aaron.dewes@protonmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import yaml

from lib.composegenerator.v1.networking import getMainContainer
from lib.entropy import deriveEntropy

def getUpdateContainer(app: dict):
    if len(app['containers']) == 1:
        return app['containers'][0]
    else:
        if 'updateContainer' in app['metadata']:
            for container in app['containers']:
                    if container['name'] == app['metadata']['updateContainer']:
                        return container
    return getMainContainer(app)

# For every app, parse the app.yml in ../apps/[name] and
# check their metadata, and return a list of all app's metadata
# Also check the path and defaultPassword and set them to an empty string if they don't exist
# In addition, set id on the metadata to the name of the app
# Return a list of all app's metadata
def getAppRegistry(apps, app_path):
    app_metadata = []
    for app in apps:
        app_yml_path = os.path.join(app_path, app, 'app.yml')
        if os.path.isfile(app_yml_path):
            with open(app_yml_path, 'r') as f:
                app_yml = yaml.safe_load(f.read())
            metadata: dict = app_yml['metadata']
            metadata['id'] = app
            metadata['path'] = metadata.get('path', '')
            metadata['defaultPassword'] = metadata.get('defaultPassword', '')
            if metadata['defaultPassword'] == "$APP_SEED":
                metadata['defaultPassword'] = deriveEntropy("app-{}-seed".format(app))
            if("mainContainer" in metadata):
                metadata.pop("mainContainer")
            app_metadata.append(metadata)
    return app_metadata
