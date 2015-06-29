import socket

from sensu.snmp.log import log
from sensu.snmp.event import TrapEvent

def get_hostname_from_address(addr):
    try:
        hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(addr)
        # parse hostname
        hostname_parts = hostname.split('.')
        if len(hostname_parts) <= 2:
            return hostname, ''
        else:
            return hostname_parts[0], '.'.join(hostname_parts[1:])
    except socket.herror:
        return addr, addr
