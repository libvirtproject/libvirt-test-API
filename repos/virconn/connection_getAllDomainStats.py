#!/usr/bin/env python
# test getAllDomainStats() API for libvirt

import libvirt

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod
from utils import utils

required_params = ()
optional_params = {'stats': '', 'flags': '', 'doms': '', 'iothread_id': ''}

ds = {"state": libvirt.VIR_DOMAIN_STATS_STATE,
      "cpu": libvirt.VIR_DOMAIN_STATS_CPU_TOTAL,
      "balloon": libvirt.VIR_DOMAIN_STATS_BALLOON,
      "vcpu": libvirt.VIR_DOMAIN_STATS_VCPU,
      "interface": libvirt.VIR_DOMAIN_STATS_INTERFACE,
      "block": libvirt.VIR_DOMAIN_STATS_BLOCK,
      "perf": libvirt.VIR_DOMAIN_STATS_PERF}

fg = {"active": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE,
      "inactive": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_INACTIVE,
      "persistent": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_PERSISTENT,
      "transient": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_TRANSIENT,
      "running": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_RUNNING,
      "paused": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_PAUSED,
      "shutoff": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_SHUTOFF,
      "other": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_OTHER,
      "backing": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_BACKING,
      "enforce": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_ENFORCE_STATS,
      "nowait": libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_NOWAIT}


def filer_domains(logger, flags):
    """
       return a filtered domains set
    """
    a = set(active_domains(logger))
    d = set(defined_domains(logger))
    if flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_PERSISTENT and \
       flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_TRANSIENT:
        domains = a | d
    elif flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_PERSISTENT:
        domains = d
    elif flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_TRANSIENT:
        domains = a - d
    else:
        domains = a | d
    if flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE and \
       flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_INACTIVE:
        domains &= (a | d)
    elif flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_ACTIVE:
        domains &= a
    elif flags & libvirt.VIR_CONNECT_GET_ALL_DOMAINS_STATS_INACTIVE:
        domains &= (d - a)
    else:
        domains &= a | d
    return domains


def active_domains(logger):
    """
       return active domains on current uri
    """
    NUM = "ls /run/libvirt/qemu|grep \".xml\""
    status, output = utils.exec_cmd(NUM, shell=True)
    output = [item.replace(".xml", "") for item in output]
    if status == 0:
        logger.debug("Got active domains: %s" % output)
        return output
    else:
        logger.debug("Got active domains: %s" % output)
        return output


def defined_domains(logger):
    """
       return defined domains on current uri
    """
    NUM = "ls /etc/libvirt/qemu|grep \".xml\""
    status, output = utils.exec_cmd(NUM, shell=True)
    output = [item.replace(".xml", "") for item in output]
    if status == 0:
        logger.debug("Got defined domains: %s" % output)
        return output
    else:
        logger.debug("Got defined domains: %s" % output)
        return output


def compare_value(logger, op1, op2):
    """
       compare 2 variables value
    """
    if op1 != op2:
        logger.debug("Check %s: Fail" % op2)
        return False
    else:
        logger.debug("Check %s: Pass" % op2)
        return True


def check_vcpu(logger, dom_name, dom_active, dom_eles):
    """
       check vcpu info of given domain
    """
    iDOM_XML = "/etc/libvirt/qemu/" + dom_name + ".xml"
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    if dom_active:
        xml = minidom.parse(aDOM_XML)
        dom = xml.getElementsByTagName('domain')[0]
        vcpu = dom.getElementsByTagName('vcpu')[0]
        vcpu_max = int(vcpu.childNodes[0].data)
        if not vcpu.getAttribute('current'):
            vcpu_cur = vcpu_max
        else:
            vcpu_cur = int(vcpu.getAttribute('current'))

        logger.debug("Checking vcpu.current: %d"
                     % dom_eles.get("vcpu.current"))
        if not compare_value(logger, vcpu_cur,
                             dom_eles.get("vcpu.current")):
            return False
        logger.debug("Checking vcpu.maximum: %d"
                     % dom_eles.get("vcpu.maximum"))
        if not compare_value(logger, vcpu_max,
                             dom_eles.get("vcpu.maximum")):
            return False
    else:
        xml = minidom.parse(iDOM_XML)
        vcpu = xml.getElementsByTagName('vcpu')[0]
        vcpu_max = int(vcpu.childNodes[0].data)
        logger.debug("Checking vcpu.maximum: %d"
                     % dom_eles.get("vcpu.maximum"))
        if not compare_value(logger, vcpu_max,
                             dom_eles.get("vcpu.maximum")):
            return False
    #for each vcpu.state field
    check_each_vcpu(logger, dom_name, dom_active, dom_eles)
    return True


