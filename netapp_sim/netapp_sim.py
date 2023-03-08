'''
    This is the main module, and plays the two roles of “service consumer” and 
    “service provider”. It can be used programmatically or launched through 
    CLI.
'''


from threading import Thread

from protocol import send_request


def _send_request(cos_id: int, data: bytes):
    print(send_request(cos_id=cos_id, data=data))


# for testing
if __name__ == '__main__':
    print('\nClick ENTER to send a request\nOr wait to receive requests')
    while True:
        input()
        Thread(target=_send_request, args=(2, b'data + program')).start()
