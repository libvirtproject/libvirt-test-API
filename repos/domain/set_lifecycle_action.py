#!/usr/bin/python
"""
Changes the actions of lifecycle events for domain represented
as <on_$type>$action</on_$type> in the domain XML and test if
it is successful
"""

from libvirt import libvirtError
import libvirt
from utils import utils, process
import time
from src import sharedmod
from lxml import etree as ET
import functools
from utils.utils import version_compare

required_params = ('guestname',)
optional_params = {'on_type': 'poweroff',
                   'action': 'restart',
                   'flags': 'none',
                   }

LIFECYCLE_TYPE_DESC = {"poweroff": 0, "reboot": 1, "crash": 2}

TYPE_NAME = ("on_poweroff", "on_reboot", "on_crash")

LIFECYCLE_ACTION_DESC = {"destroy": 0, "restart": 1,
                         "rename-restart": 2, "preserve": 3,
                         "coredump-destroy": 4, "coredump-restart": 5}


def get_xml_text(domobj, flags):
    #get the xml element(on_poweroff,on_reboot,on_crash) text
    guestxml = domobj.XMLDesc(flags)
    tree = ET.XML(guestxml)
    lifecycle_list = ['', '', '']
    for i in range(len(TYPE_NAME)):
        for elem in tree.iter(tag=TYPE_NAME[i]):
            lifecycle_list[i] = elem.text
            break
    return lifecycle_list


def get_params(domobj, logger, params, params_value, guestname):
    #check params and get corresponding value
    lifecycle_list = get_xml_text(domobj, 0)

    for i in range(len(TYPE_NAME)):
        logger.debug("guest start with %s value is %s" % (TYPE_NAME[i], lifecycle_list[i]))

    on_type = params.get('on_type', 'poweroff')
    logger.info("lifecycle type is %s" % on_type)

    action = params.get('action', 'restart')
    logger.info("lifecycle action is %s" % action)

    flags = params.get('flags', 'none')

    cmd = "ps -ef | grep %s | grep qemu | head -n 1 | grep 'no-reboot'" % guestname
    ret = process.run(cmd, shell=True, ignore_status=True)
    logger.debug("out is %s" % ret.stdout)
    if not ret.exit_status:
        logger.info("notice:QEMU was started with -no-reboot option")
        return 2

    if lifecycle_list[LIFECYCLE_TYPE_DESC[on_type]] == action:
        logger.info("lifecycle action no change")
        return 2

    if (on_type != "crash") \
            and (action == "coredump-destroy" or action == "coredump-restart"):
        logger.info("lifecycle event type %s doesn't support %s action " % (on_type, action))
        return 2

    if on_type not in LIFECYCLE_TYPE_DESC:
        logger.error("lifecycle type value is invalid")
        return 1

    for key in LIFECYCLE_TYPE_DESC:
        if on_type == key:
            params_value[0] = LIFECYCLE_TYPE_DESC[key]
            break

    if action not in LIFECYCLE_ACTION_DESC:
        logger.error("lifecycle action value is invalid")
        return 1

    for key in LIFECYCLE_ACTION_DESC:
        if action == key:
            params_value[1] = LIFECYCLE_ACTION_DESC[key]
            break

    ret = 0
    for flag in flags.split('|'):
        if flag == "current":
            ret = ret | libvirt.VIR_DOMAIN_AFFECT_CURRENT
        elif flag == "live":
            ret = ret | libvirt.VIR_DOMAIN_AFFECT_LIVE
        elif flag == "config":
            ret = ret | libvirt.VIR_DOMAIN_AFFECT_CONFIG
        elif flag == "none":
            pass
        else:
            logger.error("lifecycle flags value is invalid")
            return 1
    params_value[2] = ret

    return 0


def check_dom_state(domobj, expect_states):
    state = domobj.info()[0]
    if state != expect_states:
        return 1
    return 0


def check_action_result(domobj, guestname, logger, on_type, action):
    if on_type == 0:
        domobj.shutdown()
    elif on_type == 1:
        domobj.reboot()
    else:
        domobj.coreDump("/%s.core" % guestname, libvirt.VIR_DUMP_CRASH)

    time.sleep(30)

    #action destroy or preserve
    if (action == 0 or action == 3) and on_type != 2:
        ret = utils.wait_for(functools.partial(check_dom_state, domobj, 5), 600)
        if ret:
            logger.info("The domain state is not as expected")
            return 1

    #action restart or rename-start or coredump_restart
    elif (action == 1 or action == 2) and on_type != 2:
        ret = utils.wait_for(functools.partial(check_dom_state, domobj, 1), 600)
        domobj.destroy()
        if ret:
            logger.info("The domain state is not as expected")
            return 1

    #action coredump-destroy or coredump-restart or other when on_type is crash
    if on_type == 2:
        cmd = "ls /%s.core" % guestname
        ret = process.system(cmd, shell=True, ignore_status=True)
        if ret:
            return 1

    return 0


def check_result(domobj, guestname, logger, on_type, action, flags):
    #check xml
    if flags & libvirt.VIR_DOMAIN_AFFECT_CONFIG:
        lifecycle_list = get_xml_text(domobj, 2)
    else:
        lifecycle_list = get_xml_text(domobj, 0)

    if LIFECYCLE_ACTION_DESC[lifecycle_list[on_type]] != action:
        logger.error("set lifecycle action failed")
        return 1
    if flags == 0 or flags == 1:
        return check_action_result(domobj, guestname, logger, on_type, action)

    return 0


def set_lifecycle_action(params):
    """
    Changes the actions of lifecycle events for domain represented
    as <on_$type>$action</on_$type> in the domain XML and test if
    it is successful
    Argument is a dictionary with two keys:
    {'logger': logger, 'guestname': guestname}
    logger -- an object of utils/log.py
    mandatory arguments: guestname -- as same the domain name
    optional argument: type -- lifecycle events type,
                                including:"poweroff" "reboot" "crash"
                       action -- lifecycle action,
                                including:"destroy" "restart" "rename-restart"
                                "preserve" "coredump-destroy" "coredump-restart"
                       flags -- affect domain
                                including:"live" "current" "config"
    """
    guestname = params['guestname']
    logger = params['logger']
    params_value = ['', '', '']

    if not version_compare("libvirt-python", 3, 9, 0, logger):
        logger.info("Current libvirt-python don't support setLifecycleAction().")
        return 0

    conn = sharedmod.libvirtobj['conn']
    domobj = conn.lookupByName(guestname)

    ret = get_params(domobj, logger, params, params_value, guestname)
    if ret == 1:
        return 1
    elif ret == 2:
        domobj.destroy()
        return 0

    logger.info("params_value is %s" % params_value)

    on_type = params_value[0]
    action = params_value[1]
    flags = params_value[2]

    try:
        domobj.setLifecycleAction(on_type, action, flags)
    except libvirtError as e:
        logger.info("set lifecycle action failed" + str(e))
        return 1
    ret = check_result(domobj, guestname, logger, on_type, action, flags)
    if ret:
        return 1
    logger.info("PASS")
    return 0


def set_lifecycle_action_clean(params, logger):
    """clean testing environment"""
    on_type = params.get('on_type', 'poweroff')
    logger = params['logger']
    guestname = params['guestname']
    if on_type == 'crash':
        ret = utils.del_file("/%s.core" % guestname, logger)
