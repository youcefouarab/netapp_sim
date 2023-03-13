'''
    This module provides methods for database operations.
    
    Methods:
    --------
    save(obj): Insert obj as a row in the table suitable for its class. 

    update(obj): Update row from obj.
    
    fetch(cls): Fetch row(s) from the table suitable for class cls.

    as_csv(cls): Convert database table to CSV file.
'''


from os import getenv
from os.path import dirname, abspath
from sqlite3 import connect
from csv import writer

from model import Model, CoS, Request
import config


# database config
ROOT_PATH = dirname(dirname(abspath(__file__)))
_db_path = getenv('DB_PATH', '')
if _db_path != ':memory:':
    DB_PATH = ROOT_PATH + '/' + _db_path
else:
    DB_PATH = _db_path
DB_DEFS_PATH = ROOT_PATH + '/' + getenv('DB_DEFS_PATH', '')

# table names
_tables = {
    CoS.__name__: 'cos',
    Request.__name__: 'requests'
}

# table definitions
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

    try:
        cols = _get_columns(obj.__class__)
        vals = '('
        for _ in range(len(cols)):
            vals += '?,'
        vals = vals[:-1] + ')'
        Connection().execute('insert into {}{} values {}'.format(
            _tables[obj.__class__.__name__], str(cols), vals), 
            _adapt(obj)).connection.commit()
        return True
    except Exception as e:
        print(e)
        return False
        # TODO manage exception


def update(obj: Model, id: str = 'id'):
    '''
        Update row from obj.

        Returns True if updated, False if not.
    '''

    try:
        cols = _get_columns(obj.__class__)
        sets = ''
        for col in cols:
            sets += col + '=?,'
        Connection().execute('update {} set {} where {}={}'.format(
            _tables[obj.__class__.__name__], sets[:-1], id, getattr(obj, id)), 
            _adapt(obj)).connection.commit()
        return True
    except Exception as e:
        print(e)
        return False
        # TODO manage exception


def fetch(cls, **kwargs):
    '''
        Fetch row(s) from the table suitable for class cls.

        Filters can be applied through kwargs. Example:

            >>> fetch(CoS, id=('=', 1))

        Returns: list of rows if selected, None if not.
    '''

    where = ''
    vals = []
    for key in kwargs:
        cond, val = kwargs[key]
        where += key + cond + '? and '
        vals.append(str(val))
    if where:
        where = ' where ' + where[:-4]
    try:
        return _convert(Connection().execute('select * from {}'.format(
            _tables[cls.__name__]) + where, vals).fetchall(), cls)
    except Exception as e:
        print(e)
        return None
        # TODO manage exception


def as_csv(cls, **kwargs):
    '''
        Convert database table to CSV file.

        Filters can be applied through kwargs. Example:

            >>> as_csv(Request, host=('=', 10.0.0.2))

        Returns True if converted, False if not.
    '''
    
    where = ''
    for key in kwargs:
        cond, val = kwargs[key]
        where += key + cond + str(val) + ' and '
    if where:
        where = ' where ' + where[:-4]
    try:
        rows = Connection().execute('select * from {}'.format(
            _tables[cls.__name__]) + where).fetchall()
    except Exception as e:
        print(e)
        return False
        # TODO manage exception
    else:
        cols = _get_columns(cls)
        try:
            with open(ROOT_PATH + '/data/' + _tables[cls.__name__] + '.csv', 
                      'w', newline='') as file:
                csv_writer = writer(file)
                csv_writer.writerow(cols)
                csv_writer.writerows(rows)
            return True
        except Exception as e:
            print(e)
            return False
            # TODO manage exception


# ============
#     UTIL
# ============


# singleton database connection (for time optimization)
# with check_same_thread == False, thread sync must be ensured manually
class Connection:
    def __new__(self):
        if not hasattr(self, '_connection'):
            self._connection = connect(DB_PATH, check_same_thread=False)
            # ensure tables exist
            self._connection.executescript(DEFINITIONS).connection.commit()
        return self._connection


# encode object as table row
def _adapt(obj: Model):
    if obj.__class__.__name__ is CoS.__name__:
        return (obj.id, obj.name, obj.get_max_response_time(),
                obj.get_min_concurrent_users(),
                obj.get_min_requests_per_second(), obj.get_min_bandwidth(),
                obj.get_max_delay(), obj.get_max_jitter(), 
                obj.get_max_loss_rate(), obj.get_min_cpu(), obj.get_min_ram(),
                obj.get_min_disk(),)
    if obj.__class__.__name__ is Request.__name__:
        return (obj.id, obj.cos.id, obj.state, obj.host, obj.data, obj.result,
                obj.hreq_at, obj.hres_at, obj.rres_at, obj.dres_at)


# decode table rows as objects
def _convert(itr: list, cls):
    ret = []
    for item in itr:
        if cls.__name__ is CoS.__name__:
            obj = CoS(item[0], item[1])
            if item[2] != None:
                obj.set_max_response_time(item[2])
            if item[3] != None:
                obj.set_min_concurrent_users(item[3])
            if item[4] != None:
                obj.set_min_requests_per_second(item[4])
            if item[5] != None:
                obj.set_min_bandwidth(item[5])
            if item[6] != None:
                obj.set_max_delay(item[6])
            if item[7] != None:
                obj.set_max_jitter(item[7])
            if item[8] != None:
                obj.set_max_loss_rate(item[8])
            if item[9] != None:
                obj.set_min_cpu(item[9])
            if item[10] != None:
                obj.set_min_ram(item[10])
            if item[11] != None:
                obj.set_min_disk(item[11])

        if cls.__name__ is Request.__name__:
            obj = Request(item[0], fetch(CoS, id=('=', item[1])[0]), item[4])
            obj.state = item[2]
            obj.host = item[3]
            obj.result = item[5]
            obj.hreq_at = item[6]
            obj.hres_at = item[7]
            obj.rres_at = item[8]
            obj.dres_at = item[9]

        ret.append(obj)
    return ret


# get table columns as tuple
def _get_columns(cls):
    if cls.__name__ is CoS.__name__:
        return ('id', 'name', 'max_response_time', 'min_concurrent_users',
                'min_requests_per_second', 'min_bandwidth', 'max_delay',
                'max_jitter', 'max_loss_rate', 'min_cpu', 'min_ram', 
                'min_disk')
    if cls.__name__ is Request.__name__:
        return ('id', 'cos_id', 'state', 'host', 'data', 'result', 'hreq_at',
                'hres_at', 'rres_at', 'dres_at')
    return ()
