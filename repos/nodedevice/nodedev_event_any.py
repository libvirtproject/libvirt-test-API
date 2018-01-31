import importlib
from src import sharedmod
from utils.events import eventListenerThread, eventLoopPure
from utils.utils import parse_flags, get_rand_str, version_compare

required_params = ('event_runner',)
optional_params = {
    "nodedev_name": "",
    "xml": "xmls/virtual_hba.xml",
    "event_id": None,
    "event_type": None,
    "event_detail": None,
    "event_timeout": 5,
    "event_runner_params": {}
}


def nodedev_event_any(params):
    logger = params['logger']
    nodedev_name = params.get('nodedev_name', None)
    nodedev_xml = params.get('xml', None)
    event_id = parse_flags(params, param_name="event_id")
    event_type = parse_flags(params, param_name="event_type")
    event_detail = parse_flags(params, param_name="event_detail")
    event_runner = params.get('event_runner', None)
    event_runner_params = params.get('event_runner_params', {})
    event_timeout = int(params.get('event_timeout', 5))

    if not version_compare("libvirt-python", 3, 8, 0, logger):
        eventLoopPure(logger)

    if nodedev_name:
        logger.info("Listening for event on %s" % nodedev_name)
    else:
        logger.info("Listening for events")

    #String, use it to verify the integrity of callback's extra param

    random_str = get_rand_str()
    eventListener = eventListenerThread(nodedev_name, event_id, event_type,
                                        event_detail, logger, random_str)
    eventListener.start()

    try:
        conn = sharedmod.libvirtobj['conn']

        nodedevobj = None
        id = conn.nodeDeviceEventRegisterAny(nodedevobj, event_id,
                                             eventListener.callback,
                                             random_str)

        event_runner_entry = event_runner.split(':')[-1]
        event_runner = importlib.import_module(
            'repos.' + event_runner.replace(":", "."))
        event_runner_params = dict(eval(str(event_runner_params)))
        event_runner_params.update({"logger": logger})
        if nodedev_xml:
            event_runner_params.update({"xml": nodedev_xml})
        #TODO: Multilevel param parsing instead of use eval
        # to convert string to dict
        try:
            if getattr(event_runner, event_runner_entry)(event_runner_params):
                logger.error("Event trigger returned with error.")
                return 1
        except Exception, e:
            logger.error(str(e))
            logger.error("Something went wrong, exiting...")
            return 1

        eventListener.join(event_timeout)

        if eventListener.result:
            return 0

        logger.error("Callback didn't get expected event and opaque")
        return 1

    finally:
        try:
            conn.nodeDeviceEventDeregisterAny(id)
        except Exception as e:
            logger.error("Failed to unregist. %s", e)
        eventListener.stop()
