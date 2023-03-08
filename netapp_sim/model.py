'''
    This module includes classes used to model various networking concepts, 
    such as network nodes, their types and their specs, network interfaces and 
    their specs, network links and their specs, network applications, Classes 
    of Service (CoS) and their requirements.

    Classes:
    --------
    Model: Base class for all model classes.

    InterfaceSpecs: Network interface specs at given timestamp.

    Interface: Network interface (port).

    NodeSpecs: Network node specs at given timestamp.

    Node: Network node.

    LinkSpecs: Network link specs at given timestamp.

    Link: Network link.

    CoSSpecs: Set of minimum specs required to run applications belonging to 
    the Class of Service.

    CoS: Class of Service.

    Application: Network application. 
'''

from enum import Enum
from time import time
from copy import deepcopy


class Model:
    '''
        Base class for all model classes.
    '''

    def as_dict(self):
        return self.__dict__

    # the following methods are for database operations

    def save(self):
        '''
            Insert as a row in database table.

            Returns True if inserted, False if not.
        '''
        from dblib import save
        return save(self)

    @classmethod
    def fetch(cls, **kwargs):
        '''
            Fetch row(s) from database table.

            Filters can be applied through kwargs. Example:

                >>> CoS.fetch(id=('=', 1))

            Returns list of rows if selected, None if not.
        '''
        from dblib import fetch
        return fetch(cls, **kwargs)


class InterfaceSpecs(Model):
    '''
        Network interface specs.
    '''

    def __init__(self, bandwidth_up: float = 0, bandwidth_down: float = 0,
                 timestamp: float = time()):
        self.bandwidth_up = bandwidth_up
        self.bandwidth_down = bandwidth_down
        self.timestamp = timestamp


class Interface(Model):
    '''
        Network interface (port).

        Recommendation: use the provided getters and setters for specs in case 
        their structure changes in future updates.
    '''

    def __init__(self, name: str, num: int = -1, mac: str = '',
                 ipv4: str = '', specs: InterfaceSpecs = None):
        self.name = name
        self.num = num
        self.mac = mac
        self.ipv4 = ipv4
        if not specs:
            specs = InterfaceSpecs()
        self.specs = specs

    def as_dict(self):
        d = deepcopy(self.__dict__)
        d['specs'] = self.specs.as_dict()
        return d

    # the following methods serve for access to the interface specs no
    # matter how they are implemented (whether they are attributes
    # in the object, are objects themselves within an Iterable, etc.)

    def get_bandwidth_up(self):
        return self.specs.bandwidth_up

    def set_bandwidth_up(self, bandwidth_up: float = 0):
        self.specs.bandwidth_up = bandwidth_up
        self.set_timestamp()

    def get_bandwidth_down(self):
        return self.specs.bandwidth_down

    def set_bandwidth_down(self, bandwidth_down: float = 0):
        self.specs.bandwidth_down = bandwidth_down
        self.set_timestamp()

    def get_timestamp(self):
        return self.specs.timestamp

    def set_timestamp(self, timestamp: float = time()):
        self.specs.timestamp = timestamp


class NodeType(Enum):
    '''
        Network node type enumeration.
    '''
    SERVER = 'SERVER'
    VM = 'VM'
    IOT_OBJECT = 'IOT_OBJECT'
    GATEWAY = 'GATEWAY'
    SWITCH = 'SWITCH'
    ROUTER = 'ROUTER'


class NodeSpecs(Model):
    '''
        Network node specs at given timestamp.
    '''

    def __init__(self, cpu: int = 0, ram: float = 0, disk: float = 0,
                 timestamp: float = time()):
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.timestamp = timestamp


