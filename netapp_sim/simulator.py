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
from logging import info

from monitor import Monitor
from model import Request
from consts import MY_IP
import config


# host capacities (offered resources)
_host = ''
if getenv('HOSTS_USE_DEFAULT', False) == 'True':
    _host = 'DEFAULT'
    _caps = getenv('HOSTS_DEFAULT', None)
else:
    _host = MY_IP
    _caps = getenv('HOSTS_' + MY_IP, None)
    if _caps == None:
        print(' *** WARNING: Host capacities for ' + MY_IP + ' missing '
              'from conf.yml (even though USE_DEFAULT is False). '
              'Defaulting to HOSTS:DEFAULT.')
        _caps = getenv('HOSTS_DEFAULT', None)
if _caps == None:
    print(' *** ERROR: Default host capacities missing from conf.yml.')
    exit()
_caps = eval(_caps)

try:
    CPU = int(_caps['CPU'])
except:
    print(' *** ERROR: HOSTS:' + _host + ':CPU parameter invalid or missing '
          'from conf.yml.')
    exit()
try:
    RAM = int(_caps['RAM'])
except:
    print(' *** ERROR: HOSTS:' + _host + ':RAM parameter invalid or missing '
          'from conf.yml.')
    exit()
try:
    DISK = int(_caps['DISK'])
except:
    print(' *** ERROR: HOSTS:' + _host + ':DISK parameter invalid or missing '
          'from conf.yml.')
    exit()

# real monitoring config
SIM_ON = getenv('SIMULATION_ACTIVE', False) == 'True'
monitor = Monitor()
measures = monitor.measures
monitor_period = 0.1  # monitor.monitor_period
if not SIM_ON:
    # start monitor
    monitor.start()
    while 'cpu_count' not in measures:
        sleep(monitor_period)
    if CPU > measures['cpu_count']:
        print(' *** ERROR: Host cannot offer %d CPUs when it only has %d. '
              'Activate simulation to allow more resources than there really '
              'are.' % (CPU, measures['cpu_count']))
        monitor.stop()
        exit()
    while 'memory_total' not in measures:
        sleep(monitor_period)
    if RAM > measures['memory_total']:
        print(' *** ERROR: Host cannot offer %.2fMB of RAM when it only has '
              '%.2fMB. Activate simulation to allow more resources than '
              'there are available.' % (RAM, measures['memory_total']))
        monitor.stop()
        exit()
    while 'disk_total' not in measures:
        sleep(monitor_period)
    if DISK > measures['disk_total']:
        print(' *** ERROR: Host cannot offer %.2fGB of disk when it only has '
              '%.2fGB. Activate simulation to allow more resources than '
              'there are available.' % (DISK, measures['disk_total']))
        monitor.stop()
        exit()

# simulation variables of reserved resources
_reserved = {
    'cpu': 0,
    'ram': 0,  # in MB
    'disk': 0  # in GB
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


def _get_resources(quiet: bool = False):
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
        info('current(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (cpu, ram, disk))
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
        cpu, ram, disk = _get_resources(quiet)
        return (cpu >= min_cpu and ram >= min_ram and disk >= min_disk,
                cpu, ram, disk)


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

    sleep(uniform(SIM_EXEC_MIN, SIM_EXEC_MAX))
    return b'result'
