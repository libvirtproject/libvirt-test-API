#!/usr/bin/python
import time
import threading

import libvirt
from libvirt import libvirtError
from src import sharedmod


required_params = ('action',)
optional_params = {'networkname': 'testnetcb',
                   'bridgename': 'testnetcbbr',
                   'bridgeip': '192.168.123.1',
                   'bridgenetmask': '255.255.255.0',
                   'netstart': '192.168.123.2',
                   'netend': '192.168.123.254',
                   'netmode': 'nat',
                   'netip6addr': '2001:db8:ca2:99::1',
                   'netip6prefix': '64',
                   'netip6start': '2001:db8:ca2:99::11',
                   'netip6end': '2001:db8:ca2:99::ff',
                   'xml': 'xmls/network.xml',
                   }


def net_define(conn, net_name, xmlstr):
    """ define a network
    """
    conn.networkDefineXML(xmlstr)


def net_undefine(conn, net_name, xmlstr):
    """ undefine a network
    """
    netobj = conn.networkLookupByName(net_name)
    netobj.undefine()


def net_start(conn, net_name, xmlstr):
    """ start a network
    """
    try:
        netobj = conn.networkLookupByName(net_name)
        netobj.create()
    except libvirtError:
        conn.networkCreateXML(xmlstr)


def net_destroy(conn, net_name, xmlstr):
    """ destroy a network
    """
    netobj = conn.networkLookupByName(net_name)
    netobj.destroy()


event_func_map = {"define": net_define,
                  "undefine": net_undefine,
                  "start": net_start,
                  "destroy": net_destroy,
                  }


def net_str_to_func(action):
    """ convert string to net function
    """
    return event_func_map[action]


class event_loop(object):

    def __init__(self):
        self._thread = None
        self.running = False

    def __del__(self):
        self._thread = None
        self.running = False

    def _event_loop_native(self):
        while self.running:
            libvirt.virEventRunDefaultImpl()

    def start(self):
        """ start event loop by spawning a new thread
        """
        libvirt.virEventRegisterDefaultImpl()
        self.running = True
        self._thread = threading.Thread(target=self._event_loop_native,
                                        name="libvirtEventLoop")
        self._thread.setDaemon(True)
        self._thread.start()

    def wait(self, timeout=None):
        self._thread.join(timeout)


class event_lifecycle_callback(object):

    def __init__(self, net_name, action):
        self._net_name = net_name
        self._action = action
        self.callback_id = None
        self.finished = False

    def __del__(self):
        self._net_name = None
        self._action = None
        self.callback_id = None
        self.finished = False

    def _net_event_str(self, event):
        netEventStrings = ("define",
                           "undefine",
                           "start",
                           "destroy",
                           )
        return netEventStrings[event]

    def callback_func(self, conn, net, event, detail, opaque):
        """ the callback function implement
        """
        if net.name() == self._net_name and \
                self._net_event_str(event) == self._action:
            self.finished = True


class event_trigger(object):

    def __init__(self, conn, args):
        self._conn = conn
        self._net = args[0]
        self._xmlstr = args[1]
        self._action = args[2]
        self._thread = None
        self.fin_event = threading.Event()

    def __del__(self):
        self.fin_event.clear()
        self._thread = None
        self._conn = None
        self._net = None
        self._xmlstr = None
        self._action = None

    def _thread_func(self, conn, action, net_name, xmlstr):
        net_str_to_func(action)(conn, net_name, xmlstr)
        self.fin_event.set()

    def start(self):
        """ start to trigger an event by spawning a new thread
        """
        self._thread = threading.Thread(target=self._thread_func,
                                        args=(self._conn, self._action,
                                              self._net, self._xmlstr))
        self._thread.setDaemon(True)
        self._thread.start()


def check_event_callback(callback, logger):
    """ check event callback result, returns True if success,
        or False if timeout. threading.Event.wait() always return None in
        python2.6, for compatibilities we implement timeout mechanism.
    """
    counter = 60
    while not callback.finished:
        time.sleep(1)
        counter -= 1
        if counter < 0:
            logger.error("event callback checking time out")
            return False

    return True


def event_callback(params):
    """ test event callback
        it expects virtual network started while testing destroy callback,
        defined while testing undefined callback, verse vice.
    """
    logger = params['logger']
    xmlstr = params['xml']
    action = params['action']
    net_name = params.get('networkname', 'testnetcb')
    event_id = libvirt.VIR_NETWORK_EVENT_ID_LIFECYCLE
    started = False
    defined = False
    ret = 1

    conn = sharedmod.libvirtobj['conn']
    logger.info("begin to %s network: %s" % (action, net_name))

    if action not in event_func_map:
        logger.error("wrong action specified: %s" % action)
        return 1

    # detect if the target net is active
    for n in conn.listAllNetworks(2):
        if n.name() == net_name:
            started = True

    # detect if the target net is defined
    for n in conn.listAllNetworks(4):
        if n.name() == net_name:
            defined = True

    if action == 'destroy':
        if not started:
            logger.error("the virtual network %s is not active" % net_name)
            return 1
    elif action == 'undefine':
        if not defined:
            logger.error("the virtual network %s is not defined" % net_name)
            return 1
    elif action == 'define':
        if defined:
            logger.error("the virtual network %s is defined" % net_name)
            return 1
    else:
        if started:
            logger.error("the virtual network %s is started" % net_name)
            return 1

    # start event loop
    el = event_loop()
    el.start()

    # re-fetch the connection
    conn = libvirt.open()

    ec = event_lifecycle_callback(net_name, action)
    # register event callback
    try:
        ec.callback_id = conn.networkEventRegisterAny(None, event_id,
                                                      ec.callback_func, None)
    except libvirtError as e:
        logger.error("API error message: %s, error code is %s" %
                     (e.get_error_message(), e.get_error_code()))
        logger.error("fail to destroy domain")
        # unregister callback
        conn.networkEventDeregisterAny(ec.callback_id)
        el.running = False
        el.wait(60)
        return 1

    # do action for network in child thread, always before main thread
    args = [net_name, xmlstr, action]
    et = event_trigger(conn, args)
    et.start()

    # wait for event_tigger finished
    et.fin_event.wait(60)

    if check_event_callback(ec, logger):
        logger.info("event callback on %s's %s: pass" % (net_name, action))
        ret = 0
    else:
        logger.error("event callback on %s's %s: fail" % (net_name, action))

    conn.networkEventDeregisterAny(ec.callback_id)
    el.running = False
    el.wait(60)
    return ret