def check_each_vcpu(logger, dom_name, dom_active, dom_eles):
    """
       check each vcpu info, but ignore vcpu.*.time
    """
    iDOM_XML = "/etc/libvirt/qemu/" + dom_name + ".xml"
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    vcpu_index = 0
    if dom_active:
        vcpu_stat = 1
        xml = minidom.parse(aDOM_XML)
        dom = xml.getElementsByTagName('vcpus')[0]
        dom_pid = str(xml.getElementsByTagName("domstatus")[0].
                      getAttributeNode('pid').nodeValue)
        vcpu = dom.getElementsByTagName('vcpu')
        for vcpu_sub in vcpu:
            proc_path = "/proc/"
            vcpu_pre = "vcpu." + str(vcpu_index) + "."
            attr1 = dom_eles.get(vcpu_pre + "state")
            logger.debug("Checking %sstate: %d" % (vcpu_pre, attr1))
            if not compare_value(logger, vcpu_stat, attr1):
                return False
            vcpu_index += 1
    else:
        vcpu_stat = 0
        xml = minidom.parse(iDOM_XML)
        vcpu = xml.getElementsByTagName('vcpu')[0]
        vcpu_max = int(vcpu.childNodes[0].data)
        vcpu_cur = vcpu.getAttributeNode('current')
        if not vcpu_cur:
            for i in range(0, vcpu_max):
                vcpu_pre = "vcpu." + str(i) + "."
                logger.debug("Checking %sstate: %s"
                             % (vcpu_pre, dom_eles.get(vcpu_pre + "state")))
                if not compare_value(logger, vcpu_stat,
                                     dom_eles.get(vcpu_pre + "state")):
                    return False
        elif int(vcpu_cur.nodeValue) <= vcpu_max:
            for i in range(0, int(vcpu_cur.nodeValue)):
                vcpu_pre = "vcpu." + str(i) + "."
                logger.debug("Checking %sstate: %s"
                             % (vcpu_pre, dom_eles.get(vcpu_pre + "state")))
                if not compare_value(logger, vcpu_stat,
                                     dom_eles.get(vcpu_pre + "state")):
                    return False
    return True


def check_balloon(logger, dom_name, dom_active, dom_eles):
    """
       check balloon of given domain
    """
    iDOM_XML = "/etc/libvirt/qemu/" + dom_name + ".xml"
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    if dom_active:
        xml = minidom.parse(aDOM_XML)
        dom = xml.getElementsByTagName('domain')[0]
        mem_max = int(dom.getElementsByTagName('memory')[0]
                      .childNodes[0].data)
        mem_cur = int(dom.getElementsByTagName('currentMemory')[0]
                      .childNodes[0].data)
        logger.debug("Checking balloon.maximum: %d"
                     % dom_eles.get("balloon.maximum"))
        if not compare_value(logger, mem_max,
                             dom_eles.get("balloon.maximum")):
            return False
        logger.debug("Checking balloon.current: %d"
                     % dom_eles.get("balloon.current"))
        if not compare_value(logger, mem_cur,
                             dom_eles.get("balloon.current")):
            return False
    else:
        xml = minidom.parse(iDOM_XML)
        mem_max = int(xml.getElementsByTagName('memory')[0].
                      childNodes[0].data)
        logger.debug("Checking balloon.maximum: %d"
                     % dom_eles.get("balloon.maximum"))
        if not compare_value(logger, mem_max,
                             dom_eles.get("balloon.maximum")):
            return False
    return True


