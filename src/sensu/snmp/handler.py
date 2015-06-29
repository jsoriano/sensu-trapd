from sensu.snmp.event import TrapEvent
from sensu.snmp.log import log


class TrapHandler(object):

    def __init__(self, trap_type, trap_args, event):
        self.trap_type = trap_type
        self.trap_args = trap_args
        self.event = event

    def handles(self, trap):
        if trap.oid == self.trap_type:
            for trap_arg in trap.arguments:
                if str(trap_arg) not in ['1.3.6.1.2.1.1.3.0'] and trap_arg not in self.trap_args.keys():
                    return False
            return True
        return False

    def _build_substitutions(self, trap):
        substitutions = dict()

        # add default substitutions
        substitutions['oid'] = str(trap.oid)

        # build substitution list from trap properties
        for k, v in trap.properties.items():
            substitutions[k] = str(v)

        # build substitution list from trap arguments
        for trap_arg_type_oid, token in self.trap_args.items():
            if trap_arg_type_oid in trap.arguments:
                substitutions[token] = str(trap.arguments[trap_arg_type_oid])

        return substitutions

    def transform(self, trap):
        substitutions = self._build_substitutions(trap)
        return TrapEvent(self.event, substitutions)
