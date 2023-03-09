'''
    This module defines the communication protocol between hosts, including 
    the packets' header and the protocol's responder.

    Classes:
    --------
    Request: This class is used to save information on requests sent by 
    consumers and to track their states.

    MyProtocol: This class defines the communication protocol between hosts, 
    including the packet header's fields, as well as ways to detect if a packet 
    is an answer to another.

    MyProtocolAM: This class defines the protocol's responder (Answering 
    Machine), which takes decisions and builds and sends replies to received 
    packets based on the protocol's state.

    Methods:
    --------
    send_request(cos_id, data): Send a request to host and execute a network 
    application of Class of Service (CoS) identified by cos_id, with data as 
    input.
'''


from threading import Thread
from time import time
from datetime import datetime
from string import ascii_letters, digits
from random import choice

from scapy.all import (Packet, ByteEnumField, StrLenField, IntEnumField,
                       StrField, ConditionalField, AnsweringMachine, conf,
                       bind_layers, send, srp1, sr1, sniff, Ether, IP)

from simulator import (check_resources, reserve_resources, free_resources,
                       execute)
from model import CoS


# protocol states
HREQ = 1    # host request
HRES = 2    # host response
RREQ = 3    # resource reservation request
RRES = 4    # resource reservation response
RCAN = 5    # resource reservation cancellation
DREQ = 6    # data exchange request
DRES = 7    # data exchange response
DACK = 8    # data exchange acknowledgement
DCAN = 9    # data exchange cancellation
DWAIT = 10  # data exchange wait
FAIL = 0

# protocol timeouts and retries
HREQ_TO = 1
HREQ_RT = 3

RREQ_TO = 1
RREQ_RT = 3

RRES_TO = 1
RRES_RT = 3

DREQ_TO = 1
DREQ_RT = 3

DRES_TO = 1
DRES_RT = 3

# misc. consts
REQ_ID_LEN = 10
BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'
BROADCAST_IP = '255.255.255.255'

# dict of requests sent by consumer
requests = {'_': None}  # '_' is placeholder

# dict of requests received by provider
_requests = {}

# dict of CoS id -> name
_cos = {cos.id: cos.name for cos in CoS.fetch()}


class Request:  # used by consumer
    '''
        This class is used to save information on requests sent by consumers 
        and to track their states.

        Attributes:
        -----------
        req_id: Unique ID of request (by default a string of 10 characters 
        randomly generated from ASCII letters and digits).

        cos_id: ID of the required CoS.

        state: State of request, enumeration of HREQ (1) (waiting for host), 
        RREQ (3) (waiting for resources), DREQ (6) (waiting for data), DRES (7) 
        (finished), FAIL (0) (failed).

        host: IP of host selected to execute request.

        data: Bytes containing input data, and possibly the program to execute
        by the selected host.

        result: Bytes containing received execution result.

        hreq_at: Timestamp of sending host request.

        hres_at: Timestamp of receiving first host response.

        rres_at: Timestamp of receiving resource reservation response.

        dres_at: Timestamp of receiving data exchange response.
    '''

    _states = {
        HREQ: 'waiting for host',
        RREQ: 'waiting for resources',
        DREQ: 'waiting for data',
        DRES: 'finished',
        FAIL: 'failed'
    }

    def __init__(self, cos_id: int, data: bytes):
        self.req_id = self._generate_request_id()
        self.cos_id = cos_id
        self.state = HREQ
        self.host = None
        self.data = data
        self.result = None
        self.hreq_at = time()
        self.hres_at = None
        self.rres_at = None
        self.dres_at = None
        self._late = False

    def _t(self, x):
        return datetime.fromtimestamp(x) if x != None else ''

    def __repr__(self):
        return ('\nrequest(req_id=%s, state=(%s), cos=%s, host=%s, '
                'hreq_at=%s, hres_at=%s, rres_at=%s, dres_at=%s)\n' % (
                    self.req_id, self._states[self.state], _cos[self.cos_id], 
                    self.host, self._t(self.hreq_at), self._t(self.hres_at), 
                    self._t(self.rres_at), self._t(self.dres_at)))

    def _generate_request_id(self):
        id = '_'
        while id in requests:
            id = ''.join(
                choice(ascii_letters + digits) for _ in range(REQ_ID_LEN))
        return id


