'''
    Simulator for checking, reserving and freeing resources for network 
    applications, as well as their execution based on the requirements of their 
    Classes of Service (CoS).
    
    It can also function as a proxy of monitor, applying a filter to real 
    measurements (of CPU, RAM, and disk) to get simulated ones based on 
    capacities declared in conf.yml.

    Methods:
    --------
    check_resources(request): Returns True if the current resources can satisfy 
    the requirements of request, False if not.
    
    reserve_resources(request): Subtract a quantity of resources to be reserved 
    for request from simulation variables.
    
    free_resources(request): Add back a quantity of resources reserved for 
    request to simulation variables.

    execute(data): Simulate the execution of network application by doing 
    sleeping for a determined period of time (by default randomly generated 
    between 0s and 1s).
'''


from os import getenv
from threading import Lock
from random import uniform
from time import sleep
from logging import info
from pprint import pformat

from monitor import Monitor
from model import Request
from consts import MY_IP
import config


# host capacities (offered resources)
_host = 'DEFAULT'
if getenv('HOSTS_USE_DEFAULT', False) == 'True':
    _caps = getenv('HOSTS_DEFAULT', None)
else:
    _caps = getenv('HOSTS_' + MY_IP, None)
    if _caps == None:
        print(' *** WARNING in simulator: Host capacities for ' + MY_IP +
              ' missing from conf.yml (even though USE_DEFAULT is False). '
              'Defaulting to HOSTS:DEFAULT.')
        _caps = getenv('HOSTS_DEFAULT', None)
    else:
        _host = MY_IP
if _caps == None:
    print(' *** ERROR in simulator: Default host capacities missing from '
          'conf.yml.')
    exit()
_caps = eval(_caps)

try:
    CPU = int(_caps['CPU'])
except:
    print(' *** ERROR in simulator: HOSTS:' + _host + ':CPU parameter '
          'invalid or missing from conf.yml.')
    exit()

try:
    RAM = int(_caps['RAM'])
except:
    print(' *** ERROR in simulator: HOSTS:' + _host + ':RAM parameter '
          'invalid or missing from conf.yml.')
    exit()

try:
    DISK = int(_caps['DISK'])
except:
    print(' *** ERROR in simulator: HOSTS:' + _host + ':DISK parameter '
          'invalid or missing from conf.yml.')
    exit()

# real monitoring config
SIM_ON = getenv('SIMULATION_ACTIVE', False) == 'True'

if not SIM_ON:
    # start monitor
    monitor = Monitor()
    monitor.start()
    measures = monitor.measures
    wait = 0.1 #monitor.monitor_period

    while 'cpu_count' not in measures:
        sleep(wait)
    if CPU > measures['cpu_count']:
        print(' *** ERROR in simulator: Host cannot offer %d CPUs when it '
              'only has %d. Activate simulation to allow more resources than '
              'there really are.' % (CPU, measures['cpu_count']))
        monitor.stop()
        exit()

    while 'memory_total' not in measures:
        sleep(wait)
    if RAM > measures['memory_total']:
        print(' *** ERROR in simulator: Host cannot offer %.2fMB of RAM when '
              'it only has %.2fMB. Activate simulation to allow more resources '
              'than there really are.' % (RAM, measures['memory_total']))
        monitor.stop()
        exit()

    while 'disk_total' not in measures:
        sleep(wait)
    if DISK > measures['disk_total']:
        print(' *** ERROR in simulator: Host cannot offer %.2fGB of disk when '
              'it only has %.2fGB. Activate simulation to allow more resources '
              'than there really are.' % (DISK, measures['disk_total']))
        monitor.stop()
        exit()

# simulation variables of reserved resources
_reserved = {
    'cpu': 0,
    'ram': 0,  # in MB
    'disk': 0,  # in GB
}
_reserved_lock = Lock()  # for thread safety

# simulated exec time interval
try:
    SIM_EXEC_MIN = float(getenv('SIMULATION_EXEC_MIN', None))
    try:
        SIM_EXEC_MAX = float(getenv('SIMULATION_EXEC_MAX', None))
        if SIM_EXEC_MAX < SIM_EXEC_MIN:
            print(' *** WARNING: SIMULATION:EXEC_MIN and SIMULATION:EXEC_MAX '
                  'invalid. Defaulting to [0s, 1s].')
            SIM_EXEC_MIN = 0
            SIM_EXEC_MAX = 1
    except:
        print(' *** WARNING: SIMULATION:EXEC_MAX parameter invalid or missing '
              'from conf.yml. Defaulting to [0s, 1s].')
        SIM_EXEC_MIN = 0
        SIM_EXEC_MAX = 1
except:
    print(' *** WARNING: SIMULATION:EXEC_MIN parameter invalid or missing '
          'from conf.yml. Defaulting to [0s, 1s].')
    SIM_EXEC_MIN = 0
    SIM_EXEC_MAX = 1


def get_resources(quiet: bool = False):
    cpu = CPU - _reserved['cpu']
    _ram = RAM
    if not SIM_ON and measures['memory_free'] < RAM:
        _ram = measures['memory_free']
    ram = _ram - _reserved['ram']
    _disk = DISK
    if not SIM_ON and measures['disk_free'] < DISK:
        _disk = measures['disk_free']
    disk = _disk - _reserved['disk']
    if not quiet:
        if not SIM_ON:
            info('Host\'s real capacities\n'
                 '    CPU        = %d\n'
                 '    TOTAL RAM  = %.2f MB\n'
                 '    FREE RAM   = %.2f MB\n'
                 '    TOTAL DISK = %.2f GB\n'
                 '    FREE DISK  = %.2f GB\n' % (
                    measures['cpu_count'],
                    measures['memory_total'],
                    measures['memory_free'],
                    measures['disk_total'],
                    measures['disk_free']))
        info('Available for reservation\n'
             '    CPU  = %d\n'
             '    RAM  = %.2f MB\n'
             '    DISK = %.2f GB\n' % (cpu, ram, disk))
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
            info('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (
                min_cpu, min_ram, min_disk))
        cpu, ram, disk = get_resources(quiet)
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
        info('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (
            min_cpu, min_ram, min_disk))
        cpu, ram, disk, _, _ = get_resources(quiet=True)
        if cpu >= min_cpu and ram >= min_ram and disk >= min_disk:
            _reserved['cpu'] += min_cpu
            _reserved['ram'] += min_ram
            _reserved['disk'] += min_disk
            get_resources()
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
        get_resources()
        return True


def execute(data: bytes):
    '''
        Simulate execution of network application by doing nothing for a 
        determined period of time (by default randomly generated between 0s 
        and 1s).

        Returns result.
    '''

    sleep(uniform(SIM_EXEC_MIN, SIM_EXEC_MAX))
    return b'result'
