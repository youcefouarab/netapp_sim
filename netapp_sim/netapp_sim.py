from threading import Thread
from random import choice
from string import ascii_letters, digits
from time import time
from datetime import datetime

from scapy.all import bind_layers, sendp, Ether, IP

from protocol import MyProtocol, MyProtocolAM, HREQ, HRES, RRES, DRES, FAIL
from monitor import Monitor
from consts import REQ_ID_LEN


BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'
BROADCAST_IP = '255.255.255.255'

_requests = {'_': None}  # '_' is placeholder

_states = {
    HREQ: 'waiting',
    HRES: 'started',
    RRES: 'pending',
    DRES: 'finshed',
    FAIL: 'failed'
}

_t = datetime.fromtimestamp


def _generate_request_id():
    id = '_'
    while id in _requests:
        id = ''.join(choice(ascii_letters + digits) for _ in range(REQ_ID_LEN))
    return id.encode()


class Request:
    def __init__(self, req_id: bytes, cos_id: int):
        self.req_id = req_id
        self.state = HREQ
        self.cos_id = cos_id
        self.host = ''
        self.hreq_at = time()   # timestamp of sending host request
        self.hres_at = 0        # timestamp of receiving first host response
        self.rres_at = 0        # timestamp of receiving resource reservation response
        self.dres_at = 0        # timestamp of receiving data exchange response

    def __repr__(self):
        return ('\nrequest(req_id=%s, state=%s, cos_id=%d, host=%s, '
                'hreq_at=%s, hres_at=%s, rres_at=%s, dres_at=%s)\n' % (
                    self.req_id.decode(), _states[self.state], self.cos_id, 
                    self.host, _t(self.hreq_at), _t(self.hres_at), 
                    _t(self.rres_at), _t(self.dres_at)))


def request_host(cos_id: int):
    print('Send host request')
    req_id = _generate_request_id()
    _requests[req_id] = Request(req_id, cos_id)
    print(Request(req_id, cos_id))
    sendp(Ether(dst=BROADCAST_MAC)
          / IP(dst=BROADCAST_IP)
          / MyProtocol(state=HREQ, req_id=req_id, cos_id=cos_id), verbose=0)


# for testing
if __name__ == '__main__':
    bind_layers(IP, MyProtocol)
    bind_layers(Ether, MyProtocol)
    Monitor().start()
    Thread(target=MyProtocolAM(_requests=_requests, verbose=0)).start()
    print('\nClick ENTER to send a request\nOr wait to receive requests\n')
    while True:
        input()
        request_host(cos_id=2)
