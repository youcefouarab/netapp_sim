'''
    General purpose library for database operations, providing methods that 
    serve as a facade to hide the complexities of the database-specific library 
    used. Currently supports SQLite database library.
    
    Methods:
    --------
    insert(obj): Insert obj as a row in its corresponding database table. 

    update(obj): Update corresponding database table row from obj.
    
    select(cls, fields, as_obj): Select row(s) from the database table of cls.

    as_csv(cls): Convert the database table of cls to a CSV file.
'''


from os import getenv
from os.path import dirname, abspath
from queue import Queue
from threading import Thread, Event
from sqlite3 import connect
from csv import writer

from model import Model, CoS, Request, Attempt, Response
from consts import MY_IP
import config


# database config
ROOT_PATH = dirname(dirname(abspath(__file__)))

_db_path = getenv('DATABASE_PATH', None)
if _db_path == None:
    print(' *** WARNING in dblib: DATABASE:PATH parameter invalid or missing '
          'from conf.yml. Defaulting to in-memory database.')
    _db_path = ':memory:'
elif _db_path != ':memory:':
    # if SIMULATION:ACTIVE is True (like Mininet), create different DB files
    # for different hosts (add IP address to file name)
    if getenv('SIMULATION_ACTIVE', False) == 'True':
        names = _db_path.split('.')
        names.insert(-1, MY_IP)
        _db_path = '.'.join(names)
    _db_path = ROOT_PATH + '/' + _db_path
DB_PATH = _db_path

_db_defs_path = getenv('DATABASE_DEFS_PATH', None)
if _db_defs_path == None:
    print(' *** WARNING in dblib: DATABASE:DEFS_PATH parameter invalid or '
          'missing from conf.yml. Defaulting to empty database.')
    _db_defs_path = ''
DB_DEFS_PATH = ROOT_PATH + '/' + _db_defs_path

# table definitions
try:
    DEFINITIONS = open(DB_DEFS_PATH, 'r').read()
except:
    DEFINITIONS = ''

# table names
_tables = {
    CoS.__name__: 'cos',
    Request.__name__: 'requests',
    Attempt.__name__: 'attempts',
    Response.__name__: 'responses'
}

# queue managing db operations from multiple threads
_queue = Queue()
_rows = {}


# ====================
#     MAIN METHODS
# ====================


def insert(obj: Model):
    '''
        Insert obj as a row in its corresponding database table.

        Returns True if inserted, False if not.
    '''

    try:
        cols = _get_columns(obj.__class__)
        _len = len(cols)
        vals = '('
        for i in range(_len):
            vals += '?'
            if i < _len - 1:
                vals += ','
        vals += ')'

        event = Event()

        global _queue
        _queue.put((
            'insert into {} {} values {}'.format(
                _tables[obj.__class__.__name__], str(cols), vals),
            _adapt(obj),
            event
        ))

        event.wait()
        return True

    except Exception as e:
        print(' *** ERROR in dblib.insert', e.__class__.__name__, e)
        return False


def update(obj: Model, _id: tuple = ('id',)):
    '''
        Update corresponding database table row from obj.

        Returns True if updated, False if not.
    '''

    try:
        _id_dict = {_id_field: ('=', getattr(obj, _id_field))
                    for _id_field in _id}
        where, vals = _get_where_str(**_id_dict)
        cols = _get_columns(obj.__class__)
        sets = ''
        for col in cols:
            sets += col + '=?,'

        event = Event()

        global _queue
        _queue.put((
            'update {} set {} {}'.format(
                _tables[obj.__class__.__name__], sets[:-1], where),
            _adapt(obj) + vals,
            event
        ))

        event.wait()
        return True

    except Exception as e:
        print(' *** ERROR in dblib.update', e.__class__.__name__, e)
        return False


def select(cls, fields: tuple = ('*',), groups: tuple = None,
           as_obj: bool = True, **kwargs):
    '''
        Select row(s) from the database table of cls.

        Filters can be applied through args and kwargs. Example:

            >>> select(CoS, fields=('id', 'name'), id=('=', 1), as_obj=False)

        as_obj should only be set to True if fields is (*).

        Returns list of rows if selected, None if not.
    '''

    try:
        where, vals = _get_where_str(**kwargs)
        group_by = _get_groups_str(groups)

        event = Event()

        global _queue
        _queue.put((
            'select {} from {} {}'.format(
                _get_fields_str(fields), _tables[cls.__name__],
                where + group_by),
            vals,
            event
        ))

        event.wait()

        global _rows
        if as_obj:
            return _convert(_rows[event], cls)
        return _rows[event]

    except Exception as e:
        print(' *** ERROR in dblib.select', e.__class__.__name__, e)
        return None