def check_interface(logger, dom_name, dom_active, dom_eles):
    """
       check interface info, only check the count and name  attributes
       other sub-attributes of net.* will be ignored
    """
    iDOM_XML = "/etc/libvirt/qemu/" + dom_name + ".xml"
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    netfile = "/proc/net/dev"
    if dom_active:
        xml = minidom.parse(aDOM_XML)
        dom = xml.getElementsByTagName('domain')[0]
        dev = dom.getElementsByTagName('devices')[0]
        nic = dev.getElementsByTagName('interface')
        logger.debug("Checking net.count: %d" % dom_eles.get("net.count"))
        if not compare_value(logger, len(nic), dom_eles.get("net.count")):
            return False
        for iface in nic:
            if_name = iface.getElementsByTagName("target")[0].\
                getAttribute('dev')
            if_name += ":"
            logger.debug("Checking %s" % if_name)
            content = open(netfile, 'r')
            if if_name in str(content.readlines()):
                logger.debug("Check %s: Pass" % if_name)
            else:
                logger.debug("Check %s: Fail" % if_name)
                return False
            content.close()
    else:
        pass
    return True


def count_disk_chain(logger, filepath, dom_active):
    """
       count deep of disk chain
    """
    CMD = "file %s"
    num = 0
    while True:
        status, output = utils.exec_cmd(CMD % filepath, shell=True)
        if status != 0:
            logger.debug("Can not see the back file")
        if "has backing file" in output[0]:
            num += 1
            filepath = output[0].split("(path")[1].split(")")[0].strip()
        else:
            break
        if not dom_active:
            break
    return num


def check_block(logger, dom_name, dom_active, dom_eles, backing_f):
    """
       check the block info, only check count, name and path attributes,
       other sub-attributes of block.* will be ignored
    """
    iDOM_XML = "/etc/libvirt/qemu/" + dom_name + ".xml"
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    disk_index = 0
    if dom_active:
        xml = minidom.parse(aDOM_XML)
        dom = xml.getElementsByTagName('domain')[0]
        dev = dom.getElementsByTagName('devices')[0]
        disk = dev.getElementsByTagName('disk')
        disk_count = len(disk)
        for dk in disk:
            disk_name = dk.getElementsByTagName('target')[0]\
                .getAttributeNode('dev').nodeValue
            disk_sour = dk.getElementsByTagName('source')[0]\
                .getAttributeNode('file').nodeValue
            if backing_f:
                disk_count += count_disk_chain(logger, disk_sour, dom_active)
        logger.debug("Checking disk.count: %d" % dom_eles.get("block.count"))
        if not compare_value(logger, disk_count, dom_eles.get("block.count")):
            return False
        if not check_each_block(logger, dom_name, dom_eles, backing_f):
            return False
    else:
        xml = minidom.parse(iDOM_XML)
        dev = xml.getElementsByTagName('devices')[0]
        disk = dev.getElementsByTagName('disk')
        disk_count = len(disk)
        logger.debug("Checking disk.count: %d" % dom_eles.get("block.count"))
        if not compare_value(logger, disk_count, dom_eles.get("block.count")):
            return False
        for dk in disk:
            disk_pre = "block." + str(disk_index) + "."
            disk_name = dk.getElementsByTagName('target')[0]\
                .getAttributeNode('dev').nodeValue
            logger.debug("Checking %sname: %s"
                         % (disk_pre, dom_eles.get(disk_pre + "name")))
            if not compare_value(logger, disk_name,
                                 dom_eles.get(disk_pre + "name")):
                return False
            disk_sour = dk.getElementsByTagName('source')[0]\
                .getAttributeNode('file').nodeValue
            logger.debug("Checking %spath: %s"
                         % (disk_pre, dom_eles.get(disk_pre + "path")))
            if not compare_value(logger, disk_sour,
                                 dom_eles.get(disk_pre + "path")):
                return False
            disk_index += 1
    return True


