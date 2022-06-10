# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from os import path
import random
from lib.composegenerator.v2.types import ContainerStage2, NetworkConfig
from lib.citadelutils import parse_dotenv
from dacite import from_dict

def getFreePort(networkingFile: str, appId: str):
    # Ports used currently in Citadel
    usedPorts = [
        # Dashboard
        80,
        # Sometimes used by nginx with some setups
        433,
        # Dashboard SSL
        443,
        # Bitcoin Core P2P
        8333,
        # LND gRPC
        10009,
        # LND REST
        8080,
        # Electrum Server
        50001,
        # Tor Proxy
        9050,
    ]
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)
    if 'ports' in networkingData:
        usedPorts += list(networkingData['ports'].values())
    else:
        networkingData['ports'] = {}

    if appId in networkingData['ports']:
        return networkingData['ports'][appId]

    while True:
        port = str(random.randint(1024, 49151))
        if port not in usedPorts:
            # Check if anyhing is listening on the specific port
            if os.system("netstat -ntlp | grep " + port + " > /dev/null") != 0:
                networkingData['ports'][appId] = port
                break

    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)

    return port

def assignIpV4(appId: str, containerName: str):
    cleanContainerName = containerName.strip()
    # If the name still contains a newline, throw an error
    if cleanContainerName.find("\n") != -1:
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        cleanContainerName.upper().replace("-", "_")
    )
    # Write a list of used IPs to the usedIpFile as JSON, and read that file to check if an IP
    # can be used
    usedIps = []
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)

    if 'ip_addresses' in networkingData:
        usedIps = list(networkingData['ip_addresses'].values())
    else:
        networkingData['ip_addresses'] = {}
    # An IP 10.21.21.xx, with x being a random number above 40 is asigned to the container
    # If the IP is already in use, it will be tried again until it's not in use
    # If it's not in use, it will be added to the usedIps list and written to the usedIpFile
    # If the usedIpsFile contains all IPs between  10.21.21.20 and  10.21.21.255 (inclusive),
    # Throw an error, because no more IPs can be used
    if len(usedIps) == 235:
        raise Exception("No more IPs can be used")

    if "{}-{}".format(appId, cleanContainerName) in networkingData['ip_addresses']:
        ip = networkingData['ip_addresses']["{}-{}".format(
            appId, cleanContainerName)]
    else:
        while True:
            ip = "10.21.21." + str(random.randint(20, 255))
            if ip not in usedIps:
                networkingData['ip_addresses']["{}-{}".format(
                    appId, cleanContainerName)] = ip
                break

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(ip):
        return

    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, ip))
    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)

def assignIp(container: ContainerStage2, appId: str, networkingFile: str, envFile: str) -> ContainerStage2:
    # Strip leading/trailing whitespace from container.name
    container.name = container.name.strip()
    # If the name still contains a newline, throw an error
    if container.name.find("\n") != -1:
        raise Exception("Newline in container name")
    env_var = "APP_{}_{}_IP".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
    )
    # Write a list of used IPs to the usedIpFile as JSON, and read that file to check if an IP
    # can be used
    usedIps = []
    networkingData = {}
    if path.isfile(networkingFile):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)

    if 'ip_addresses' in networkingData:
        usedIps = list(networkingData['ip_addresses'].values())
    else:
        networkingData['ip_addresses'] = {}
    # An IP 10.21.21.xx, with x being a random number above 40 is asigned to the container
    # If the IP is already in use, it will be tried again until it's not in use
    # If it's not in use, it will be added to the usedIps list and written to the usedIpFile
    # If the usedIpsFile contains all IPs between  10.21.21.20 and  10.21.21.255 (inclusive),
    # Throw an error, because no more IPs can be used
    if len(usedIps) == 235:
        raise Exception("No more IPs can be used")

    if "{}-{}".format(appId, container.name) in networkingData['ip_addresses']:
        ip = networkingData['ip_addresses']["{}-{}".format(
            appId, container.name)]
    else:
        while True:
            ip = "10.21.21." + str(random.randint(20, 255))
            if ip not in usedIps:
                networkingData['ip_addresses']["{}-{}".format(
                    appId, container.name)] = ip
                break
    container.networks = from_dict(data_class=NetworkConfig, data={'default': {
        'ipv4_address': "$" + env_var}})

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(ip):
        return container

    # Now append a new line  with APP_{app_name}_{container_name}_IP=${IP} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, ip))
    with open(networkingFile, 'w') as f:
        json.dump(networkingData, f)
    return container


def assignPort(container: dict, appId: str, networkingFile: str, envFile: str):
    # Strip leading/trailing whitespace from container.name
    container.name = container.name.strip()
    # If the name still contains a newline, throw an error
    if container.name.find("\n") != -1 or container.name.find(" ") != -1:
        raise Exception("Newline or space in container name")

    env_var = "APP_{}_{}_PORT".format(
        appId.upper().replace("-", "_"),
        container.name.upper().replace("-", "_")
    )

    port = getFreePort(networkingFile, appId)

    dotEnv = parse_dotenv(envFile)
    if env_var in dotEnv and str(dotEnv[env_var]) == str(port):
        return {"port": port, "env_var": "${{{}}}".format(env_var)}

    # Now append a new line  with APP_{app_name}_{container_name}_PORT=${PORT} to the envFile
    with open(envFile, 'a') as f:
        f.write("{}={}\n".format(env_var, port))

    # This is confusing, but {{}} is an escaped version of {} so it is ${{ {} }}
    # where the outer {{ }} will be replaced by {} in the returned string
    return {"port": port, "env_var": "${{{}}}".format(env_var)}