def select_page(cls, page: int, page_size: int, fields: tuple = ('*',),
                orders: tuple = None, as_obj: bool = True, **kwargs):
    '''
        ...
    '''

    try:
        where, vals = _get_where_str(**kwargs)
        order_by = _get_orders_str(orders)
        if not where:
            where += ' where '
        else:
            where += ' and '
        where += ' oid not in (select oid from {} {} limit {}) '.format(
            _tables[cls.__name__], order_by, (page - 1) * page_size)

        event = Event()

        global _queue
        _queue.put((
            'select {} from {} {} limit {}'.format(
                _get_fields_str(fields), _tables[cls.__name__],
                where + order_by, page_size),
            vals,
            event
        ))

        event.wait()

        global _rows
        if as_obj:
            return _convert(_rows[event], cls)
        return _rows[event]

    except Exception as e:
        print(' *** ERROR in dblib.select_page', e.__class__.__name__, e)
        return None


def as_csv(cls, fields: tuple = ('*',), abs_path: str = '', _suffix: str = '',
           **kwargs):
    '''
        Convert the database table of cls to a CSV file.

        Filters can be applied through args and kwargs. Example:

            >>> as_csv(Request, fields=('id', 'host'), host=('=', '10.0.0.2'))

        Returns True if converted, False if not.
    '''

    rows = select(cls, fields, as_obj=False, **kwargs)
    if rows != None:
        try:
            if fields[0] == '*':
                fields = _get_columns(cls)
            with open(abs_path if abs_path else (
                    ROOT_PATH + '/data/' + _tables[cls.__name__] + _suffix + '.csv'),
                    'w', newline='') as file:
                csv_writer = writer(file)
                csv_writer.writerow(fields)
                csv_writer.writerows(rows)
            return True

        except Exception as e:
            print(' *** ERROR in dblib.as_csv', e.__class__.__name__, e)
            return False
    else:
        return False


# =============
#     UTILS
# =============


# singleton database connection
class Connection:
    def __new__(self):
        if not hasattr(self, '_connection'):
            self._connection = connect(DB_PATH)
            self._connection.executescript(DEFINITIONS).connection.commit()
            self._connection.row_factory = lambda _, row: list(row)
        return self._connection


def _execute():
    global _queue
    global _rows
    while True:
        try:
            sql, params, event = _queue.get()
            cursor = Connection().execute(sql, params)
            if sql[0:6] == 'select':
                _rows[event] = cursor.fetchall()
            event.set()
            if sql[0:6] != 'select' and _queue.empty():
                cursor.connection.commit()

        except Exception as e:
            print(' *** ERROR in dblib._execute', e.__class__.__name__, e)


Thread(target=_execute).start()


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
        return (obj.id, obj.cos.id, obj.data, obj.result, obj.host, obj.state,
                obj.hreq_at, obj.dres_at)

    if obj.__class__.__name__ is Attempt.__name__:
        return (obj.req_id, obj.attempt_no, obj.host, obj.state, obj.hreq_at,
                obj.hres_at, obj.rres_at, obj.dres_at)

    if obj.__class__.__name__ is Response.__name__:
        return (obj.req_id, obj.attempt_no, obj.host, obj.cpu, obj.ram,
                obj.disk, obj.timestamp)


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
            obj = Request(
                item[0], select(CoS, id=('=', item[1]))[0], item[2], item[3],
                item[4], item[5], item[6], item[7], {
                    att.attempt_no: att
                    for att in select(Attempt, req_id=('=', item[0]))
                })

        if cls.__name__ is Attempt.__name__:
            obj = Attempt(item[0], item[1], item[2], item[3], item[4], item[5],
                          item[6], item[7])

        if cls.__name__ is Response.__name__:
            obj = Response(item[0], item[1], item[2], item[3], item[4],
                           item[5], item[6])

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
        return ('id', 'cos_id', 'data', 'result', 'host', 'state', 'hreq_at',
                'dres_at')

    if cls.__name__ is Attempt.__name__:
        return ('req_id', 'attempt_no', 'host', 'state', 'hreq_at', 'hres_at',
                'rres_at', 'dres_at')

    if cls.__name__ is Response.__name__:
        return ('req_id', 'attempt_no', 'host', 'cpu', 'ram', 'disk',
                'timestamp')

    return ()


def _get_fields_str(fields: tuple):
    fields_str = '*'
    for field in fields:
        fields_str += field + ','
    if fields_str != '*':
        fields_str = fields_str[1:-1]
    return fields_str


def _get_where_str(**kwargs):
    where = ''
    vals = ()
    for key in kwargs:
        cond, val = kwargs[key]
        where += key + cond + '? and '
        vals += (str(val),)
    if where:
        where = ' where ' + where[:-4]
    return where, vals


def _get_groups_str(groups: tuple = None):
    groups_str = ''
    if groups:
        groups_str += ' group by '
        for group in groups:
            groups_str += group + ','
    return groups_str[:-1]


def _get_orders_str(orders: tuple = None):
    orders_str = ''
    if orders:
        orders_str += ' order by '
        for order in orders:
            orders_str += order + ','
    return orders_str[:-1]
