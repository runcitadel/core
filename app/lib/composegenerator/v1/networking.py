from lib.citadelutils import parse_dotenv
import json
from os import path
import random
from lib.composegenerator.v1.utils.networking import getFreePort, getHiddenService


def assignIp(container: dict, appId: str, networkingFile: str, envFile: str):
    # Strip leading/trailing whitespace from container['name']
    container['name'] = container['name'].strip()
    # If the name still contains a newline, throw an error
    if(container['name'].find("\n") != -1):
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        container['name'].upper().replace("-", "_")
    )
    # Write a list of used IPs to the usedIpFile as JSON, and read that file to check if an IP
    # can be used
    usedIps = []
    networkingData = {}
    if(path.isfile(networkingFile)):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)

    if('ip_addresses' in networkingData):
        usedIps = list(networkingData['ip_addresses'].values())
    else:
        networkingData['ip_addresses'] = {}
    # An IP 10.21.21.xx, with x being a random number above 50 is asigned to the container
    # If the IP is already in use, it will be tried again until it's not in use
    # If it's not in use, it will be added to the usedIps list and written to the usedIpFile
    # If the usedIpsFile contains all IPs between  10.21.21.50 and  10.21.21.255 (inclusive),
    # Throw an error, because no more IPs can be used
    if(len(usedIps) == 206):
        raise Exception("No more IPs can be used")

    if("{}-{}".format(appId, container['name']) in networkingData['ip_addresses']):
        ip = networkingData['ip_addresses']["{}-{}".format(appId, container['name'])]
    else:
        while True:
            ip = "10.21.21." + str(random.randint(50, 255))
            if(ip not in usedIps):
                networkingData['ip_addresses']["{}-{}".format(appId, container['name'])] = ip
                break
    container['networks'] = {'default': {
        'ipv4_address': "$" + env_var}}

    dotEnv = parse_dotenv(envFile)
    if(env_var in dotEnv and str(dotEnv[env_var]) == str(ip)):
        return container

    # Now append a new line  with APP_{app_name}_{container_name}_IP=${IP} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, ip))
    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)
    return container


def assignPort(container: dict, appId: str, networkingFile: str, envFile: str):
    # Strip leading/trailing whitespace from container['name']
    container['name'] = container['name'].strip()
    # If the name still contains a newline, throw an error
    if(container['name'].find("\n") != -1 or container['name'].find(" ") != -1):
        raise Exception("Newline or space in container name")

    env_var = "APP_{}_{}_PORT".format(
        appId.upper().replace("-", "_"),
        container['name'].upper().replace("-", "_")
    )

    port = getFreePort(networkingFile, appId)

    dotEnv = parse_dotenv(envFile)
    if(env_var in dotEnv and str(dotEnv[env_var]) == str(port)):
        return {"port": port, "env_var": "${{{}}}".format(env_var)}

    # Now append a new line  with APP_{app_name}_{container_name}_PORT=${PORT} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, port))

    # This is confusing, but {{}} is an escaped version of {} so it is ${{ {} }}
    # where the outer {{ }} will be replaced by {} in the returned string
    return {"port": port, "env_var": "${{{}}}".format(env_var)}


def configureMainPort(app: dict, nodeRoot: str):
    registryFile = path.join(nodeRoot, "apps", "registry.json")
    registry: list = []
    if(path.isfile(registryFile)):
        with open(registryFile, 'r') as f:
            registry = json.load(f)
    else:
        raise Exception("Registry file not found")


    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))

    if len(app['containers']) == 1:
        mainContainer = app['containers'][0]
    else:
        if not "mainContainer" in app['metadata']:
            raise Exception("No main container defined")

        for container in app['containers']:
            if(container['name'] == app['metadata']['mainContainer']):
                mainContainer = container
                break
    

    portDetails = assignPort(mainContainer, app['metadata']['id'], path.join(
        nodeRoot, "apps", "networking.json"), path.join(nodeRoot, ".env"))
    containerPort = portDetails['port']
    portAsEnvVar = portDetails['env_var']
    portToAppend = portAsEnvVar

    if "port" in mainContainer:
        portToAppend = "{}:{}".format(portAsEnvVar, mainContainer['port'])
        del mainContainer['port']

    if "ports" in mainContainer:
        mainContainer['ports'].append(portToAppend)
    else:
        mainContainer['ports'] = [portToAppend]

    mainContainer = assignIp(mainContainer, app['metadata']['id'], path.join(
        nodeRoot, "apps", "networking.json"), path.join(nodeRoot, ".env"))

    # If the IP wasn't in dotenv before, now it should be
    dotEnv = parse_dotenv(path.join(nodeRoot, ".env"))

    containerIP = dotEnv['APP_{}_{}_IP'.format(app['metadata']['id'].upper().replace(
        "-", "_"), mainContainer['name'].upper().replace("-", "_"))]

    hiddenservice = getHiddenService(
        app['metadata']['name'], app['metadata']['id'], containerIP, containerPort)

    torDaemons = ["torrc-apps", "torrc-apps-2", "torrc-apps-3"]
    torFileToAppend = torDaemons[random.randint(0, len(torDaemons) - 1)]
    with open(path.join(nodeRoot, "tor", torFileToAppend), 'a') as f:
        f.write(hiddenservice)

    # Also set the port in metadata
    app['metadata']['port'] = int(containerPort)

    for registryApp in registry:
        if(registryApp['id'] == app['metadata']['id']):
            registry[registry.index(registryApp)] = app['metadata']
            break

    with open(registryFile, 'w') as f:
        json.dump(registry, f, indent=4, sort_keys=True)

    return app


def configureIps(app: dict, networkingFile: str, envFile: str):
    for container in app['containers']:
        if('noNetwork' in container and container['noNetwork']):
            # Check if port is defined for the container
            if('port' in container):
                raise Exception("Port defined for container without network")
            if(app['metadata']['mainContainer'] == container['name']):
                raise Exception("Main container without network")
            # Skip this iteration of the loop
            continue
        
        container = assignIp(container, app['metadata']['id'], networkingFile, envFile)

    return app