class Node(Model):
    '''
        Network node.

        Recommendation: use the provided getters and setters for specs in case 
        their structure changes in future updates.
    '''

    def __init__(self, id, state: bool, type: NodeType, label: str = '',
                 interfaces: dict = {},
                 specs: NodeSpecs = None):
        self.id = id
        self.state = state
        self.type = type
        self.label = label
        self.interfaces = interfaces
        if not specs:
            specs = NodeSpecs()
        self.specs = specs

    def as_dict(self):
        d = deepcopy(self.__dict__)
        d['type'] = self.type.value
        for name, intf in self.interfaces.items():
            d['interfaces'][name] = intf.as_dict()
        d['specs'] = self.specs.as_dict()
        return d

    # the following methods serve for access to the node specs no
    # matter how they are implemented (whether they are attributes
    # in the object, are objects themselves within an Iterable, etc.)

    def get_cpu(self):
        return self.specs.cpu

    def set_cpu(self, cpu: int = 0):
        self.specs.cpu = cpu
        self.set_timestamp()

    def get_ram(self):
        return self.specs.ram

    def set_ram(self, ram: float = 0):
        self.specs.ram = ram
        self.set_timestamp()

    def get_disk(self):
        return self.specs.disk

    def set_disk(self, disk: float = 0):
        self.specs.disk = disk
        self.set_timestamp()

    def get_timestamp(self):
        return self.specs.timestamp

    def set_timestamp(self, timestamp: float = time()):
        self.specs.timestamp = timestamp


class LinkSpecs(Model):
    '''
        Network link specs at given timestamp.
    '''

    def __init__(self, bandwidth: float = 0, delay: float = float('inf'),
                 jitter: float = float('inf'), loss_rate: float = 1,
                 timestamp: float = time()):
        self.bandwidth = bandwidth
        self.delay = delay
        self.jitter = jitter
        self.loss_rate = loss_rate
        self.timestamp = timestamp


class Link(Model):
    '''
        Network link.    

        Recommendation: use the provided getters and setters for specs in case 
        their structure changes in future updates.
    '''

    def __init__(self, src_port: Interface, dst_port: Interface,
                 state: bool, specs: LinkSpecs = None):
        self.src_port = src_port
        self.dst_port = dst_port
        self.state = state
        if not specs:
            specs = LinkSpecs()
        self.specs = specs

    def as_dict(self):
        d = deepcopy(self.__dict__)
        d['src_port'] = self.src_port.as_dict()
        d['dst_port'] = self.dst_port.as_dict()
        d['specs'] = self.specs.as_dict()
        return d

    # the following methods serve for access to the node specs no
    # matter how they are implemented (whether they are attributes
    # in the object, are objects themselves within an Iterable, etc.)

    def get_bandwidth(self):
        return self.specs.bandwidth

    def set_bandwidth(self, bandwidth: float = 0):
        self.specs.bandwidth = bandwidth
        self.set_timestamp()

    def get_delay(self):
        return self.specs.delay

    def set_delay(self, delay: float = float('inf')):
        self.specs.delay = delay
        self.set_timestamp()

    def get_jitter(self):
        return self.specs.jitter

    def set_jitter(self, jitter: float = float('inf')):
        self.specs.jitter = jitter
        self.set_timestamp()

    def get_loss_rate(self):
        return self.specs.loss_rate

    def set_loss_rate(self, loss_rate: float = 1):
        self.specs.loss_rate = loss_rate
        self.set_timestamp()

    def get_timestamp(self):
        return self.specs.timestamp

    def set_timestamp(self, timestamp: float = time()):
        self.specs.timestamp = timestamp


class CoSSpecs(Model):
    '''
        Set of minimum specs required to run applications belonging to the 
        Class of Service.
    '''

    def __init__(self,
                 max_response_time: float = float('inf'),
                 min_concurrent_users: float = 0,
                 min_requests_per_second: float = 0,
                 min_bandwidth: float = 0,
                 max_delay: float = float('inf'),
                 max_jitter: float = float('inf'),
                 max_loss_rate: float = 1,
                 min_cpu: int = 0,
                 min_ram: float = 0,
                 min_disk: float = 0):
        self.max_response_time = max_response_time
        self.min_concurrent_users = min_concurrent_users
        self.min_requests_per_second = min_requests_per_second
        self.min_bandwidth = min_bandwidth
        self.max_delay = max_delay
        self.max_jitter = max_jitter
        self.max_loss_rate = max_loss_rate
        self.min_cpu = min_cpu
        self.min_ram = min_ram
        self.min_disk = min_disk


