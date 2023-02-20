from scapy.all import Packet, ShortField


class HostRequest(Packet):
    name = 'HostRequest'
    fields_desc = [
        ShortField('cos', 0),]


class HostResponse(Packet):
    name = 'HostResponse'
    fields_desc = [
        ShortField('ok', 1),]
