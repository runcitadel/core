from lib.validate import findAndValidateApps
import os
import yaml
# List all apps using findAndValidateApps()
# then parse the app.yml in ../apps/[name] and
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
                app_metadata.append(metadata)
    return app_metadata

# Creates a registry with just the things we need in the update checker so we can remove registry.json from this repo.
# We need these properties: id, name, repo, version, nothing else. We don't need to check for the existence of these properties.
# app_yml['metadata'] may contain other properties, but we don't need them and we remove them from the registry.
def getSimpleAppRegistry(apps, app_path):
    app_metadata = []
    for app in apps:
        app_yml_path = os.path.join(app_path, app, 'app.yml')
        if os.path.isfile(app_yml_path):
            with open(app_yml_path, 'r') as f:
                app_yml = yaml.safe_load(f.read())
                metadata = {
                    'id': app,
                    'name': app_yml['metadata']['name'],
                    'repo': app_yml['metadata']['repo'],
                    'version': app_yml['metadata']['version']
                }
                app_metadata.append(metadata)
    return app_metadata
