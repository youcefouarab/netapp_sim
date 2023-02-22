from threading import Thread
from random import choice
from string import ascii_letters, digits
from time import time

from scapy.all import bind_layers, sendp, Ether, IP

from protocol import MyProtocol, MyProtocolAM, HREQ
from consts import *


_requests = {'_': None}  # '_' is for reference when generating IDs


def _generate_request_id():
    id = '_'
    while id in _requests:
        id = ''.join(choice(ascii_letters + digits) for _ in range(REQ_ID_LEN))
    return id.encode()


class Request:
    def __init__(self, cos_id: int):
        self.cos_id = cos_id
        self.host = None
        self.state = WAITING
        self.waiting_at = time()
        self.starting_at = None
        self.pending_at = None
        self.finished_at = None


def request_host(cos_id: int):
    req_id = _generate_request_id()
    _requests[req_id] = Request(cos_id)
    sendp(Ether(dst=BROADCAST_MAC)
          / IP(dst=BROADCAST_IP)
          / MyProtocol(state=HREQ, req_id=req_id, cos_id=cos_id))


if __name__ == '__main__':
    bind_layers(Ether, MyProtocol)
    Thread(target=MyProtocolAM(_requests=_requests)).start()
    request_host(cos_id=2)
