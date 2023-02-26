from random import uniform
from time import sleep

from monitor import Monitor
from model import CoS


_r = {          # simulation of reserved resources
    'cpu': 0,
    'ram': 0,   # in MB
    'disk': 0   # in GB
}


def _get_resources():
    m = Monitor().measures
    cpu = m['cpu_count'] - _r['cpu']
    ram = m['memory_free'] - _r['ram']
    disk = m['disk_free'] - _r['disk']
    print('current(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (cpu, ram, disk))
    return cpu, ram, disk


def check_resources(cos_id: int):
    print('Checking resources... ')
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        min_cpu = cos.get_min_cpu()
        min_ram = cos.get_min_ram()
        min_disk = cos.get_min_disk()
        print('required(cpu=%d, ram=%.2fMB, disk=%.2fGB)' % (min_cpu, min_ram,
              min_disk))
        cpu, ram, disk = _get_resources()
        return cpu >= min_cpu and ram >= min_ram and disk >= min_disk
    except:
        return False
        # TODO manage exception


def reserve_resources(cos_id: int):
    print('Reserving resources')
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        _r['cpu'] += cos.get_min_cpu()
        _r['ram'] += cos.get_min_ram()
        _r['disk'] += cos.get_min_disk()
        _get_resources()
    except:
        return False
        # TODO manage exception


def execute(data):
    print('Execution')
    sleep(uniform(0, 1))
    return


def free_resources(cos_id: int):
    print('Freeing resources')
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        _r['cpu'] -= cos.get_min_cpu()
        _r['ram'] -= cos.get_min_ram()
        _r['disk'] -= cos.get_min_disk()
        _get_resources()
    except:
        return False
        # TODO manage exception
