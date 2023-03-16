'''
    This is the main module, and it plays the two roles of “service consumer” 
    and “service provider”. It can be used through CLI.
'''


from threading import Thread

from protocol import send_request, cos_names


def _list_cos():
    print()
    for id, name in cos_names.items():
        print(' ', id, '-', name, end=' ')
        if id == 1:
            print('(default)', end='')
        print()
    print()


def _send_request(cos_id: int, data: bytes):
    print(send_request(cos_id=cos_id, data=data))
    _list_cos()


# for testing
if __name__ == '__main__':
    print('\nChoose a Class of Service and click ENTER to send a request\n'
          'Or wait to receive requests')
    _list_cos()
    while True:
        cos_id = input()
        if cos_id == '':
            cos_id = 1
        try:
            cos_id = int(cos_id)
        except:
            print('Invalid CoS ID')
            _list_cos()
        else:
            if cos_id not in cos_names:
                print('This CoS doesn\'t exist')
                _list_cos()
            else:
                Thread(target=_send_request,
                       args=(cos_id, b'data + program')).start()
