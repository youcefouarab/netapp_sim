'''
    Main module of NetApp Sim. It plays the dual role of “service consumer” 
    and “service provider”. It can be launched through CLI.
'''


from threading import Thread
from logging import getLogger
from flask import cli

from protocol import send_request, cos_names
from simulator import get_resources
from gui import app
from consts import MY_IP


# disable flask console messages
getLogger('werkzeug').disabled = True
cli.show_server_banner = lambda *args: None


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
    # starting web server (gui)
    app.logger.disabled = True
    Thread(target=app.run, args=('0.0.0.0',)).start()
    print('\nServer starting at http://' + MY_IP + ':8050')
    # starting cli
    print('\nChoose a Class of Service and click ENTER to send a request\n'
          'Or wait to receive requests')
    _list_cos()
    print()
    get_resources()
    print()
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
