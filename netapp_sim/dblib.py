'''
    This module provides methods for database operations.
    
    Methods:
    --------
    save(obj): Insert obj as a row in the table suitable for its class. 
    
    fetch(cls): Fetch row(s) from the table suitable for class cls.
'''

from os import getenv
from sqlite3 import connect

from model import Model, CoS
import config

# database configuration settings
DB_PATH = getenv('DB_PATH', '')
DB_DEFS_PATH = getenv('DB_DEFS_PATH', '')

# table names and definitions
COS = 'cos'
APPLICATION = 'application'
try:
    DEFINITIONS = open(DB_DEFS_PATH, 'r').read()
except:
    DEFINITIONS = ''
    #  TODO manage exception


# ====================
#     MAIN METHODS
# ====================


def save(obj: Model):
    '''
        Insert obj as a row in the table suitable for its class.

        Returns True if inserted, False if not.
    '''
    table, cols, vals = _get_table(obj.__class__)
    if table:
        try:
            Connection().execute('insert into {}{} values {}'.format(
                table, cols, vals), _adapt(obj)).connection.commit()
            return True
        except:
            return False
            # TODO manage exception
    return False


def fetch(cls, **kwargs):
    '''
        Fetch row(s) from the table suitable for class cls.

        Filters can be applied through kwargs. Example:

            >>> fetch(CoS, id=('=', 1))

        Returns: list of rows if selected, None if not.
    '''
    table, _, _ = _get_table(cls)
    where = ''
    for key in kwargs:
        cond, val = kwargs[key]
        where += key + cond + str(val) + ' and '
    if where:
        where = ' where ' + where[:-4]
    if table:
        try:
            return _convert(Connection().execute('select * from {}'.format(
                table) + where).fetchall(), cls)
        except:
            return None
            # TODO manage exception
    return None


# ============
#     UTIL
# ============


# singleton database connection

class Connection:
    def __new__(self):
        if not hasattr(self, '_connection'):
            self._connection = connect(DB_PATH)
            # ensure tables exist
            self._connection.executescript(DEFINITIONS).connection.commit()
        return self._connection


# encode object as table row

def _adapt(obj: Model):
    if obj.__class__.__name__ is CoS.__name__:
        return (obj.name,
                obj.get_max_response_time(),
                obj.get_min_concurrent_users(),
                obj.get_min_requests_per_second(),
                obj.get_min_bandwidth(),
                obj.get_max_delay(),
                obj.get_max_jitter(),
                obj.get_max_loss_rate(),
                obj.get_min_cpu(),
                obj.get_min_ram(),
                obj.get_min_disk(),)


# decode table rows as objects

def _convert(itr: list, cls):
    ret = []
    if cls.__name__ is CoS.__name__:
        for item in itr:
            cos = CoS(item[0], item[1])
            if item[2] != None:
                cos.set_max_response_time(item[2])
            if item[3] != None:
                cos.set_min_concurrent_users(item[3])
            if item[4] != None:
                cos.set_min_requests_per_second(item[4])
            if item[5] != None:
                cos.set_min_bandwidth(item[5])
            if item[6] != None:
                cos.set_max_delay(item[6])
            if item[7] != None:
                cos.set_max_jitter(item[7])
            if item[8] != None:
                cos.set_max_loss_rate(item[8])
            if item[9] != None:
                cos.set_min_cpu(item[9])
            if item[10] != None:
                cos.set_min_ram(item[10])
            if item[11] != None:
                cos.set_min_disk(item[11])
            ret.append(cos)
    return ret


# get table name with columns and values from class

def _get_table(cls):
    if cls.__name__ is CoS.__name__:
        return COS, '''(name, max_response_time, min_concurrent_users,
            min_requests_per_second, min_bandwidth, max_delay,
            max_jitter, max_loss_rate, min_cpu, min_ram, min_disk)
            ''', '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    return '', '', ''
