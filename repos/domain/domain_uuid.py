#!/usr/bin/env python
import uuid

from src import sharedmod
from libvirt import libvirtError
from utils import process

required_params = ('guestname',)
optional_params = {}

VIRSH_DOMUUID = "virsh domuuid"
RUNNING_DIR = '/var/run/libvirt/qemu'
CONFIG_DIR = '/etc/libvirt/qemu'
NEGATIVE_UUID = ['----', None, 123, ]


def check_domain_exists(conn, guestname, logger):
    " check if the domain exists, may or may not be active "
    guest_names = []
    ids = conn.listDomainsID()
    for id in ids:
        obj = conn.lookupByID(id)
        guest_names.append(obj.name())

    guest_names += conn.listDefinedDomains()
    if guestname not in guest_names:
        logger.error("%s doesn't exist" % guestname)
        return False
    return True


def check_domain_uuid_with_virsh(guestname, UUIDString, logger):
    """ check UUID String of guest with virsh """
    cmd = VIRSH_DOMUUID + ' %s' % guestname
    ret = process.run(cmd, shell=True, ignore_status=True)
    if ret.exit_status:
        logger.error("executing " + "\"" + VIRSH_DOMUUID + ' %s' % guestname + "\"" + " failed")
        logger.error(ret.stdout)
        return False
    else:
        UUIDString_virsh = ret.stdout
        logger.debug("UUIDString from API is %s" % UUIDString)
        logger.debug("UUIDString from virsh domuuid is %s" % UUIDString_virsh)
        if UUIDString == ret.stdout:
            return True
        else:
            return False


def check_lookupByUUIDString(conn, domain, UUIDString, logger):
    if domain.XMLDesc() != conn.lookupByUUIDString(UUIDString).XMLDesc():
        logger.error("lookupByUUIDString Failed")
        return False
    logger.info("lookupByUUIDString success")
    return True


def check_lookupByUUID(conn, domain, UUID, logger):
    if domain.XMLDesc() != conn.lookupByUUID(UUID).XMLDesc():
        logger.error("lookupByUUID Failed")
        return False
    logger.info("lookupByUUID success")
    return True


def negative_tests(conn, logger):
    logger.info("Negative test...")
    for dom_uuid in NEGATIVE_UUID:
        logger.info("Try UUID %s ..." % str(dom_uuid))
        success = False
        try:
            lookup_result = conn.lookupByUUIDString(dom_uuid)
        except Exception as e:
            try:
                lookup_result = conn.lookupByUUID(dom_uuid)
            except Exception as e:
                success = True
                logger.info("Negative test success with %s" % str(e))
                return True

        if success is False:
            logger.error("Negative test failed with uuid %s" % dom_uuid)
            return False


def domain_uuid(params):
    """ check domain UUID related APIs
    """
    logger = params['logger']
    guestname = params.get('guestname', None)
    conn = sharedmod.libvirtobj['conn']
    logger.info("guest name is %s" % guestname)
    domain = conn.lookupByName(guestname)

    try:
        if not check_domain_exists(conn, guestname, logger):
            return 1

        logger.info("get the UUID string of %s" % domain.name())
        UUIDString = domain.UUIDString()
        logger.info("UUID String is %s" % UUIDString)

        if uuid.UUID(UUIDString).bytes != domain.UUID():
            logger.info("Raw UUID don't match UUID String")
            return 1
        logger.info("Raw UUID match UUID String")

        if not check_lookupByUUIDString(conn, domain, UUIDString, logger):
            return 1

        if not check_lookupByUUID(conn, domain, uuid.UUID(UUIDString).bytes, logger):
            return 1

    except libvirtError as e:
        logger.error("API error message: %s, error code is %s"
                     % (e.message, e.get_error_code()))
        return 1

    if not check_domain_uuid_with_virsh(domain.name(), UUIDString, logger):
        logger.error("UUIDString from API is not the same as the one from virsh")
        return 1
    logger.info("UUIDString from API is the same as the one from virsh")

    if not negative_tests(conn, logger):
        return 1

    return 0
