from scapy.all import Packet, AnsweringMachine, sendp, Ether, IP

from layers import HostRequest, HostResponse


class HostRequestAM(AnsweringMachine):
    function_name = 'hram'
    send_function = staticmethod(sendp)

    def is_request(self, req: Packet):
        return HostRequest in req

    def make_reply(self, req: Packet):
        print(req[Ether].src, req[IP].src)
        return HostResponse(ok=1)


class HostResponseAM(AnsweringMachine):
    function_name = 'hram_'
    send_function = staticmethod(sendp)

    def is_request(self, req: Packet):
        return HostResponse in req

    def make_reply(self, req: Packet):
        print(req[IP].src, 'has replied')
        #return