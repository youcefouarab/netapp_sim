'''
    This module contains the Monitor class, which is responsible for monitoring 
    the state of available resources of the node it's running on (number of 
    CPUs, free memory, and free disk, as well as free bandwidth and delay on 
    each network interface), and saving the most recent measures in a 
    dictionary.
'''


from threading import Thread
from time import monotonic, sleep
from psutil import net_if_addrs, net_if_stats, net_io_counters
from psutil import cpu_count, virtual_memory, disk_usage
from socket import socket, AF_INET, SOCK_STREAM

from meta import SingletonMeta


class Monitor(metaclass=SingletonMeta):
    '''
        This class is responsible for monitoring the state of available 
        resources of the node it's running on (number of CPUs, free memory, 
        and free disk, as well as free bandwidth and delay on each network 
        interface), and saving the most recent measures in a dictionary.

        Attributes:
        -----------
        monitor_period: time to wait before each measure. Default is 1s.

        ping_host_ip: destination IP address to which delay is calculated. 
        Default is 8.8.8.8.

        ping_host_port: destination port number to which delay is calculated. 
        Default is 443.

        ping_timeout: time to wait before declaring delay as infinite. Default 
        is 4s.

        measures: dict saving the most recent measures in the following 
        structure: 

        {
        \t  'cpu_count': <int>,
        \t  'memory_total: <float>, # in MB
        \t  'memory_free': <float>, # in MB
        \t  'disk_total': <float>, # in GB
        \t  'disk_free': <float>, # in GB
        \t  'iface_name': {
        \t\t    'bandwidth_up': <float>, # in Mbit/s
        \t\t    'bandwidth_down': <float>, # in Mbit/s
        \t\t    'delay': <float>, # in s
        \t  },
        }.

        Methods:
        --------
        start(): Start monitoring thread.

        stop(): Stop monitoring thread.
    '''

    def __init__(self, monitor_period: float = 1,
                 ping_host_ip: str = '8.8.8.8', ping_host_port: int = 443,
                 ping_timeout: float = 4):
        self.measures = {}
        self.monitor_period = monitor_period
        self.ping_host_ip = ping_host_ip
        self.ping_host_port = ping_host_port
        self.ping_timeout = ping_timeout

        self._ips = {}
        for _iface, _addrs in net_if_addrs().items():
            for _addr in _addrs:
                if _addr.family == AF_INET:
                    self._ips[_iface] = _addr.address

        self._run = False

    def start(self):
        '''
            Start monitoring thread.
        '''
        if not self._run:
            self._run = True
            Thread(target=self._start).start()

    def stop(self):
        '''
            Stop monitoring thread.
        '''
        self._run = False

    def set_monitor_period(self, period: float = 1):
        self.monitor_period = period

    def set_ping_host(self, ip: str = '8.8.8.8', port: int = 443):
        self.ping_host_ip = ip
        self.ping_host_port = port

    def set_ping_timeout(self, timeout: float = 4):
        self.ping_timeout = timeout

    def _start(self):
        # get network I/O stats on each interface
        # by setting pernic to True
        io = net_io_counters(pernic=True)
        while self._run:
            # node specs
            self.measures['cpu_count'] = cpu_count()
            mem = virtual_memory()
            self.measures['memory_total'] = mem.total / 1e+6  # in MB
            self.measures['memory_free'] = mem.available / 1e+6  # in MB
            disk = disk_usage('/')
            self.measures['disk_total'] = disk.total / 1e+9  # in GB
            self.measures['disk_free'] = disk.free / 1e+9  # in GB
            # link specs
            for iface in io:
                if iface != 'lo':
                    # delay
                    # use thread so it's asynchronous (in case of timeout)
                    Thread(target=self._get_delay, args=(iface,)).start()
            # get network I/O stats on each interface again
            sleep(self.monitor_period)
            io_2 = net_io_counters(pernic=True)
            # get network interfaces stats
            stats = net_if_stats()
            for iface in io:
                if iface != 'lo' and iface in io_2 and iface in stats:
                    # bandwidth
                    # speed = (new bytes - old bytes) / period
                    # current speed = max(up speed, down speed)
                    up_bytes = io_2[iface].bytes_sent - io[iface].bytes_sent
                    up_speed = up_bytes * 8 / self.monitor_period  # in bits/s
                    down_bytes = io_2[iface].bytes_recv - io[iface].bytes_recv
                    down_speed = down_bytes * 8 / self.monitor_period  # in bits/s
                    #  get max speed (capacity)
                    max_speed = stats[iface].speed * 1000000  # in bits/s
                    # calculate free bandwidth
                    bandwidth_up = (max_speed - up_speed) / 1e+6  # in Mbits/s
                    bandwidth_down = (max_speed - down_speed) / \
                        1e+6  # in Mbits/s
                    #  save bandwidth measurement
                    self.measures.setdefault(iface, {})
                    self.measures[iface]['bandwidth_up'] = bandwidth_up
                    self.measures[iface]['bandwidth_down'] = bandwidth_down
                # if interface is removed during monitor period
                # remove from measures dict
                elif iface not in io_2 or iface not in stats:
                    self.measures.pop(iface, None)
            # update network I/O stats for next iteration
            io = io_2

    def _get_delay(self, via_iface: str):
        '''
            Connect to host:port via interface specified by name and calculate 
            total delay before response.

            If timeout set, connection will be closed after timeout seconds 
            and delay will be considered infinite.
        '''
        with socket(AF_INET, SOCK_STREAM) as s:
            # bind socket to interface if specified
            if via_iface:
                ip = self._get_ip(via_iface)
                if ip:
                    s.bind((ip, 0))
            # set timeout in case of errors
            s.settimeout(self.ping_timeout)
            # start timer
            t_start = monotonic()
            # try to connect to host
            try:
                s.connect((self.ping_host_ip, self.ping_host_port))
                # stop timer and calculate delay
                delay = (monotonic() - t_start)
            except:
                # if exception, connection wasn't acheived correctly
                delay = float('inf')
            finally:
                # close connection
                s.close()
                self.measures.setdefault(via_iface, {})
                self.measures[via_iface]['delay'] = delay

    def _get_ip(self, iface: str):
        '''
            Returns IP address of interface specified by name.
        '''
        if iface in self._ips:
            return self._ips[iface]
        else:
            addrs = net_if_addrs()
            if iface in addrs:
                for addr in addrs[iface]:
                    if addr.family == AF_INET:
                        self._ips[iface] = addr.address
                        return addr.address
            return None


# for testing
if __name__ == '__main__':
    monitor = Monitor()
    monitor.start()
    while True:
        print(monitor.measures)
        sleep(monitor.monitor_period)
