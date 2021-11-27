from typing import Union
from dataclasses import dataclass, field
from dacite import from_dict

@dataclass
class Metadata:
    id: str
    name: str
    version: str
    category: str
    tagline: str
    description: str
    developer: str
    website: str
    repo: str
    support: str
    gallery: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    mainContainer: Union[str, None] = None
    updateContainer: Union[str, None] = None
    path: str = ""
    defaultPassword: str = ""
    torOnly: bool = False

@dataclass
class Container:
    name: str
    image: str
    permissions: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    port: Union[int, None] = None
    environment: Union[dict, None] = None
    data: list = field(default_factory=list)
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: list = field(default_factory=list)
    entrypoint: Union[list[str], str] = field(default_factory=list)
    bitcoin_mount_dir: Union[str, None] = None
    command: Union[list[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    needsHiddenService: Union[bool, None] = None
    hiddenServicePort: Union[int, None] = None
    hiddenServicePorts: Union[dict, None] = None
    environment_allow: list = field(default_factory=list)
    # Only added later
    volumes: list = field(default_factory=list)
    restart: Union[str, None] = None

@dataclass
class App:
    version: Union[str, int]
    metadata: Metadata
    containers: list[Container]

# Generate an app instance from an app dict
def generateApp(appDict):
    return from_dict(data_class=App, data=appDict)

@dataclass
class Network:
    ipv4_address: Union[str, None] = None

@dataclass
class NetworkConfig:
    default: Network

# After converting data dir and defining volumes, stage 2
@dataclass
class ContainerStage2:
    id: str
    name: str
    image: str
    permissions: list[str] = field(default_factory=list)
    ports: list = field(default_factory=list)
    environment: Union[dict, None] = None
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: list[str] = field(default_factory=list)
    entrypoint: Union[list[str], str] = field(default_factory=list)
    command: Union[list[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    needsHiddenService: Union[bool, None] = None
    hiddenServicePort: Union[int, None] = None
    hiddenServicePorts: Union[dict, None] = None
    volumes: list[str] = field(default_factory=list)
    networks: NetworkConfig = field(default_factory=NetworkConfig)
    restart: Union[str, None] = None

@dataclass
class AppStage2:
    version: Union[str, int]
    metadata: Metadata
    containers: list[ContainerStage2]

@dataclass
class MetadataStage3:
    id: str
    name: str
    version: str
    category: str
    tagline: str
    description: str
    developer: str
    website: str
    dependencies: list[str]
    repo: str
    support: str
    gallery: list[str]
    mainContainer: Union[str, None] = None
    updateContainer: Union[str, None] = None
    path: str = ""
    defaultPassword: str = ""
    torOnly: bool = False

@dataclass
class AppStage3:
    version: Union[str, int]
    metadata: MetadataStage3
    containers: list[ContainerStage2]

@dataclass
class ContainerStage4:
    id: str
    name: str
    image: str
    ports: list = field(default_factory=list)
    environment: Union[dict, None] = None
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: list[str] = field(default_factory=list)
    entrypoint: Union[list[str], str] = field(default_factory=list)
    command: Union[list[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    needsHiddenService: Union[bool, None] = None
    hiddenServicePort: Union[int, None] = None
    hiddenServicePorts: Union[dict, None] = None
    volumes: list[str] = field(default_factory=list)
    networks: NetworkConfig = field(default_factory=NetworkConfig)
    restart: Union[str, None] = None

@dataclass
class AppStage4:
    version: Union[str, int]
    metadata: MetadataStage3
    services: list[ContainerStage4]