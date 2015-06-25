import os
import sys
import threading
import socket
import time
from collections import deque

from sensu.snmp.log import log
from sensu.snmp.log import events_log

class TrapEventDispatcherThread(threading.Thread):

    def __init__(self, config):
        # Initialize threading.Thread
        threading.Thread.__init__(self, name=self.__class__.__name__)
        # Initialize TrapEventDispatcher
        self._config = config
        self._trap_event_dispatcher = TrapEventDispatcher(config)
        self._run = False
        self._events = deque()

    def dispatch(self, event):
        # Log Event
        events_log.info(event.to_json())
        # Enqueue TrapEvent
        self._events.append(event)
        log.debug("TrapEventDispatcherThread: Enqueued Event: %r" % (event))
        return True

    def stop(self):
        self._run = False
        self._trap_event_dispatcher._close()

    def run(self):
        log.debug("%s: Started" % (self.name))
        self._run = True
        backoff = 0
        while self._run:
            if backoff <= 0:
                try:
                    # pop event off queue
                    event = self._events.popleft()

                    # attempt to dispatch event
                    if not self._trap_event_dispatcher.dispatch(event):
                        # dispatch failed. put the event back on the queue
                        self._events.appendleft(event)

                        # back off
                        backoff = int(self._config['dispatcher']['backoff'])

                        log.debug("TrapDispatcherThread: back off for %d seconds" % (backoff))

                except IndexError:
                    # Nothing in queue
                    pass

            else:
                backoff = backoff - 1

            time.sleep(1)

        log.debug("%s: Exiting" % (self.name))

class TrapEventDispatcher(object):
    def __init__(self, config):
        self._config = config
        self._remote_host = self._config['dispatcher']['host']
        self._remote_port = int(self._config['dispatcher']['port'])
        self._socket_timeout = int(self._config['dispatcher']['timeout'])
        self._socket = None
        log.debug("TrapEventDispatcher: Initialized")

    def _connect(self):
        log.debug("TrapEventDispatcher: Connecting to %s:%d" % (self._remote_host, self._remote_port))
        # create socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self._socket is None:
            # log Error
            log.error("TrapEventDispatcher: Unable to create socket")
            # close Socket
            self._close()
            return

        # set socket timeout
        self._socket.settimeout(self._socket_timeout)

        # connect to graphite server
        try:
            self._socket.connect((self._remote_host, self._remote_port))
            # Log
            log.debug("TrapEventDispatcher: Established connection to %s:%d" % (self._remote_host, self._remote_port))
        except:
            # Log Error
            log.exception("TrapEventDispatcher: Failed to connect to %s:%d" % (self._remote_host, self._remote_port))
            # Close Socket
            self._close()
            return

    def _close(self):
        if self._socket is not None:
            log.debug("TrapEventDispatcher: Closing connection to %s:%d" % (self._remote_host, self._remote_port))
            self._socket.close()
        self._socket = None

    def dispatch(self, event):
        log.debug("TrapEventDispatcher: Dispatching TrapEvent: %r" % (event))
        try:
            self._connect()

            # Send event
            self._socket.sendall(event.to_json())

            if self._config['dispatcher']['check_response']:
                # Receive event confirmation
                self._socket.setblocking(0)
                timer = int(time.time())
                data = ""
                while (int(time.time()) - timer) < self._socket_timeout:
                    try:
                        data = self._socket.recv(512)
                        break
                    except socket.error, e:
                        pass
                self._socket.setblocking(1)
                if len(data) <= 0 or data.strip() != "ok":
                    log.error("TrapEventDispatcher: Error dispatching event. Response was: %s" % (data))
                    return False

            log.info("TrapEventDispatcher: Dispatched TrapEvent: %r" % (event))

            return True
        except:
            log.exception("TrapEventDispatcher: Error dispatching event")
        finally:
            self._close()
        return False
