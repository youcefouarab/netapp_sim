from threading import Thread
from time import sleep

from scapy.all import bind_layers, IP, Ether

from protocol import MyProtocol, MyProtocolAM
from monitor import Monitor

bind_layers(IP, MyProtocol)
bind_layers(Ether, MyProtocol)

Monitor().start()

Thread(target=MyProtocolAM()).start()