def check_each_block(logger, dom_name, dom_eles, backing_f):
    """
       for a active domain, this function will list all backing
       block info
    """
    aDOM_XML = "/run/libvirt/qemu/" + dom_name + ".xml"
    disk_index = 0
    xml = minidom.parse(aDOM_XML)
    dom = xml.getElementsByTagName('domain')[0]
    dev = dom.getElementsByTagName('devices')[0]
    disk = dev.getElementsByTagName('disk')
    for dk in disk:
        disk_pre = "block." + str(disk_index) + "."
        disk_name = dk.getElementsByTagName('target')[0]\
            .getAttributeNode('dev').nodeValue
        disk_sour = dk.getElementsByTagName('source')[0]\
            .getAttributeNode('file').nodeValue
        logger.debug("Checking %s %s" % (disk_name, disk_sour))
        if not compare_value(logger, disk_name,
                             dom_eles.get(disk_pre + "name")):
            return False
        if not compare_value(logger, disk_sour,
                             dom_eles.get(disk_pre + "path")):
            return False
        if not backing_f:
            disk_index += 1
            continue
        while True:
            temp = dk.getElementsByTagName('backingStore')[0]
            if temp.hasChildNodes():
                temp_name = disk_name
                temp_backingIndex = int(temp.getAttributeNode('index').
                                        nodeValue)
                temp_path = temp.getElementsByTagName('source')[0].\
                    getAttributeNode('file').nodeValue
                logger.debug("Checking %s %s %s"
                             % (temp_name, temp_backingIndex, temp_path))
                disk_index += 1
                disk_pre = "block." + str(disk_index) + "."
                if not compare_value(logger, temp_name,
                                     dom_eles.get(disk_pre + "name")):
                    return False
                if not compare_value(logger, temp_backingIndex,
                                     dom_eles.get(disk_pre + "backingIndex")):
                    return False
                if not compare_value(logger, temp_path,
                                     dom_eles.get(disk_pre + "path")):
                    return False
            else:
                break
            dk = temp
        disk_index += 1
    return True


def check_perf(logger, dom_name, dom_active, dom_eles):
    # TODO: add check for perf
    logger.info("check perf")
    return True


def check_iothread(logger, dom_name, dom_active, dom_eles, iothread_id):
    # check for iothread values
    # default values:
    #   poll-max-ns: 32768
    #   poll-grow: 0
    #   poll-shrink: 0
    logger.info("check iothread values")
    if dom_eles['iothread.%s.poll-max-ns' % iothread_id] != 32768:
        logger.error("check iothread.%s.poll-max-ns failed." % iothread_id)
        return False
    if dom_eles['iothread.%s.poll-grow' % iothread_id] != 0:
        logger.error("check iothread.%s.poll-grow failed." % iothread_id)
        return False
    if dom_eles['iothread.%s.poll-shrink' % iothread_id] != 0:
        logger.error("check iothread.%s.poll-shrink failed." % iothread_id)
        return False

    return True


