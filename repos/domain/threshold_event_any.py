import importlib
import libvirt
from utils.events import eventListenerThreadThreshold, eventLoopPure
from utils.utils import parse_flags, get_rand_str, version_compare

required_params = ('event_runner', )
optional_params = {
    "event_id": None,
    "event_domain": None,
    "event_timeout": 5,
    "event_runner_params": {}
}


def threshold_event_any(params):
    """
    Listen for event, event_runner will do the job to trigger the event
    This test case listen for specified event.
    """
    logger = params['logger']
    event_id = parse_flags(params, param_name="event_id")
    event_runner = params.get('event_runner', None)
    event_domain = params.get('event_domain', None)
    event_runner_params = params.get('event_runner_params', {})
    event_timeout = int(params.get('event_timeout', 5))

    if not version_compare("libvirt-python", 3, 8, 0, logger):
        eventLoopPure(logger)

    if event_domain:
        logger.info("Listening for event on domain %s" % event_domain)
    else:
        logger.info("Listening for events")

    logger.info("event_runner_params: %s" % event_runner_params)
    event_runner_params = dict(eval(str(event_runner_params)))
    threshold = event_runner_params['threshold']

    #String, use it to verify the integrity of callback's extra param
    random_str = get_rand_str()
    eventListener = eventListenerThreadThreshold(
        event_domain, event_id, threshold, logger, random_str)
    eventListener.start()

    try:
        conn = libvirt.open(None)

        domobj = None
        if event_domain:
            domobj = conn.lookupByName(event_domain)

        conn.domainEventRegisterAny(domobj, event_id, eventListener.callbackThreshold, random_str)

        event_runner_entry = event_runner.split(':')[-1]
        event_runner = importlib.import_module('repos.' + event_runner.replace(":", "."))
        event_runner_params.update({"logger": logger})
        #TODO: Multilevel param parsing instead of use eval to convert string to dict
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
            conn.domainEventDeregisterAny(0)
        except Exception:
            logger.error("Failed to unregist.")
        eventListener.stop()
