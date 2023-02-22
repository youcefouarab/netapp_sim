from threading import Lock

from scapy.all import (FieldLenField, Scapy_Exception, Packet, ByteField,
                       StrLenField, IntField, AnsweringMachine, sendp, Ether)

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


class VariableFieldLenField(FieldLenField):
    def addfield(self, pkt, s, val):
        val = self.i2m(pkt, val)
        data = []
        while val:
            if val > 127:
                data.append(val & 127)
                val /= 127
            else:
                data.append(val)
                lastoffset = len(data) - 1
                data = "".join(chr(val | (0 if i == lastoffset else 128))
                               for i, val in enumerate(data))
                return s + data
            if len(data) > 3:
                raise Scapy_Exception("%s: malformed length field" %
                                      self.__class__.__name__)

    def getfield(self, pkt, s):
        value = 0
        for offset, curbyte in enumerate(s):
            curbyte = ord(curbyte)
            value += (curbyte & 127) * (128 ** offset)
            if curbyte & 128 == 0:
                return s[offset + 1:], value
            if offset > 2:
                raise Scapy_Exception("%s: malformed length field" %
                                      self.__class__.__name__)


class MyProtocol(Packet):
    name = 'MyProtocol'
    fields_desc = [
        ByteField('state', HREQ),
        StrLenField('req_id', '', _req_id_len),
        IntField('cos_id', 0),
        #VariableFieldLenField('len', 0, length_of='data'),
        #StrLenField('data', '', length_from=lambda pkt: pkt.len),
    ]


class MyProtocolAM(AnsweringMachine):
    function_name = 'mpam'
    sniff_options = {'filter': 'inbound'}
    send_function = staticmethod(sendp)

    def parse_options(self, _requests={'_': None}):
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
            my_proto.state = RRES
            return Ether(dst=req[Ether].src) / my_proto


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


def free_resources(cos_id: int):
    try:
        cos: CoS = CoS.fetch(id=('=', cos_id))[0]
        _r['cpu'] -= cos.get_min_cpu()
        _r['ram'] -= cos.get_min_ram()
        _r['disk'] -= cos.get_min_disk()
    except:
        return False
        # TODO manage exception
