from utils import get_ip


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

# misc. consts
REQ_ID_LEN = 10
BROADCAST_MAC = 'ff:ff:ff:ff:ff:ff'
BROADCAST_IP = '255.255.255.255'
DEFAULT_IP = '0.0.0.0'
MY_IP = get_ip()
