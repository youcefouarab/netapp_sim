from sys import path
from os.path import dirname


path.append(dirname(__file__))


from .gui import app
