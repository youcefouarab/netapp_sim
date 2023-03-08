'''
    This module simulates checking, reserving and freeing resources for, as 
    well as execution of, network applications based on requirements of their 
    Class of Service (CoS). It can be considered a proxy of monitor, applying 
    a filter to real measurements (of CPU, RAM, and disk) to get simulated 
    ones.

    Methods:
    --------
    check_resources(cos_id): Returns True if current resources can satisfy 
    requirements of CoS identified by cos_id, False if not.
    
    reserve_resources(cos_id): Add quantity of resources to be reserved to 
    simulation variables.
    
    free_resources(cos_id): Subtract quantity of reserved resource from 
    simulation variables.

    execute(data): Simulate execution of network application by doing nothing 
    for a determined period of time (by default randomly generated between 0s 
    and 1s).
'''


from threading import Lock
from random import uniform
from time import sleep

from monitor import Monitor
from model import CoS


_reserved = {  # simulation variables of reserved resources
    'cpu': 0,
    'ram': 0,  # in MB
    'disk': 0  # in GB
}
_reserved_lock = Lock()  # for thread safety

EXEC_T_MIN = 0
EXEC_T_MAX = 1


# start monitor
monitor = Monitor()
monitor.start()

# get all CoS (for time optimization)
cos_dict = {cos.id: cos for cos in CoS.fetch()}


def _get_resources(quiet: bool = False):
    measures = monitor.measures
    cpu = measures['cpu_count'] - _reserved['cpu']
    ram = measures['memory_free'] - _reserved['ram']
    disk = measures['disk_free'] - _reserved['disk']
    if not quiet:
        print('current(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (cpu, ram, disk))
    return cpu, ram, disk


def check_resources(cos_id: int, quiet: bool = False):
    '''
        Returns True if current resources can satisfy requirements of CoS 
        identified by cos_id, False if not.
    '''
    with _reserved_lock:
        try:
            cos: CoS = cos_dict[cos_id]
        except:
            return False
            # TODO manage exception
        else:
            min_cpu = cos.get_min_cpu()
            min_ram = cos.get_min_ram()
            min_disk = cos.get_min_disk()
            if not quiet:
                print('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (
                    min_cpu, min_ram, min_disk))
            cpu, ram, disk = _get_resources(quiet)
            return cpu >= min_cpu and ram >= min_ram and disk >= min_disk


def reserve_resources(cos_id: int):
    '''
        Add quantity of resources to be reserved to simulation variables.

        Returns True if reserved, False if not.
    '''
    with _reserved_lock:
        try:
            cos: CoS = cos_dict[cos_id]
        except:
            return False
            # TODO manage exception
        else:
            min_cpu = cos.get_min_cpu()
            min_ram = cos.get_min_ram()
            min_disk = cos.get_min_disk()
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


def free_resources(cos_id: int):
    '''
        Subtract quantity of reserved resource from simulation variables.

        Returns True if freed, False if not.
    '''
    with _reserved_lock:
        try:
            cos: CoS = cos_dict[cos_id]
        except:
            return False
            # TODO manage exception
        else:
            _reserved['cpu'] -= cos.get_min_cpu()
            if _reserved['cpu'] < 0:
                _reserved['cpu'] = 0
            _reserved['ram'] -= cos.get_min_ram()
            if _reserved['ram'] < 0:
                _reserved['ram'] = 0
            _reserved['disk'] -= cos.get_min_disk()
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
