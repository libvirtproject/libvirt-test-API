#!/usr/bin/evn python
#Update a network

from libvirt import libvirtError
from src import sharedmod

COMMANDDICT = {"none": 0, "modify": 1, "delete": 2, "add-first": 4}
SECTIONDICT = {"none": 0, "bridge": 1, "domain": 2, "ip": 3, "ip-dhcp-host": 4,
               "ip-dhcp-range": 5, "forward": 6, "forward-interface": 7,
               "forward-pf": 8, "portgroup": 9, "dns-host": 10, "dns-txt": 11,
               "dns-srv": 12}
FLAGSDICT = {"current": 0, "live": 1, "config": 2}

required_params = ('networkname', )
optional_params = {
    'command': 'add-first',
    'section': 'ip-dhcp-host',
    'parentIndex': 0,
    'xml': 'xmls/ip-dhcp-host.xml',
    'flag': 'current',
}


def update(params):
    """Update a network from xml"""
    global logger
    logger = params['logger']
    networkname = params['networkname']
    conn = sharedmod.libvirtobj['conn']

    command = params['command']
    logger.info("The specified command is %s" % command)
    section = params['section']
    logger.info("The specified section is %s" % section)
    parentIndex = int(params.get('parentIndex', 0))
    logger.info("The specified parentIndex is %d" % parentIndex)
    xmlstr = params.get('xml', 'xmls/ip-dhcp-host.xml').replace('\"', '\'')
    logger.info("The specified updatexml is %s" % xmlstr)
    flag = params.get('flag', 'current')
    logger.info("The specified flag is %s" % flag)

    command_val = 0
    section_val = 0
    flag_val = 0
    if command in COMMANDDICT:
        command_val = COMMANDDICT.get(command)
    if section in SECTIONDICT:
        section_val = SECTIONDICT.get(section)
    if flag in FLAGSDICT:
        flag_val = FLAGSDICT.get(flag)

    try:
        network = conn.networkLookupByName(networkname)
        logger.info("The original network xml is %s" % network.XMLDesc(0))
        network.update(command_val, section_val, parentIndex, xmlstr,
                       flag_val)
        updated_netxml = network.XMLDesc(0)
        logger.info("The updated network xml is %s" % updated_netxml)
        #The check only works when flag isn't set as config
        if flag_val != 2:
            if command_val == 0 or command_val == 2:
                if xmlstr not in updated_netxml:
                    logger.info("Successfully update network")
                    return 0
                else:
                    logger.error("Failed to update network")
                    return 1

            elif command_val == 1 or command_val == 4:
                if xmlstr in updated_netxml:
                    logger.info("Successfully update network")
                    return 0
                else:
                    logger.error("Failed to update network")
                    return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.get_error_message(), e.get_error_code()))
        return 1

    return 0
