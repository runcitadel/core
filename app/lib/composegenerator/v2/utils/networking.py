# SPDX-FileCopyrightText: 2021-2022 Citadel and contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later

from lib.composegenerator.v2.types import Metadata, Container


def getHiddenServiceMultiPort(name: str, id: str, internalIp: str, ports: list) -> str:
    hiddenServices = """
# {} Hidden Service
HiddenServiceDir /var/lib/tor/app-{}
""".format(
        name, id
    )
    for port in ports:
        hiddenServices += "HiddenServicePort {} {}:{}".format(port, internalIp, port)
        hiddenServices += "\n"
    return hiddenServices


def getHiddenServiceString(
    name: str, id: str, internalPort, internalIp: str, publicPort
) -> str:
    return """
# {} Hidden Service
HiddenServiceDir /var/lib/tor/app-{}
HiddenServicePort {} {}:{}

""".format(
        name, id, publicPort, internalIp, internalPort
    )


def getHiddenService(appName: str, appId: str, appIp: str, appPort: str) -> str:
    return getHiddenServiceString(appName, appId, appPort, appIp, "80")


def getContainerHiddenService(
    metadata: Metadata, container: Container, containerIp: str, isMainContainer: bool
) -> str:
    if isMainContainer and not container.hiddenServicePorts:
        return getHiddenServiceString(
            metadata.name, metadata.id, metadata.internalPort, containerIp, 80
        )

    if container.hiddenServicePorts:
        if isinstance(container.hiddenServicePorts, int):
            return getHiddenServiceString(
                "{} {}".format(metadata.name, container.name),
                metadata.id,
                container.hiddenServicePorts,
                containerIp,
                container.hiddenServicePorts,
            )
        elif isinstance(container.hiddenServicePorts, list):
            return getHiddenServiceMultiPort(
                "{} {}".format(metadata.name, container.name),
                metadata.id,
                containerIp,
                container.hiddenServicePorts,
            )
        elif isinstance(container.hiddenServicePorts, dict):
            additionalHiddenServices = {}
            hiddenServices = "# {} {} Hidden Service\nHiddenServiceDir /var/lib/tor/app-{}-{}\n".format(
                metadata.name, container.name, metadata.id, container.name
            )
            initialHiddenServices = "# {} {} Hidden Service\nHiddenServiceDir /var/lib/tor/app-{}-{}\n".format(
                metadata.name, container.name, metadata.id, container.name
            )
            otherHiddenServices = ""
            for key, value in container.hiddenServicePorts.items():
                if isinstance(key, int):
                    hiddenServices += "HiddenServicePort {} {}:{}".format(
                        key, containerIp, value
                    )
                    hiddenServices += "\n"
                else:
                    additionalHiddenServices[key] = value
            for key, value in additionalHiddenServices.items():
                otherHiddenServices += "\n"
                if isinstance(value, int):
                    otherHiddenServices += "# {} {} {} Hidden Service\nHiddenServiceDir /var/lib/tor/app-{}-{}\n".format(
                        metadata.name, container.name, key, metadata.id, container.name
                    )
                    otherHiddenServices += "HiddenServicePort {} {}:{}".format(
                        value, containerIp, value
                    )
                elif isinstance(value, list):
                    otherHiddenServices += getHiddenServiceMultiPort(
                        "{} {}".format(metadata.name, key), "{}-{}".format(metadata.id, key), containerIp, value
                    )
                
            if hiddenServices == initialHiddenServices:
                return otherHiddenServices
            else :
                return hiddenServices + "\n" + otherHiddenServices
        del container.hiddenServicePorts

    return ""