class _Request:  # used by provider
    def __init__(self, req_id: bytes):
        self.req_id = req_id
        self.cos_id = 1
        self.state = HREQ
        self.thread = None
        self.result = None
        self._freed = False


class MyProtocol(Packet):
    '''
        This class defines the communication protocol between hosts, including 
        the packet header's fields, as well as ways to detect if a packet is 
        an answer to another.

        Fields:
        -------
        state: 1 byte indicating the state of the protocol, enumeration of 
        HREQ (1) (host request), HRES (2) (host response), RREQ (3) (resource 
        reservation request), RRES (4) (resource reservation response), RCAN 
        (5) (resource reservation cancellation), DREQ (6) (data exchange 
        request), DRES (7) (data exchange response), DACK (8) (data exchange 
        acknowledgement), DCAN (9) (data exchange cancellation), DWAIT (10) 
        (data exchange wait).

        req_id: String of 10 bytes indicating the request's ID.

        cos_id: Integer of 4 bytes indicating the application's CoS ID, by 
        default is 1 (best-effort). Conditional field for state == HREQ (1).

        data: String of undefined number of bytes containing input data and 
        possibly program to execute. Conditional field for state == DREQ (6) 
        or state == DRES (7).
    '''

    _states = {
        HREQ: 'host request (HREQ)',
        HRES: 'host response (HRES)',
        RREQ: 'resource reservation request (RREQ)',
        RRES: 'resource reservation response (RRES)',
        RCAN: 'resource reservation cancellation (RCAN)',
        DREQ: 'data exchange request (DREQ)',
        DRES: 'data exchange response (DRES)',
        DACK: 'data exchange acknowledgement (DACK)',
        DCAN: 'data exchange cancellation (DCAN)',
        DWAIT: 'data exchange wait (DWAIT)',
    }

    name = 'MyProtocol'
    fields_desc = [
        ByteEnumField('state', HREQ, _states),
        StrLenField('req_id', '', lambda _: REQ_ID_LEN),
        ConditionalField(IntEnumField('cos_id', 0, _cos),
                         lambda pkt: pkt.state == HREQ),
        ConditionalField(StrField('data', ''),
                         lambda pkt: pkt.state == DREQ or pkt.state == DRES)
    ]

    def show(self):
        print()
        return super().show()

    def hashret(self):
        return self.req_id

    def answers(self, other):
        if not isinstance(other, MyProtocol):
            return 0
        # host request expects host response
        if (other.state == HREQ and self.state == HRES
            # resource reservation request expects resource reservation
            # response or resource reservation cancellation
            or other.state == RREQ and (self.state == RRES
                                        or self.state == RCAN)
            # resource reservation response expects data exchange request
            # or resource reservation cancellation
            or other.state == RRES and (self.state == DREQ
                                        or self.state == RCAN)
            # data exchange request expects data exchange response, data
            # exchange wait, or data exchange cancellation
            or other.state == DREQ and (self.state == DRES
                                        or self.state == DWAIT
                                        or self.state == DCAN)
            # data exchange response expects data exchange acknowledgement
            # or data exchange cancellation
            or other.state == DRES and (self.state == DACK
                                        or self.state == DCAN)):
            return 1
        return 0


# for scapy to be able to dissect MyProtocol packets
# bind_layers(Ether, MyProtocol)
bind_layers(IP, MyProtocol)

# IP broadcast fails when the following are true (responses are not received)
conf.checkIPaddr = False
conf.checkIPsrc = False
# making them false means IP src must be checked manually


