import json
import os
import random

def getFreePort(networkingFile: str, appId: str):
    # Ports used currently in Umbrel
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

def getHiddenService(appName: str, appId: str, appIp: str, appPort: str) -> str:
                return '''
# {} Hidden Service
HiddenServiceDir /var/lib/tor/app-{}
HiddenServicePort 80 {}:{}

            '''.format(appName, appId, appIp, appPort)
