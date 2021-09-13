def convertServicesToContainers(app: dict):
    app['containers'] = []
    # Loop through the dict app['services']
    for container in app['services']:
        app['services'][container]['name'] = container
        app['containers'].append(app['services'][container])
    del app['services']
    return app


# Now invert convertDataDirToVolume by, from a string in format '${APP_DATA_DIR}/' + container['name'] + '/:' + container['data']
# getting only the part after the :/
def convertVolumeToDataDir(app: dict):
    for container in app['containers']:
        if 'volumes' in container:
            # Try to detect the data dir(ectories), they should be something like ${APP_DATA_DIR}/<something>:<something-else>
            # and should be converted into <something>:<something-else>
            container['data'] = []
            for i in range(len(container['volumes']) - 1, -1, -1):
                if('${APP_DATA_DIR}' in container['volumes'][i]):
                    # ${APP_DATA_DIR}/<something>:<something-else> should be converted into <something>:<something-else>
                    # Remove the ${APP_DATA_DIR}
                    container['data'].append(
                        container['volumes'][i].replace('${APP_DATA_DIR}/', ''))
                    container['volumes'].remove(container['volumes'][i])

    return app


# Remove duplicated items from a list
def removeDuplicates(list_to_clean: list):
    return list(set(list_to_clean))

# Get permissions from a container where these are unknown
# If a containers env vars contains the string "BITCOIN", it very likely needs the bitcoind permission
# If a containers env vars contains the string "LND" or a volume contains the string LND_DATA_DIR, it very likely needs the lnd permission


def getContainerPermissions(app: dict, name: str):
    for container in app['containers']:
        container['permissions'] = []
        if("environment" in container):
            if(isinstance(container['environment'], list)):
                for envVar in container['environment']:
                    if(str(envVar).find('BITCOIN') != -1):
                        container['permissions'].append('bitcoind')
                    if(str(envVar).find('LND') != -1):
                        container['permissions'].append('lnd')

            elif(isinstance(container['environment'], dict)):
                for envVar in container['environment'].values():
                    # BITCOIN_NETWORK is also useful for LND, and doesn't need the btcoin permission
                    if str(envVar).find('BITCOIN') != -1 and str(envVar).find('BITCOIN_NETWORK') == -1:
                        container['permissions'].append('bitcoind')
                    if(str(envVar).find('LND') != -1):
                        container['permissions'].append('lnd')
                    if(str(envVar).find('ELECTRUM') != -1):
                        container['permissions'].append('electrum')

        # Now loop through volumes
        if('volumes' in container):
            for i in range(len(container['volumes']) - 1, -1, -1):
                volume = container['volumes'][i]
                if('LND_DATA_DIR' in volume):
                    container['permissions'].append('lnd')
                    container['volumes'].remove(volume)
                    continue
                if('BITCOIN_DATA_DIR' in volume):
                    container['permissions'].append('bitcoind')
                    container['volumes'].remove(volume)
                    continue

            if(len(container['volumes']) == 0):
                del container['volumes']
            else:
                print("Warning: Couldn't parse some volumes for container {} in app {}".format(
                    container['name'], name))

        if(len(container['permissions']) == 0):
            del container['permissions']
        else:
            container['permissions'] = removeDuplicates(
                container['permissions'])

    return app


def convertComposeYMLToAppYML(app: dict, name: str, registry: dict):
    appMetadata = {}
    # Get the member of the registry list where element['name']== name
    for element in registry:
        if(element['id'] == name):
            appMetadata = element
            break

    if(appMetadata == {}):
        print("Warning: Couldn't get metadata for app {}".format(name))

    app = convertServicesToContainers(app)
    app = convertVolumeToDataDir(app)
    app = getContainerPermissions(app, name)
    for container in app['containers']:
        if('networks' in container):
            container['ip'] = container['networks']['default']['ipv4_address']
            del container['networks']

        if('permissions' in container):
            if not 'dependencies' in appMetadata:
                appMetadata['dependencies'] = []
            for permission in container['permissions']:
                appMetadata['dependencies'].append(permission)
            appMetadata['dependencies'] = removeDuplicates(appMetadata['dependencies'])
        
        if('restart' in container):
            del container['restart']

    del app['version']
    return {"metadata": appMetadata, **app}
