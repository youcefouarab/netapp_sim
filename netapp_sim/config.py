from os import path, environ
from yaml import safe_load

CONF = path.dirname(path.dirname(path.abspath(__file__))) + '/conf.yml'

try:
    with open(CONF, 'r') as f:
        config = safe_load(f)
        for section in config:
            for param in config[section]:
                environ[param] = str(config[section][param])
except:
    print(' *** ERROR: Configuration failed')
    exit()
    # TODO manage exception
