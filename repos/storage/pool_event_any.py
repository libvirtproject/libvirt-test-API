import libvirt
import importlib
from src import sharedmod
from utils.events import eventListenerThread, virEventLoopPureThread
from utils.utils import parse_flags, get_rand_str


required_params = ('event_runner', )
optional_params = {
    "poolname": "",
    "event_id": None,
    "event_type": None,
    "event_detail": None,
    "event_timeout": 5,
    "event_runner_params": {}
}


def pool_event_any(params):
    """
    Listen for event, event_runner will do the job to trigger the event
    This test case listen for specified event.
    """
    logger = params['logger']
    poolname = params.get('poolname', None)
    event_id = parse_flags(params, param_name="event_id")
    event_type = parse_flags(params, param_name="event_type")
    event_detail = parse_flags(params, param_name="event_detail")
    event_runner = params.get('event_runner', None)
    event_runner_params = params.get('event_runner_params', {})
    event_timeout = int(params.get('event_timeout', 5))

    if poolname:
        logger.info("Listening for event on pool %s" % poolname)
    else:
        logger.info("Listening for events")

    eventLoop = virEventLoopPureThread(logger)
    eventLoop.regist(libvirt)
    eventLoop.start()

    #String, use it to verify the integrity of callback's extra param

    random_str = get_rand_str()
    eventListener = eventListenerThread(poolname, event_id, event_type,
                                        event_detail, logger, random_str)
    eventListener.start()

    try:
        conn = sharedmod.libvirtobj['conn']

        poolobj = None
        if poolname:
            poolobj = conn.storagePoolLookupByName(poolname)

        conn.storagePoolEventRegisterAny(poolobj, event_id,
                                         eventListener.callback,
                                         random_str)

        event_runner_entry = event_runner.split(':')[-1]
        event_runner = importlib.import_module(
            'repos.' + event_runner.replace(":", "."))
        event_runner_params = dict(eval(str(event_runner_params)))
        event_runner_params.update({"logger": logger})
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
            conn.storagePoolEventDeregisterAny(0)
        except Exception as e:
            logger.error("Failed to unregist. %s", e)
        eventListener.stop()
        eventLoop.stop()
