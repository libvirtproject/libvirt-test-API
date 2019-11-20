#!/usr/bin/env python
import os
import shutil
import tempfile
import re
import requests

from utils import utils

brickpath = "/tmp/test-api-brick"
imagename = "libvirt-test-api"


def setup_storage(params, mountpath, logger):
    storage = params.get('storage', 'local')
    sourcehost = params.get('sourcehost')
    sourcepath = params.get('sourcepath')
    diskpath = ""
    if storage == "local":
        diskpath = params.get('diskpath', "/var/lib/libvirt/images/libvirt-test-api")
    else:
        if storage == "gluster":
            if not os.path.isdir(brickpath):
                os.mkdir(brickpath, 0755)
            utils.setup_gluster("test-api-gluster", utils.get_local_hostname(), brickpath, logger)
            utils.mount_gluster("test-api-gluster", utils.get_local_hostname(), mountpath, logger)
        elif storage == "nfs":
            utils.setup_nfs(sourcehost, sourcepath, mountpath, logger)
        elif storage == "iscsi":
            utils.setup_iscsi(sourcehost, sourcepath, mountpath, logger)
        else:
            logger.error("%s is not exists." % storage)
            mountpath = ""
        diskpath = mountpath + "/" + imagename
    return diskpath


def cleanup_storage(params, mountpath, logger):
    storage = params.get('storage', 'local')
    sourcepath = params.get('sourcepath')
    if storage == "gluster":
        utils.umount_gluster(mountpath, logger)
        utils.cleanup_gluster("test-api-gluster", logger)
        if os.path.isdir(brickpath):
            shutil.rmtree(brickpath)
    elif storage == "nfs":
        utils.cleanup_nfs(mountpath, logger)
    elif storage == "iscsi":
        utils.cleanup_iscsi(sourcepath, mountpath, logger)

    shutil.rmtree(mountpath)


def get_iscsi_disk_path(portal, target):
    dev_path = "/dev/disk/by-path/"
    if os.path.exists(dev_path):
        disk = "ip-%s:3260-iscsi-%s-lun" % (portal, target)
        devices = []
        devices = os.listdir(dev_path)
        for dev in devices:
            if disk in dev:
                return (dev_path + dev)
    return ""


def get_path_from_url(url, key):
    web_con = requests.get(url)
    match = re.compile(r'<a href=".*">.*%s</a>' % key)
    name = re.findall(match, web_con.content)[0].split("\"")[1]
    path = "%s/%s" % (url, name)
    return path