class CoS(Model):
    '''
        Class of Service.

        Recommendation: use the provided getters and setters for specs in case 
        their structure changes in future updates.
    '''

    def __init__(self, id: int, name: str, specs: CoSSpecs = None):
        self.id = id
        self.name = name
        if not specs:
            specs = CoSSpecs()
        self.specs = specs

    def as_dict(self):
        d = deepcopy(self.__dict__)
        d['specs'] = self.specs.as_dict()
        return d

    # the following methods serve for access to the CoS specs no
    # matter how they are implemented (whether they are attributes
    # in the object, are objects themselves within an Iterable, etc.)

    def get_max_response_time(self):
        return self.specs.max_response_time

    def set_max_response_time(self, max_response_time: float = float('inf')):
        self.specs.max_response_time = max_response_time

    def get_min_concurrent_users(self):
        return self.specs.min_concurrent_users

    def set_min_concurrent_users(self, min_concurrent_users: float = 0):
        self.specs.min_concurrent_users = min_concurrent_users

    def get_min_requests_per_second(self):
        return self.specs.min_requests_per_second

    def set_min_requests_per_second(self, min_requests_per_second: float = 0):
        self.specs.min_requests_per_second = min_requests_per_second

    def get_min_bandwidth(self):
        return self.specs.min_bandwidth

    def set_min_bandwidth(self, bandwidth: float = 0):
        self.specs.min_bandwidth = bandwidth

    def get_max_delay(self):
        return self.specs.max_delay

    def set_max_delay(self, delay: float = float('inf')):
        self.specs.max_delay = delay

    def get_max_jitter(self):
        return self.specs.max_jitter

    def set_max_jitter(self, max_jitter: float = float('inf')):
        self.specs.max_jitter = max_jitter

    def get_max_loss_rate(self):
        return self.specs.max_loss_rate

    def set_max_loss_rate(self, max_loss_rate: float = 1):
        self.specs.max_loss_rate = max_loss_rate

    def get_min_cpu(self):
        return self.specs.min_cpu

    def set_min_cpu(self, cpu: int = 0):
        self.specs.min_cpu = cpu

    def get_min_ram(self):
        return self.specs.min_ram

    def set_min_ram(self, ram: float = 0):
        self.specs.min_ram = ram

    def get_min_disk(self):
        return self.specs.min_disk

    def set_min_disk(self, disk: float = 0):
        self.specs.min_disk = disk


class Application(Model):
    '''
        Network application. 

        Recommendation: use the provided getters for specs in case their 
        structure changes in future updates.
    '''

    def __init__(self, id: int, name: str, cos: CoS, node: Node):
        self.id = id
        self.name = name
        self.cos = cos
        self.node = node

    def as_dict(self):
        d = deepcopy(self.__dict__)
        d['cos'] = self.cos.as_dict()
        d['node'] = self.node.as_dict()
        return d

    # the following methods serve for access to the CoS specs no
    # matter how they are implemented (whether they are attributes
    # in the object, are objects themselves within an Iterable, etc.)

    def get_max_response_time(self):
        return self.cos.get_max_response_time()

    def get_min_requests_per_second(self):
        return self.cos.get_min_requests_per_second()

    def get_min_concurrent_users(self):
        return self.cos.get_min_concurrent_users()

    def get_min_bandwidth(self):
        return self.cos.get_min_bandwidth()

    def get_max_delay(self):
        return self.cos.get_max_delay()

    def get_max_jitter(self):
        return self.cos.get_max_jitter()

    def get_max_loss_rate(self):
        return self.cos.get_max_loss_rate()

    def get_min_cpu(self):
        return self.cos.get_min_cpu()

    def get_min_ram(self):
        return self.cos.get_min_ram()

    def get_min_disk(self):
        return self.cos.get_min_disk()
