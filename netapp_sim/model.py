'''
    This module includes classes used to model Classes of Service (CoS) and 
    their requirements, as well as network application hosting requests.

    Classes:
    --------
    Model: Base class for all model classes.

    CoSSpecs: Set of minimum specs required to host network applications 
    belonging to Class of Service.

    CoS: Class of Service.

    Request: Network application hosting request.
'''


from time import time
from datetime import datetime
from string import ascii_letters, digits
from random import choice

from consts import HREQ, RREQ, DREQ, DRES, FAIL, REQ_ID_LEN, requests


class Model:
    '''
        Base class for all model classes.

        Methods:
        --------
        as_dict(flat): Converts object to dictionary and returns it. If flat 
        is False, nested objects will become nested dictionaries; otherwise, 
        all attributes in nested objects will be in parent dictionary.

        save(): Insert as row in database table.

        update(): Update row from object.

        fetch(): Fetch row(s) from database table.

        as_csv(): Convert database table to CSV file.
    '''

    def as_dict(self, flat: bool = False, _prefix: str = ''):
        '''
            Converts object to a dictionary and returns it. If flat is False, 
            nested objects will become nested dictionaries; otherwise, all 
            attributes in nested objects will be in parent dictionary.

            To avoid name conflicts when flat is True, nested attribute name 
            will be prefixed: <parent_attribute_name>_<nested_attribute_name> 
            (example: Request.cos.id will become cos_id).
        '''

        if flat and _prefix:
            _prefix += '_'
        return {_prefix + str(key): val for key, val in self.__dict__.items()}

    # the following methods are for database operations

    def save(self):
        '''
            Insert as row in database table.

            Returns True if inserted, False if not.
        '''

        from dblib import save
        return save(self)

    def update(self, _id: str = 'id'):
        '''
            Update row from obj.

            Return True if updated, False if not.
        '''

        from dblib import update
        return update(self, _id)

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

    @classmethod
    def as_csv(cls, **kwargs):
        '''
            Convert database table to CSV file.

            Filters can be applied through kwargs. Example:

                >>> Request.as_csv(host=('=', 10.0.0.2))

            Returns True if converted, False if not.
        '''

        from dblib import as_csv
        return as_csv(cls, **kwargs)


class CoSSpecs(Model):
    '''
        Set of minimum specs required to host network applications belonging 
        to Class of Service.

        Attributes:
        -----------
        max_response_time: default is inf
        min_concurrent_users: default is 0
        min_requests_per_second: default is 0
        min_bandwidth: default is 0
        max_delay: default is inf
        max_jitter: default is inf
        max_loss_rate: default is 1
        min_cpu: default is 0
        min_ram: default is 0
        min_disk: default is 0
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

        Recommendation: use provided getters and setters for specs in case 
        their structure changes in future updates.

        Attributes:
        -----------
        id: CoS ID.

        name: CoS name.

        specs: CoSSpecs object.
    '''

    def __init__(self, id: int, name: str, specs: CoSSpecs = None):
        self.id = id
        self.name = name
        if not specs:
            specs = CoSSpecs()
        self.specs = specs

    def as_dict(self, flat: bool = False, _prefix: str = ''):
        d = super().as_dict(flat, _prefix)
        if not flat:
            d['specs'] = self.specs.as_dict()
        else:
            if _prefix:
                _prefix += '_'
            del d[_prefix + 'specs']
            d.update(self.specs.as_dict(flat, _prefix=_prefix+'specs'))
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


class Request(Model):
    '''
        Network application hosting request.

        Attributes:
        -----------
        id: Request ID.

        cos: CoS object of required Class of Service.

        data: Input data bytes.

        result: Execution result bytes.

        host: Network application host IP address.

        state: Request state, enumeration of HREQ (1) (waiting for host), RREQ 
        (3) (waiting for resources), DREQ (6) (waiting for data), DRES (7) 
        (finished), FAIL (0) (failed). Default is HREQ (1).

        hreq_at: Host request timestamp. Default is object creation time.

        hres_at: First host response timestamp.

        rres_at: Resource reservation response timestamp.

        dres_at: Data exchange response timestamp.
    '''

    _states = {
        HREQ: 'waiting for host',
        RREQ: 'waiting for resources',
        DREQ: 'waiting for data',
        DRES: 'finished',
        FAIL: 'failed'
    }

    def __init__(self, cos: CoS, data: bytes):
        self.id = self._generate_request_id()
        self.cos = cos
        self.data = data
        self.result = None
        self.host = None
        self.state = HREQ
        self.hreq_at = time()
        self.hres_at = None
        self.rres_at = None
        self.dres_at = None
        self._late = False

    def _t(self, x):
        return datetime.fromtimestamp(x) if x != None else x

    def __repr__(self):
        return ('\nrequest(id=%s, state=(%s), cos=%s, host=%s, hreq_at=%s, '
                'hres_at=%s, rres_at=%s, dres_at=%s)\n' % (
                    self.id, self._states[self.state], self.cos.name,
                    self.host, self._t(self.hreq_at), self._t(self.hres_at),
                    self._t(self.rres_at), self._t(self.dres_at)))

    def as_dict(self, flat: bool = False):
        d = super().as_dict(flat)
        del d['_late']
        if not flat:
            d['cos'] = self.cos.as_dict()
        else:
            del d['cos']
            d.update(self.cos.as_dict(flat, _prefix='cos'))
        return d

    def _generate_request_id(self):
        id = '_'
        while id in requests:
            id = ''.join(
                choice(ascii_letters + digits) for _ in range(REQ_ID_LEN))
        return id

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
