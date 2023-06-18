from threading import Thread
from time import sleep

from context import send_request


'''
CoS list (set requirement values in data/definitions.sql)

id  name              
1   best-effort       
2   cpu-bound         
3   streaming         
4   conversational    
5   interactive       
6   real-time         
7   mission-critical  
'''
COS_ID = 1

'''
Send a request every INTERVAL seconds
'''
INTERVAL = 0.1  #  in seconds

'''
THREADS running in parallel
'''
THREADS = 1

'''
Stop when LIMIT requests (per thread) are sent (-1 is infinite)
'''
LIMIT = 100

'''
If SEQUENTIAL, wait for previous response before sending next request
'''
SEQUENTIAL = False

'''
DATA bytes to send
'''
DATA = b'data + program'


def _send_request(index: int, cos_id: int, data: bytes):
    print('%d-' % index, send_request(cos_id=cos_id, data=data))


def _send_requests():
    _limit = LIMIT
    index = 0
    while _limit != 0:
        _limit -= 1
        index += 1
        if SEQUENTIAL:
            _send_request(index, COS_ID, DATA)
        else:
            Thread(target=_send_request, args=(
                index, COS_ID, DATA)).start()
        sleep(INTERVAL)


for thread in range(THREADS):
    Thread(target=_send_requests).start()
