# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import random

from lib.composegenerator.v1.types import Container

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
        # Sparko
        9737,
        # Electrum Server
        50001,
        # Tor Proxy
        9050,
    ]
    networkingData = {}
    if os.path.isfile(networkingFile):
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


def getHiddenServiceMultiPort(name: str, id: str, internalIp: str, ports: list) -> str:
    hiddenServices = '''
# {} Hidden Service
HiddenServiceDir /var/lib/tor/app-{}
'''.format(name, id)
    for port in ports:
        hiddenServices += 'HiddenServicePort {} {}:{}'.format(
            port, internalIp, port)
        hiddenServices += "\n"
    return hiddenServices


def getHiddenServiceString(name: str, id: str, internalPort, internalIp: str, publicPort) -> str:
    return '''
# {} Hidden Service
HiddenServiceDir /var/lib/tor/app-{}
HiddenServicePort {} {}:{}

'''.format(name, id, publicPort, internalIp, internalPort)


def getHiddenService(appName: str, appId: str, appIp: str, appPort: str) -> str:
    return getHiddenServiceString(appName, appId, appPort, appIp, "80")


def getContainerHiddenService(appName: str, appId: str, container: Container, containerIp: str, isMainContainer: bool) -> str:
    if not container.needsHiddenService and not isMainContainer:
        return ""
    if (container.ports or not container.port) and not container.hiddenServicePort and not isMainContainer:
        print("Container {} for app {} isn't compatible with hidden service assignment".format(
            container.name, appName))
        return ""

    if isMainContainer:
        if not container.hiddenServicePorts:
            return ""
        # hiddenServicePorts is a map of hidden service name to port
        # We need to generate a hidden service for each one
        hiddenServices = ""
        for name, port in container.hiddenServicePorts.items():
            if ".." in name:
                print(".. Not allowed in service names, this app ({}) isn't getting a hidden service.".format(appName))
            
            # If port is a list, use getHiddenServiceMultiPort
            if isinstance(port, list):
                hiddenServices += getHiddenServiceMultiPort("{} {}".format(appName, name), "{}-{}".format(
                    appId, name), containerIp, port)
            else:
                hiddenServices += getHiddenServiceString("{} {}".format(appName, name), "{}-{}".format(
                    appId, name), port, containerIp, port)
        del container.hiddenServicePorts
        return hiddenServices

    del container.needsHiddenService
    if not container.port:
        data = getHiddenServiceString(appName + container.name, "{}-{}".format(
            appId, container.name), container.hiddenServicePort, containerIp, "80")
        del container.hiddenServicePort
        return data
    else:
        return getHiddenServiceString(appName + container.name, "{}-{}".format(
            appId, container.name), container.port, containerIp, container.port)
