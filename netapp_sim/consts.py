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
