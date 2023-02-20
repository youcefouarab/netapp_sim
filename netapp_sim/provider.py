from threading import Thread

from scapy.all import bind_layers, IP

from layers import HostRequest
from handlers import HostRequestAM

bind_layers(IP, HostRequest)

Thread(target=HostRequestAM()).start()
