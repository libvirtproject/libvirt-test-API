#!/usr/bin/env python
import difflib
from libvirt import libvirtError

from src import sharedmod

required_params = ('op',)
optional_params = {'xmldump': '/tmp/guest_xml_dump', 'negative': 'no'}


def change_begin_check(before, xmldump, logger):
    try:
        with open(xmldump, 'w') as xml_file:
            xml_file.write(before)
    except Exception as e:
        logger.error("Failed to dump interface xml: %s" % str(e))
        return 1
    logger.info("Transaction begin.")
    return 0


def change_commit_check(before, after, dump, logger):
    if before != after:
        logger.error("Commit caused unexpected change.")
        return 1
    if before == dump:
        logger.error("No interface changed after commit.")
        return 1
    diff = difflib.unified_diff(before.splitlines(True),
                                after.splitlines(True))
    logger.info("Interface changes: \n" + "".join(diff))
    return 0


def change_rollback_check(before, after, dump, logger):
    if dump != after:
        logger.error("Interfaces didn't rollback.")
        return 1
    diff = difflib.unified_diff(before.splitlines(True),
                                after.splitlines(True))
    logger.info("Discarded changes: \n" + "".join(diff))
    return 0


def get_interface_xml(conn):
    interfaces_xml = ""
    for interface in conn.listAllInterfaces():
        interfaces_xml = interfaces_xml + "\n" + interface.XMLDesc()
    return interfaces_xml


def change_transaction(params):
    """
    Test changeRollback/changeCommit/changeBegin
    Take paremeters:
        op: begin/commit/rollback
        xmldump: dump current interface status to a xml file as a checkpoint
        negative: nagetive test, api should be called in order:
            begin->(commit|rollback), or it's a negative test.
    """
    logger = params['logger']
    xmldump = params.get('xmldump', '/tmp/guest_xml_dump')
    negative = params.get('negative', 'no')
    op = params['op']

    conn = sharedmod.libvirtobj['conn']

    if op == 'commit':
        test = conn.changeCommit
    elif op == 'rollback':
        test = conn.changeRollback
    elif op == 'begin':
        test = conn.changeBegin
    else:
        logger.error("Invalid operation: %s" % op)
        return 1

    logger.info("Testing %s" % op)

    try:
        interfaces_before_xml = get_interface_xml(conn)
        logger.debug("interfaces before transaction %s", interfaces_before_xml)

        try:
            test()
        except libvirtError, e:
            logger.error("API error message: %s, error code is %s"
                         % (e.message, e.get_error_code()))
            if negative == 'yes':
                logger.error("Negative test pass.")
                return 0
            logger.error("Negative test failed.")
            return 1

        if negative == 'yes':
            logger.error("Negative test failed.")
            return 1

        interfaces_after_xml = get_interface_xml(conn)
        logger.debug("interfaces after transaction %s", interfaces_after_xml)

    except libvirtError, e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if op == 'begin':
        return change_begin_check(interfaces_before_xml, xmldump, logger)

    try:
        with open(xmldump, 'r') as xml_file:
            interface_dump_xml = xml_file.read()
    except Exception as e:
        logger.error("Failed to open checkpoint file: %s" % str(e))
        return 1

    logger.debug("dump xml: %s", interface_dump_xml)

    if interfaces_before_xml == interface_dump_xml:
        logger.error("No interface changed during transaction.")
        return 1

    if op == 'commit':
        return change_commit_check(interfaces_before_xml, interfaces_after_xml,
                                   interface_dump_xml, logger)
    if op == 'rollback':
        return change_rollback_check(interfaces_before_xml, interfaces_after_xml,
                                     interface_dump_xml, logger)

    return 0
