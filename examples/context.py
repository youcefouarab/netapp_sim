from sys import path
from os.path import dirname, abspath, join


path.insert(0, abspath(join(dirname(__file__), '..')))


from netapp_sim.protocol import send_request