class MyProtocolAM(AnsweringMachine):
    '''
        This class defines the protocol's responder (Answering Machine), which 
        takes decisions and builds and sends replies to received packets based 
        on the protocol's state.
    '''

    function_name = 'mpam'
    sniff_options = {'filter': 'inbound'}
    send_function = staticmethod(send)

    def is_request(self, req):
        # a packet must have Ether, IP and MyProtocol layers
        return (Ether in req and IP in req and MyProtocol in req
                # and no other layer
                and not any((layer is not Ether
                             and layer is not IP
                             and layer is not MyProtocol)
                            for layer in req.layers())
                # and must have an ID
                and req[MyProtocol].req_id != '')

    def make_reply(self, req):
        my_proto = req[MyProtocol]
        ip_src = req[IP].src
        req_id = my_proto.req_id
        _req_id = (ip_src, req_id)
        state = my_proto.state

        # provider receives host request
        if state == HREQ:
            # if new request
            if _req_id not in _requests:
                _requests[_req_id] = _Request(_req_id)
            # if not old request that was cancelled
            if (_requests[_req_id].state == HREQ
                    or _requests[_req_id].state == HRES):
                print('Recv host request from', ip_src)
                my_proto.show()
                # set cos_id (for new requests and in case cos_id was changed
                # for old request)
                _requests[_req_id].cos_id = my_proto.cos_id
                print('Checking resources')
                if check_resources(my_proto.cos_id):
                    print('Send host response to', ip_src)
                    _requests[_req_id].state = HRES
                    my_proto.state = HRES
                    return IP(dst=ip_src) / my_proto
                else:
                    print('Insufficient')
                    _requests[_req_id].state = HREQ
            return

        # provider receives resource reservation request
        if state == RREQ and _req_id in _requests:
            # host request must have already been answered positively
            # but not yet reserved
            if _requests[_req_id].state == HRES:
                print('Recv resource reservation request from', ip_src)
                my_proto.show()
                print('Reserving resources')
                # if resources are actually reserved
                if reserve_resources(_requests[_req_id].cos_id):
                    _requests[_req_id].state = RRES
                # else they became no longer sufficient in time between
                # HREQ and RREQ
                else:
                    print('Resources are no longer sufficient')
                    print('Send resource reservation cancellation to', ip_src)
                    _requests[_req_id].state = HREQ
                    my_proto.state = RCAN
                    return IP(dst=ip_src) / my_proto
            # if resources reserved
            if _requests[_req_id].state == RRES:
                Thread(target=self._respond_resources,
                       args=(my_proto, ip_src,)).start()
            return

        # consumer receives late resource reservation response
        if (state == RRES and req_id in requests
                # from a previous host
                and ip_src != requests[req_id].host):
            print('Recv resource reservation response from', ip_src)
            my_proto.show()
            # cancel with previous host
            print('Send resource reservation cancellation to', ip_src)
            my_proto.state = RCAN
            return IP(dst=ip_src) / my_proto

        # provider receives data exchange request
        if state == DREQ and _req_id in _requests:
            # already executed
            if _requests[_req_id].state == DRES:
                my_proto.state = DRES
                my_proto.data = _requests[_req_id].result
                return IP(dst=ip_src) / my_proto
            # still executing
            if (_requests[_req_id].state == RRES
                    and _requests[_req_id].thread != None):
                my_proto.state = DWAIT
                return IP(dst=ip_src) / my_proto
            print('Recv data exchange request from', ip_src)
            my_proto.show()
            # if request was cancelled before
            if _requests[_req_id].state == HREQ:
                print('This request arrived late, ', end='')
                # if resources are still available
                if check_resources(_requests[_req_id].cos_id, quiet=True):
                    print('but resources are still available')
                    print('Reserving resources')
                    reserve_resources(_requests[_req_id].cos_id)
                    _requests[_req_id].state = RRES
                else:
                    print('and resources are no longer sufficient')
                    print('Send data exchange cancellation to', ip_src)
                    _requests[_req_id].state = HREQ
                    my_proto.state = DCAN
                    return IP(dst=ip_src) / my_proto
            # new execution
            if _requests[_req_id].state == RRES:
                th = Thread(target=self._respond_data,
                            args=(my_proto, ip_src,))
                _requests[_req_id].thread = th
                th.start()
            return

        # consumer receives late data exchange response
        if state == DRES and req_id in requests:
            # if no other response was already accepted
            if not requests[req_id].dres_at:
                #  if response from previous host, accept
                if ip_src != requests[req_id].host and requests[req_id]._late:
                    requests[req_id].dres_at = time()
                    requests[req_id].state = DRES
                    requests[req_id].host = ip_src
                    requests[req_id].result = my_proto.data
                    print('Recv late data exchange response from', ip_src)
                    my_proto.show()
                    print('Send data exchange acknowledgement to', ip_src)
                    my_proto.state = DACK
                    return IP(dst=ip_src) / my_proto
                return
            # if response already received
            else:
                print('Recv late data exchange response from', ip_src)
                my_proto.show()
                print('but result already received')
                #  if different host, cancel
                if ip_src != requests[req_id].host:
                    print('Send data exchange cancellation to', ip_src)
                    my_proto.state = DCAN
                # if same host, acknowledge
                else:
                    print('Send data exchange acknowledgement to', ip_src)
                    my_proto.state = DACK
                return IP(dst=ip_src) / my_proto

        # provider receives data exchange acknowledgement
        if (state == DACK and _req_id in _requests
                and _requests[_req_id].state == DRES):
            print('Recv data exchange acknowledgement from', ip_src)
            my_proto.show()
            # only free resources if still reserved
            if not _requests[_req_id]._freed:
                print('Freeing resources')
                free_resources(_requests[_req_id].cos_id)
                _requests[_req_id]._freed = True

    def _respond_resources(self, my_proto, ip_src):
        _req_id = (ip_src, my_proto.req_id)
        my_proto.state = RRES
        retries = RRES_RT
        dreq = None
        while not dreq and retries and _requests[_req_id].state == RRES:
            print('Send resource reservation response to', ip_src)
            retries -= 1
            dreq = sr1(IP(dst=ip_src) / my_proto, timeout=RRES_TO, verbose=0)
            if dreq and dreq[MyProtocol].state == RCAN:
                print('Recv resource reservation cancellation from', ip_src)
                my_proto.show()
                _requests[_req_id].state = HREQ
                print('Freeing resources')
                free_resources(_requests[_req_id].cos_id)
                return
        # only free resources if still reserved
        if not dreq and _requests[_req_id].state == RRES:
            print('Waiting for data exchange request timed out')
            print('Freeing resources')
            free_resources(_requests[_req_id].cos_id)
            _requests[_req_id].state = HREQ
            my_proto.state = RCAN
            send(IP(dst=ip_src) / my_proto, verbose=0)

    def _respond_data(self, my_proto, ip_src):
        print('Executing')
        res = execute(my_proto.data)
        _req_id = (ip_src, my_proto.req_id)
        # save result locally
        _requests[_req_id].result = res
        _requests[_req_id].state = DRES
        my_proto.state = DRES
        my_proto.data = res
        retries = DRES_RT
        dack = None
        while not dack and retries:
            print('Send data exchange response to', ip_src)
            retries -= 1
            dack = sr1(IP(dst=ip_src) / my_proto, timeout=DRES_TO, verbose=0)
            if dack and dack[MyProtocol].state == DCAN:
                print('Recv data exchange cancellation from', ip_src)
                # only free resources if still reserved
                if not _requests[_req_id]._freed:
                    print('Freeing resources')
                    free_resources(_requests[_req_id].cos_id)
                    _requests[_req_id]._freed = True
                    return
        if not dack:
            print('Waiting for data exchange acknowledgement timed out')
            # only free resources if still reserved
            if not _requests[_req_id]._freed:
                print('Freeing resources')
                free_resources(_requests[_req_id].cos_id)
                _requests[_req_id]._freed = True


