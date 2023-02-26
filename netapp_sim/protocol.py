from threading import Lock
from time import time

from scapy.all import (Packet, ByteField, StrLenField, IntField, 
                       ConditionalField, StrField, AnsweringMachine, sendp, 
                       Ether)

from simulator import (check_resources, reserve_resources, free_resources,
                       execute)
from consts import REQ_ID_LEN


def _req_id_len(_): return REQ_ID_LEN


_requests_lock = Lock()


# protocol states
HREQ = 1    # host request
HRES = 2    # host response
RREQ = 3    # resource reservation request
RRES = 4    # resource reservation response
DREQ = 5    # data exchange request
DRES = 6    # data exchange response
DACK = 7    # data exchange acknowledgement
FAIL = 0


class MyProtocol(Packet):
    name = 'MyProtocol'
    fields_desc = [
        ByteField('state', HREQ),
        StrLenField('req_id', b'', _req_id_len),
        IntField('cos_id', 0),
        ConditionalField(StrField('data', b''), 
                         lambda pkt: pkt.state == DREQ or pkt.state == DRES)
    ]

    def show(self, dump: bool = False, indent: int = 3, lvl: str = "",
             label_lvl: str = ""):
        print()
        return super().show(dump, indent, lvl, label_lvl)

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

    def is_request(self, req):
        return MyProtocol in req

    def make_reply(self, req):
        my_proto = req[MyProtocol]
        state = my_proto.state
        eth_src = req[Ether].src
        if state == HREQ:
            print('\nRecv host request from', eth_src)
            my_proto.show()
            if check_resources(my_proto.cos_id):
                print('Send host response to', eth_src, '\n')
                my_proto.state = HRES
                return Ether(dst=eth_src) / my_proto
            else:
                print('Insufficient')
        elif state == HRES:
            req_id = my_proto.req_id
            with _requests_lock:
                if not self._requests[req_id].host:
                    print('Recv first host response from', eth_src)
                    my_proto.show()
                    print('Send resource reservation request to', eth_src)
                    self._requests[req_id].host = eth_src
                    self._requests[req_id].state = HRES
                    self._requests[req_id].hres_at = time()
                    print(self._requests[req_id])
                    my_proto.state = RREQ
                    return Ether(dst=eth_src) / my_proto
        elif state == RREQ:
            print('Recv resource reservation request from', eth_src)
            my_proto.show()
            reserve_resources(my_proto.cos_id)
            print('Send resource reservation response to', eth_src, '\n')
            my_proto.state = RRES
            return Ether(dst=eth_src) / my_proto
        elif state == RRES:
            print('Recv resource reservation response from', eth_src)
            my_proto.show()
            print('Send data exchange request to', eth_src)
            req_id = my_proto.req_id
            self._requests[req_id].state = RRES
            self._requests[req_id].rres_at = time()
            print(self._requests[req_id])
            my_proto.state = DREQ
            my_proto.data = b'data + program'
            return Ether(dst=eth_src) / my_proto
        elif state == DREQ:
            print('Recv data exchange request from', eth_src)
            my_proto.show()
            execute(my_proto.data)
            print('Send data exchange response to', eth_src, '\n')
            my_proto.state = DRES
            my_proto.data = b'response'
            return Ether(dst=eth_src) / my_proto
        elif state == DRES:
            print('Recv data exchange response from', eth_src)
            my_proto.show()
            print('Send data exchange acknowledgement to', eth_src)
            req_id = my_proto.req_id
            self._requests[req_id].state = DRES
            self._requests[req_id].dres_at = time()
            print(self._requests[req_id])
            my_proto.state = DACK
            return Ether(dst=eth_src) / my_proto
        elif state == DACK:
            print('Recv data exchange acknowledgement from', eth_src)
            my_proto.show()
            free_resources(my_proto.cos_id)
            return
