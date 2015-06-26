import os
import sys

from sensu.snmp.log import log

class Trap(object):

    def __init__(self, type_name, oid, arguments, **properties):
        self.type_name = type_name
        self.oid = oid
        self.arguments = arguments
        self.properties = properties

    def __repr__(self):
        return "<Trap %s, oid:'%r' >" % (self.type_name, self.oid)