def connection_getAllDomainStats(params):
    """
       test API for getAllDomainStats in class virConnect, the script need
       static values to compare with those returned by API,but they are
       hard to calculate, so ignore below attributes temporarily:
           cpu.time
           cpu.user
           cpu.system
           *.*.time
           net.*.rx.*
           net.*.tx.*
           block.*.rd
           block.*.wr
           block.*.fl
           ...
      for below two attributes, no good method to obtain values when
      out of libvirt, pass them temporarily too.
           state.state
           state.reason
    """
    balloon_f = False
    vcpu_f = False
    interface_f = False
    block_f = False
    backing_f = False
    filter_f = True
    perf_f = False
    iothread_f = False

    logger = params['logger']
    domstats = params.get('stats', "all")
    domstats_string = domstats.split("|")
    logger.info("The stats are %s" % domstats)
    domstats = 0
    for domstat in domstats_string:
        if domstat == 'state':
            domstats |= ds.get('state')
        elif domstat == 'cpu':
            domstats |= ds.get('cpu')
        elif domstat == 'balloon':
            domstats |= ds.get('balloon')
            balloon_f = True
        elif domstat == 'vcpu':
            domstats |= ds.get('vcpu')
            vcpu_f = True
        elif domstat == 'interface':
            domstats |= ds.get('interface')
            interface_f = True
        elif domstat == 'block':
            domstats |= ds.get('block')
            block_f = True
        elif domstat == 'perf':
            domstats |= ds.get('perf')
            perf_f = True
        elif domstat == 'iothread':
            if not utils.version_compare('libvirt-python', 5, 0, 0, logger):
                logger.info("Current libvirt-python don't support VIR_DOMAIN_STATS_IOTHREAD.")
                return 0
            else:
                ds['iothread'] = libvirt.VIR_DOMAIN_STATS_IOTHREAD
                domstats |= ds.get('iothread')
                iothread_f = True
                iothread_id = params.get("iothread_id")
        elif domstat == "all":
            domstats = 0
            balloon_f = True
            vcpu_f = True
            interface_f = True
            block_f = True
        else:
            logger.error("Unknown flags")
            return 1
    logger.info("The given stats is %d" % domstats)

    flags = params.get('flags', "all")
    logger.info("The flags are %s" % flags)
    flags_string = flags.split("|")
    flags = 0
    for flag in flags_string:
        if flag == 'active':
            flags |= fg.get('active')
        elif flag == 'inactive':
            flags |= fg.get('inactive')
        elif flag == 'persistent':
            flags |= fg.get('persistent')
        elif flag == 'transient':
            flags |= fg.get('transient')
        elif flag == 'running':
            flags |= fg.get('running')
            filter_f = False
        elif flag == 'paused':
            flags |= fg.get('paused')
            filter_f = False
        elif flag == 'shutoff':
            flags |= fg.get('shutoff')
            filter_f = False
        elif flag == 'other':
            flags |= fg.get('other')
            filter_f = False
        elif flag == 'backing':
            flags |= fg.get('backing')
            backing_f = True
        elif flag == 'enforce':
            flags |= fg.get('enforce')
        elif flag == 'nowait':
            if not utils.version_compare('libvirt-python', 4, 5, 0, logger):
                logger.info("Current libvirt-python don't support VIR_CONNECT_GET_ALL_DOMAINS_STATS_NOWAIT.")
            else:
                flags |= fg.get('nowait')
        elif flag == 'all':
            flags = 0
            filter_f = False
        else:
            logger.error("Unknown flags")
            return 1
    logger.info("The given flags is %d" % flags)

    if "doms" in params:
        doms = params.get('doms')
        doms_string = doms.split("|")
        doms_list = []
        for name in doms_string:
            doms_list.append(name)
        doms = doms_list
        flags &= 0xfc0000000
        filter_f = True
        logger.info("The revision flags is %d" % flags)
    else:
        doms = []

    try:
        conn = sharedmod.libvirtobj['conn']
        if len(doms) == 0:
            domstats_from_api = conn.getAllDomainStats(domstats, flags)
            logger.info("Got the number of domain from API: %s"
                        % len(domstats_from_api))
        else:
            logger.info("The given domains: %s" % doms)
            domstats_from_api = conn.domainListGetStats(
                [conn.lookupByName(name) for name in doms], domstats, flags)
        #filter expected domains
        domains = filer_domains(logger, flags)
        if not filter_f:
            logger.info("Check the number of domain: Skip")
        elif len(doms) == 0 and len(domains) == len(domstats_from_api):
            logger.info("Available domains: %s" % list(domains))
            logger.info("Check the number of domain %d: Pass"
                        % len(domstats_from_api))
        elif len(doms) > 0 and len(doms) == len(domstats_from_api):
            logger.info("Available domains: %s" % doms)
            logger.info("Check the number of domain %d: Pass"
                        % len(domstats_from_api))
        else:
            logger.info("Available domains: %s" % list(domains))
            logger.info("Check the number of domain %d: Fail"
                        % len(domstats_from_api))
            return 1

        for dom in domstats_from_api:
            dom_name = dom[0].name()
            dom_active = dom[0].isActive()
            dom_eles = dom[1]
            logger.debug("Domain elements are %s" % (dom_eles))
            logger.info("Checking %s:" % (dom_name))
            if vcpu_f:
                if not check_vcpu(logger, dom_name, dom_active, dom_eles):
                    logger.info("Failed to check vcpu states")
                    return 1
                else:
                    logger.info("Success to check vcpu state")
            if balloon_f:
                if not check_balloon(logger, dom_name, dom_active, dom_eles):
                    logger.info("Failed to check balloon state")
                    return 1
                else:
                    logger.info("Success to check balloon state")
            if interface_f:
                if not check_interface(logger, dom_name, dom_active, dom_eles):
                    logger.info("Failed to check interface state")
                    return 1
                else:
                    logger.info("Success to check interface state")
            if block_f:
                if not check_block(logger, dom_name, dom_active,
                                   dom_eles, backing_f):
                    logger.info("Failed to check block state")
                    return 1
                else:
                    logger.info("Success to check block state")
            if perf_f:
                if not check_perf(logger, dom_name, dom_active, dom_eles):
                    logger.info("Failed to check perf state")
                    return 1
                else:
                    logger.info("Success to check perf state")
            if iothread_f:
                if not check_iothread(logger, dom_name, dom_active, dom_eles, iothread_id):
                    logger.info("Failed to check iothread state")
                else:
                    logger.info("Success to check iothread state")

    except libvirtError as e:
        logger.error("API error message: %s" % e.get_error_message())
        return 1

    return 0
