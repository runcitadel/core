# SPDX-FileCopyrightText: 2021 Aaron Dewes <aaron.dewes@protonmail.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import random


def getFreePort(networkingFile: str, appId: str):
    # Ports used currently in Citadel
    # TODO: Update this list, currently it's outdated
    usedPorts = [80, 8333, 8332, 28332, 28333, 28334, 10009, 8080, 50001, 9050, 3002, 3000, 3300, 3001, 3004, 25441,
                 3003, 3007, 3006, 3009, 3005, 8898, 3008, 8081, 8082, 8083, 8085, 2222, 8086, 8087, 8008, 8088, 8089, 8091]
    networkingData = {}
    if(os.path.isfile(networkingFile)):
        with open(networkingFile, 'r') as f:
            networkingData = json.load(f)
    if('ports' in networkingData):
        usedPorts += list(networkingData['ports'].values())
    else:
        networkingData['ports'] = {}

    if(appId in networkingData['ports']):
        return networkingData['ports'][appId]

    while True:
        port = str(random.randint(1024, 49151))
        if(port not in usedPorts):
            # Check if anyhing is listening on the specific port
            if(os.system("netstat -ntlp | grep " + port + " > /dev/null") != 0):
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


def getContainerHiddenService(appName: str, appId: str, container: dict, containerIp: str, isMainContainer: bool) -> str:
    if not "needsHiddenService" in container and not isMainContainer:
        return ""
    if ("ports" in container or not "port" in container) and not "hiddenServicePort" in container and not isMainContainer:
        print("Container {} for app {} isn't compatible with hidden service assignment".format(
            container["name"], appName))
        return ""

    if isMainContainer:
        if not "hiddenServicePorts" in container:
            return ""
        # hiddenServicePorts is a map of hidden service name to port
        # We need to generate a hidden service for each one
        hiddenServices = ""
        for name, port in container["hiddenServicePorts"].items():
            if ".." in name:
                print(".. Not allowed in service names, this app ({}) isn't getting a hidden service.".format(appName))
            
            # If port is a list, use getHiddenServiceMultiPort
            if isinstance(port, list):
                hiddenServices += getHiddenServiceMultiPort("{} {}".format(appName, name), "{}-{}".format(
                    appId, name), containerIp, port)
            else:
                hiddenServices += getHiddenServiceString("{} {}".format(appName, name), "{}-{}".format(
                    appId, name), port, containerIp, port)
        del container["hiddenServicePorts"]
        return hiddenServices

    del container["needsHiddenService"]
    if not "port" in container:
        data = getHiddenServiceString(appName + container["name"], "{}-{}".format(
            appId, container["name"]), container["hiddenServicePort"], containerIp, "80")
        del container["hiddenServicePort"]
        return data
    else:
        return getHiddenServiceString(appName + container["name"], "{}-{}".format(
            appId, container["name"]), container["port"], containerIp, container["port"])
