'''
    This module simulates checking, reserving and freeing resources- based on
    capacities declared in conf.yml- for, as well as execution of, network 
    applications based on requirements of their Class of Service (CoS).
    
    It can also function as a proxy of monitor, applying a filter to real 
    measurements (of CPU, RAM, and disk) to get simulated ones.

    Methods:
    --------
    check_resources(req): Returns True if current resources can satisfy 
    requirements of Request, False if not.
    
    reserve_resources(req): Add quantity of resources to be reserved for 
    Request to simulation variables.
    
    free_resources(req): Subtract quantity of resources reserved for Request 
    from simulation variables.

    execute(data): Simulate execution of network application by doing nothing 
    for a determined period of time (by default randomly generated between 0s 
    and 1s).
'''


from os import getenv
from threading import Lock
from random import uniform
from time import sleep

from monitor import Monitor
from model import Request
import config


# simulation constants of resource capacities
try:
    SIM_CPU = int(getenv('SIM_CPU', None))
except:
    SIM_CPU = None
if SIM_CPU == None:
    print(' *** ERROR: SIM_CPU parameter invalid or missing from conf.yml.')
    exit()

try:
    SIM_RAM = float(getenv('SIM_RAM', None))
except:
    SIM_RAM = None
if SIM_RAM == None:
    print(' *** ERROR: SIM_RAM parameter invalid or missing from conf.yml.')
    exit()

try:
    SIM_DISK = float(getenv('SIM_DISK', None))
except:
    SIM_DISK = None
if SIM_DISK == None:
    print(' *** ERROR: SIM_DISK parameter invalid or missing from conf.yml.')
    exit()

_capacities = {  
    'cpu': SIM_CPU,
    'ram': SIM_RAM,     # in MB
    'disk': SIM_DISK    # in GB
}

# simulation variables of reserved resources
_reserved = {  
    'cpu': 0,
    'ram': 0,  # in MB
    'disk': 0  # in GB
}
_reserved_lock = Lock()  # for thread safety

# simulated exec time interval
try:
    EXEC_T_MIN = float(getenv('EXEC_T_MIN', 0))
except:
    EXEC_T_MIN = 0

try:
    EXEC_T_MAX = float(getenv('EXEC_T_MAX', 1))
except:
    EXEC_T_MAX = 1


# start monitor
# monitor = Monitor()
# monitor.start()


def _get_resources(quiet: bool = False):
    cpu = _capacities['cpu'] - _reserved['cpu']
    ram = _capacities['ram'] - _reserved['ram']
    disk = _capacities['disk'] - _reserved['disk']
    if not quiet:
        print('current(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (cpu, ram, disk))
    return cpu, ram, disk


def check_resources(req: Request, quiet: bool = False):
    '''
        Returns True if current resources can satisfy requirements of Request, 
        False if not.
    '''
    with _reserved_lock:
        min_cpu = req.get_min_cpu()
        min_ram = req.get_min_ram()
        min_disk = req.get_min_disk()
        if not quiet:
            print('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (
                min_cpu, min_ram, min_disk))
        cpu, ram, disk = _get_resources(quiet)
        return cpu >= min_cpu and ram >= min_ram and disk >= min_disk


def reserve_resources(req: Request):
    '''
        Add quantity of resources to be reserved for Request to simulation 
        variables.

        Returns True if reserved, False if not.
    '''
    with _reserved_lock:
        min_cpu = req.get_min_cpu()
        min_ram = req.get_min_ram()
        min_disk = req.get_min_disk()
        print('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (
            min_cpu, min_ram, min_disk))
        cpu, ram, disk = _get_resources(quiet=True)
        if cpu >= min_cpu and ram >= min_ram and disk >= min_disk:
            _reserved['cpu'] += min_cpu
            _reserved['ram'] += min_ram
            _reserved['disk'] += min_disk
            _get_resources()
            return True
        else:
            return False


def free_resources(req: Request):
    '''
        Subtract quantity of resources reserved for Request from simulation 
        variables.

        Returns True if freed, False if not.
    '''
    with _reserved_lock:
        _reserved['cpu'] -= req.get_min_cpu()
        if _reserved['cpu'] < 0:
            _reserved['cpu'] = 0
        _reserved['ram'] -= req.get_min_ram()
        if _reserved['ram'] < 0:
            _reserved['ram'] = 0
        _reserved['disk'] -= req.get_min_disk()
        if _reserved['disk'] < 0:
            _reserved['disk'] = 0
        _get_resources()
        return True


def execute(data: bytes):
    '''
        Simulate execution of network application by doing nothing for a 
        determined period of time (by default randomly generated between 0s 
        and 1s).

        Returns result.
    '''
    sleep(uniform(EXEC_T_MIN, EXEC_T_MAX))
    return b'response'