# start the answering machine
MyProtocolAM(verbose=0)(bg=True)


def send_request(cos_id: int, data: bytes):
    '''
        Send a request to host and execute a network application of Class of 
        Service (CoS) identified by cos_id, with data as input.
    '''
    req = Request(cos_id, data)
    req_id = req.req_id
    requests[req_id] = req

    hreq_rt = HREQ_RT
    hres = None

    # dres_at is checked throughout in case of late dres from another host

    while not hres and hreq_rt and not req.dres_at:
        req.host = ''
        req.state = HREQ
        req.hres_at = None
        print('Send host request')
        print(req)
        hreq_rt -= 1
        # send broadcast and wait for first response
        hres = srp1(Ether(dst=BROADCAST_MAC)
                    / IP(dst=BROADCAST_IP)
                    / MyProtocol(state=HREQ, req_id=req_id, cos_id=req.cos_id),
                    timeout=HREQ_TO, verbose=0)
        if hres and not req.dres_at:
            req.hres_at = time()
            req.state = RREQ
            req.host = hres[IP].src
            print('Recv first host response from', req.host)
            hres[MyProtocol].show()

            hreq_rt = HREQ_RT
            rreq_rt = RREQ_RT
            rres = None
            while not rres and rreq_rt and not req.dres_at:
                req.rres_at = None
                print('Send resource reservation request to', req.host)
                print(req)
                rreq_rt -= 1
                # send and wait for response
                rres = sr1(IP(dst=req.host)
                           / MyProtocol(state=RREQ, req_id=req_id),
                           timeout=RREQ_TO, verbose=0)
                if rres and not req.dres_at:
                    # if late response from previous host
                    # cancel (in MyProtocolAM)
                    # and wait for rres from current host
                    if rres[IP].src != req.host:
                        try:
                            rres = sniff(
                                lfilter=(lambda pkt: (
                                    IP in pkt
                                    and pkt[IP].src == req.host
                                    and MyProtocol in pkt
                                    and pkt[MyProtocol].req_id == req_id
                                    and (pkt[MyProtocol].state == RRES
                                         or pkt[MyProtocol].state == RCAN))),
                                filter='inbound', count=1, timeout=RREQ_TO)[0]
                        except:
                            rres = None
                            continue
                    # if cancelled from provider (maybe resources became no
                    # longer sufficient between hres and rreq)
                    if rres[MyProtocol].state == RCAN:
                        print('Recv resource reservation cancellation from',
                              req.host)
                        rres[MyProtocol].show()
                        # re-send hreq
                        continue
                    req.rres_at = time()
                    req.state = DREQ
                    print('Recv resource reservation response from', req.host)
                    rres[MyProtocol].show()

                    dreq_rt = DREQ_RT
                    dres = None
                    while not dres and dreq_rt and not req.dres_at:
                        print('Send data exchange request to', req.host)
                        print(req)
                        dreq_rt -= 1
                        # send and wait for response
                        dres = sr1(IP(dst=req.host)
                                   / MyProtocol(state=DREQ, req_id=req_id,
                                                data=data),
                                   timeout=DREQ_TO, verbose=0)
                        if dres and not req.dres_at:
                            # if still executing, wait
                            if (dres[IP].src == req.host
                                    and dres[MyProtocol].state == DWAIT):
                                dreq_rt = DREQ_RT
                                print(req_id.decode(), 'still executing')
                            # if response from previous host
                            # let MyProtocolAM handle it
                            if dres[IP].src != req.host:
                                dreq_rt += 1
                            if (dres[IP].src != req.host
                                or (dres[IP].src == req.host
                                    and dres[MyProtocol].state == DWAIT)):
                                try:
                                    # while waiting, sniff for dres
                                    dres = sniff(
                                        lfilter=(lambda pkt: (
                                            IP in pkt
                                            and pkt[IP].src == req.host
                                            and MyProtocol in pkt
                                            and pkt[MyProtocol].req_id == req_id
                                            and pkt[MyProtocol].state == DRES)),
                                        filter='inbound', count=1,
                                        timeout=DREQ_TO)[0]
                                except:
                                    dres = None
                                    continue
                            if dres[MyProtocol].state == DCAN:
                                print('Recv data exchange cancellation from',
                                      req.host)
                                dres[MyProtocol].show()
                                continue
                            if not req.dres_at:
                                req.dres_at = time()
                                req.state = DRES
                                req.result = dres.data
                                print('Recv data exchange response from',
                                      req.host)
                                dres[MyProtocol].show()
                                print('Send data exchange acknowledgement to',
                                      req.host)
                                print(req)
                                send(IP(dst=req.host)
                                     / MyProtocol(state=DACK, req_id=req_id),
                                     verbose=0)
                            return req.result
                        elif not req.dres_at:
                            print('No data')
                    hres = None
                    if dreq_rt == 0:
                        req._late = True
                elif not req.dres_at:
                    print('No resources')
            hres = None
        elif not req.dres_at:
            print('No hosts')

    if not req.dres_at:
        req.state = FAIL
    print(req)
    # if late dres
    if req.dres_at:
        return req.result
