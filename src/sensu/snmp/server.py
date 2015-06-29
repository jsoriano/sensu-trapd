import time
import simplejson as json

from sensu.snmp.log import log as LOG
from sensu.snmp.mib import MibResolver
from sensu.snmp.handler import TrapHandler
from sensu.snmp.receiver import TrapReceiverThread
from sensu.snmp.dispatcher import TrapEventDispatcherThread
from sensu.snmp.util import *

class SensuTrapServer(object):

    def __init__(self, config):
        self._config = config
        self._run = False

        # Configure MIBs
        self._configure_mibs()

        # Initialize TrapReceiverThread
        self._trap_receiver_thread = TrapReceiverThread(self._config, self._mibs, self._handle_trap)

        # Initialize TrapEventDispatcher
        self._trap_event_dispatcher_thread = TrapEventDispatcherThread(self._config)

        # Configure Trap Handlers
        self._trap_handlers = self._parse_trap_handlers(self._config['daemon']['trap_file'])

        LOG.debug("SensuTrapServer: Initialized")

    def _configure_mibs(self):
        try:
            self._mibs = MibResolver(self._config['mibs']['paths'], self._config['mibs']['mibs'])
        except Exception as e:
            LOG.debug(str(e))
            raise


    def _parse_trap_handlers(self, trap_file):
        # TODO: Support multiple trap files
        LOG.debug("SensuTrapServer: Parsing trap handler file: %s" % (trap_file))
        trap_handlers = dict()
        try:
            fh = open(trap_file, 'r')
            trap_file_data = json.load(fh)
            for trap_handler_id, trap_handler_config in trap_file_data.items():
                # Load TrapHandler
                trap_handler = self._load_trap_handler(trap_handler_id, trap_handler_config)
                trap_handlers[trap_handler_id] = trap_handler
                LOG.debug("SensuTrapServer: Parsed trap handler: %s" % (trap_handler_id))
        except Exception as e:
            LOG.debug(str(e))
        finally:
            fh.close()
        return trap_handlers

    def _load_trap_handler(self, trap_handler_id, trap_handler_config):
        # Parse trap type
        trap_type_module, trap_type_symbol = tuple(trap_handler_config['trap']['type'])
        # TODO: handle OIDs as trap types
        trap_type_oid = self._mibs.lookup(trap_type_module, trap_type_symbol)

        #LOG.debug("%s type=%s::%s (%r)" % (trap_handler_id, trap_type_module, trap_type_symbol, trap_type_oid))

        # Parse trap arguments
        trap_args = dict()
        if 'args' in trap_handler_config['trap']:
            for trap_arg, trap_arg_type in trap_handler_config['trap']['args'].items():
                trap_arg_type_module, trap_arg_type_symbol = tuple(trap_arg_type)
                # TODO: handle OIDs as trap arg type
                trap_arg_type_oid = self._mibs.lookup(trap_arg_type_module, trap_arg_type_symbol)
                trap_args[trap_arg_type_oid] = trap_arg

        # Initialize TrapHandler
        trap_handler = TrapHandler(trap_type_oid,
                                   trap_args,
                                   trap_handler_config['event'])
        return trap_handler

    def _dispatch_trap_event(self, trap_event):
        self._trap_event_dispatcher_thread.dispatch(trap_event)

    def _handle_trap(self, trap):
        LOG.info("SensuTrapServer: Received Trap: %s" % (trap))

        # Find TrapHandler for this Trap 
        trap_handler = None
        for trap_handler_id, th in self._trap_handlers.items():
            if th.handles(trap):
                LOG.info("SensuTrapServer: %s handling trap %r" % (trap_handler_id, trap))
                # Transform Trap
                trap_event = th.transform(trap)
                # Dispatch TrapEvent
                self._dispatch_trap_event(trap_event)
                return
        LOG.warning("No trap handler found for %r" % (trap))

    def stop(self):
        if not self._run:
            return
        self._run = False

        # Stop TrapReceiverThread
        self._trap_receiver_thread.stop()

        # Stop TrapEventDispatcherThread
        self._trap_event_dispatcher_thread.stop()

    def run(self):
        LOG.debug("SensuTrapServer: Started")
        self._run = True

        # Start TrapReceiverThread
        self._trap_receiver_thread.start()

        # Start TrapEventDispatcherThread
        self._trap_event_dispatcher_thread.start()

        while self._run:
            time.sleep(1)

        # Wait for our threads to stop
        self._trap_receiver_thread.join()
        self._trap_event_dispatcher_thread.join()
        LOG.debug("SensuTrapServer: Exiting")
