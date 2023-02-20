from threading import Thread

from scapy.all import IP, Ether, bind_layers, sendp, srp1

from layers import HostRequest, HostResponse
from handlers import HostResponseAM

bind_layers(IP, HostResponse)

#Thread(target=HostResponseAM()).start()

ans = srp1((Ether(dst='ff:ff:ff:ff:ff:ff')
            / IP(dst='255.255.255.255')
            / HostRequest(cos=2)), timeout=3, verbose=0)

print(ans)