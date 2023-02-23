from threading import Lock
from random import uniform
from time import sleep

from scapy.all import (Packet, ByteField, StrLenField, IntField, StrField, 
                       AnsweringMachine, sendp, Ether)

from monitor import Monitor
from model import CoS
from consts import *


_req_id_len = lambda x: REQ_ID_LEN


_requests_lock = Lock()

_r = {          # simulation of reserved resources
    'cpu': 0,
    'ram': 0,   # in MB
    'disk': 0   # in GB
}

# protocol states
HREQ = 1    # host request
HRES = 2    # host response
RREQ = 3    # resource reservation request
RRES = 4    # resource reservation response
DREQ = 5    # data exchange request
DRES = 6    # data exchange response
DACK = 7    # data exchange acknowledgement


class MyProtocol(Packet):
    name = 'MyProtocol'
    fields_desc = [
        ByteField('state', HREQ),
        StrLenField('req_id', b'', _req_id_len),
        IntField('cos_id', 0),
        StrField('data', b'')
    ]

    def hashret(self):
        return self.req_id

    def answers(self, other):
        if other.state == HREQ and self.state == HRES:
            return 1
        if other.state == RREQ and self.state == RRES:
            return 1
        if other.state == DREQ and self.state == DRES:
            return 1
        return 0


class MyProtocolAM(AnsweringMachine):
    function_name = 'mpam'
    sniff_options = {'filter': 'inbound'}
    send_function = staticmethod(sendp)

    def parse_options(self, _requests: dict = {'_': None}):
        self._requests = _requests

    def is_request(self, req: Packet):
        return MyProtocol in req

    def make_reply(self, req: Packet):
        req.show()
        my_proto = req[MyProtocol]
        state = my_proto.state
        if state == HREQ:
            if check_resources(my_proto.cos_id):
                my_proto.state = HRES
                return Ether(dst=req[Ether].src) / my_proto
        elif state == HRES:
            eth_src = req[Ether].src
            req_id = my_proto.req_id
            with _requests_lock:
                if self._requests[req_id].host == None:
                    self._requests[req_id].host = eth_src
                    my_proto.state = RREQ
                    return Ether(dst=req[Ether].src) / my_proto
        elif state == RREQ:
            reserve_resources(req[MyProtocol].cos_id)
            my_proto.state = RRES
            return Ether(dst=req[Ether].src) / my_proto
        elif state == RRES:
            my_proto.state = DREQ
            my_proto.data = b'data + program'
            return Ether(dst=req[Ether].src) / my_proto
        elif state == DREQ:
            execute(my_proto.data)
            my_proto.state = DRES
            my_proto.data = b'response'
            return Ether(dst=req[Ether].src) / my_proto
        elif state == DRES:
            self._requests.pop(req[MyProtocol].req_id)
            my_proto.data = b''
            my_proto.state = DACK
            return Ether(dst=req[Ether].src) / my_proto
        elif state == DACK:
            free_resources(req[MyProtocol].cos_id)
            return


def check_resources(cos_id: int):
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        m = Monitor().measures
        return (m['cpu_count'] - _r['cpu'] >= cos.get_min_cpu()
                and m['memory_free'] - _r['ram'] >= cos.get_min_ram()
                and m['disk_free'] - _r['disk'] >= cos.get_min_disk())
    except:
        return False
        # TODO manage exception


def reserve_resources(cos_id: int):
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        _r['cpu'] += cos.get_min_cpu()
        _r['ram'] += cos.get_min_ram()
        _r['disk'] += cos.get_min_disk()
    except:
        return False
        # TODO manage exception


def execute(data):
    sleep(uniform(0, 1))
    return


def free_resources(cos_id: int):
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        _r['cpu'] -= cos.get_min_cpu()
        _r['ram'] -= cos.get_min_ram()
        _r['disk'] -= cos.get_min_disk()
    except:
        return False
        # TODO manage exception
