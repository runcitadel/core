from typing import Union, List
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
    gallery: List[Union[list,str]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    updateContainer: Union[str, Union[list, None]] = field(default_factory=list)
    path: str = ""
    defaultPassword: str = ""
    torOnly: bool = False
    lightningImplementation: Union[str, None] = None
    # Added automatically later
    port: int = 0
    internalPort: int = 0

@dataclass
class ContainerMounts:
    bitcoin: Union[str, None] = None
    lnd: Union[str, None] = None
    c_lightning: Union[str, None] = None

@dataclass
class Container:
    name: str
    image: str
    permissions: list = field(default_factory=list)
    port: Union[int, None] = None
    requiredPorts: list = field(default_factory=list)
    preferredOutsidePort: Union[int, None] = None
    requiresPort: Union[bool, None] = None
    environment: Union[dict, None] = None
    data: list = field(default_factory=list)
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: list = field(default_factory=list)
    entrypoint: Union[List[str], str] = field(default_factory=list)
    mounts: Union[ContainerMounts, None] = None
    command: Union[List[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    hiddenServicePorts: Union[dict, Union[int, Union[None, list]]] = field(default_factory=list)
    environment_allow: list = field(default_factory=list)
    network_mode: Union[str, None] = None
    # Only added later
    volumes: list = field(default_factory=list)
    restart: Union[str, None] = None
    ports: list = field(default_factory=list)

@dataclass
class App:
    version: Union[str, int]
    metadata: Metadata
    containers: List[Container]

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
    permissions: List[str] = field(default_factory=list)
    ports: list = field(default_factory=list)
    environment: Union[dict, None] = None
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: List[str] = field(default_factory=list)
    entrypoint: Union[List[str], str] = field(default_factory=list)
    command: Union[List[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    hiddenServicePorts: Union[dict, Union[int, Union[None, list]]] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    networks: NetworkConfig = field(default_factory=NetworkConfig)
    restart: Union[str, None] = None
    network_mode: Union[str, None] = None

@dataclass
class AppStage2:
    version: Union[str, int]
    metadata: Metadata
    containers: List[ContainerStage2]

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
    dependencies: List[str]
    repo: str
    support: str
    gallery: List[str]
    updateContainer: Union[str, Union[list, None]] = field(default_factory=list)
    path: str = ""
    defaultPassword: str = ""
    torOnly: bool = False
    lightningImplementation: Union[str, None] = None
    # Added automatically later
    port: int = 0
    internalPort: int = 0

@dataclass
class AppStage3:
    version: Union[str, int]
    metadata: MetadataStage3
    containers: List[ContainerStage2]

@dataclass
class ContainerStage4:
    id: str
    name: str
    image: str
    ports: list = field(default_factory=list)
    environment: Union[dict, None] = None
    user: Union[str, None] = None
    stop_grace_period: str = '1m'
    depends_on: List[str] = field(default_factory=list)
    entrypoint: Union[List[str], str] = field(default_factory=list)
    command: Union[List[str], str] = field(default_factory=list)
    init: Union[bool, None] = None
    stop_signal: Union[str, None] = None
    noNetwork: Union[bool, None] = None
    hiddenServicePorts: Union[dict, Union[int, Union[None, list]]] = field(default_factory=list)
    volumes: List[str] = field(default_factory=list)
    networks: NetworkConfig = field(default_factory=NetworkConfig)
    restart: Union[str, None] = None
    network_mode: Union[str, None] = None

@dataclass
class AppStage4:
    version: Union[str, int]
    metadata: MetadataStage3
    services: List[ContainerStage4]