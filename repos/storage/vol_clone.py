#!/usr/bin/env python
# volume clone testing

import os

from xml.dom import minidom
from libvirt import libvirtError
from src import sharedmod

required_params = ('poolname', 'volname', 'clonevolname',)
optional_params = {}


def prepare_clone_xml(xmlstr, volname):
    """prepare clone xmldesc by replace name element
       with clone souce volume xml
    """
    doc = minidom.parseString(xmlstr)
    oldname = doc.getElementsByTagName("name")[0]

    newname = doc.createElement('name')
    newnameval = doc.createTextNode(volname)
    newname.appendChild(newnameval)

    volume = doc.getElementsByTagName('volume')[0]

    volume.replaceChild(newname, oldname)
    newxmlstr = doc.toxml()

    return newxmlstr


def vol_clone(params):
    """volume clone testing"""

    global logger
    logger = params['logger']
    poolname = params['poolname']
    volname = params['volname']
    clonevolname = params['clonevolname']

    logger.info("the poolname is %s, volname is %s" % (poolname, volname))
    logger.info("the clone volume name is %s" % clonevolname)

    conn = sharedmod.libvirtobj['conn']
    try:
        poolobj = conn.storagePoolLookupByName(poolname)
        old_vol = poolobj.storageVolLookupByName(volname)

        xmlstr = old_vol.XMLDesc(0)
        newxmlstr = prepare_clone_xml(xmlstr, clonevolname)
        logger.debug("volume xml:\n%s" % newxmlstr)

        logger.info("clone volume %s from source volume %s" %
                    (clonevolname, volname))

        old_volnum = poolobj.numOfVolumes()

        new_vol = poolobj.createXMLFrom(newxmlstr, old_vol, 0)
        poolobj.refresh(0)

        new_volnum = poolobj.numOfVolumes()

        logger.debug("new cloned volume path is: %s" % new_vol.path())
        if os.access(new_vol.path(), os.R_OK):
            logger.info("cloned volume path exist")
        else:
            logger.error("cloned volume path not exist")
            return 1

        if new_volnum > old_volnum:
            logger.info("clone succeed")
        else:
            logger.error("clone failed")
            return 1

    except libvirtError as e:
        logger.error("libvirt call failed: " + str(e))
        return 1

    return 0
