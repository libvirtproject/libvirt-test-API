#!/usr/bin/env python

import libvirt

from libvirt import libvirtError

required_params = ('guestname', 'iothread_id')
optional_params = {'max_ns': None,
                   'grow': None,
                   'shrink': None}


def set_iothread(params):
    """
       test API for setIOThreadParams
    """

    logger = params['logger']
    guest = params['guestname']
    max_ns = params.get('max_ns', None)
    grow = params.get('grow', None)
    shrink = params.get('shrink', None)
    iothread_id = int(params['iothread_id'])

    if not utils.version_compare("libvirt-python", 5, 0, 0, logger):
        logger.info("Current libvirt-python don't support setIOThreadParams().")
        return 0

    iothread_params = {}
    if max_ns is not None:
        iothread_params['poll_max_ns'] = int(max_ns)
        logger.info("set poll_max_ns: %s" % max_ns)
    if grow is not None:
        iothread_params['poll_grow'] = int(grow)
        logger.info("set poll_grow: %s" % grow)
    if shrink is not None:
        iothread_params['poll_shrink'] = int(shrink)
        logger.info("set poll_shrink: %s" % shrink)
    try:
        conn = libvirt.open()
        dom = conn.lookupByName(guest)
        if dom.isActive() == 1:
            dom.setIOThreadParams(iothread_id, iothread_params, 0)
            dom_stats = conn.domainListGetStats([dom], libvirt.VIR_DOMAIN_STATS_IOTHREAD, 0)
            logger.info("domain get stats: %s" % dom_stats)
        else:
            logger.error("domain is not running.")
            return 1

        # check iothread params
        if max_ns is not None:
            if dom_stats[0][1]['iothread.%s.poll-max-ns' % iothread_id] != int(max_ns):
                logger.error("check poll-max_ns failed.")
                return 1
        if grow is not None:
            if dom_stats[0][1]['iothread.%s.poll-grow' % iothread_id] != int(grow):
                logger.error("check poll-grow failed.")
                return 1
        if shrink is not None:
            if dom_stats[0][1]['iothread.%s.poll-shrink' % iothread_id] != int(shrink):
                logger.error("check poll-shrink failed.")
                return 1

        logger.info("PASS: set iothread params successful.")
    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1
    return 0
