import os
import time
import errno
import select
import threading
import libvirt

from .utils import version_compare

class eventListenerThread(threading.Thread):
    def __init__(self, event_source, event_id, event_type, event_detail, logger, rand=None):
        """
        A thread that will keep looping until callback is called with a event matches
        given event id, detail and type.

        use join(timeout) and stop to wait for a event
        eg:
            thread = eventListenerThread("domain_name",
                                         libvirt.VIR_DOMAIN_EVENT_ID_LIFECYCLE,
                                         libvirt.VIR_DOMAIN_EVENT_DEFINED,
                                         libvirt.VIR_DOMAIN_EVENT_DEFINED_ADDED,
                                         logger,
                                         "ksNsd*2s1."
            )
            try:
                thread.start()
                # Test Code here
                # Remember to add thread.callback to event handlers
                thread.join(10)
                if thread.result:
                    # Got wanted event
                else:
                    # Didn't get the event :(
            finally:
                thread.stop()

        :param event_source: Where the waiting event should come from
            could be a domain/node device/others.
        :param event_id: (Not actually used yet).
        :param event_type: Event type to wait for.
        :param event_detail: Event detail to wait for.
        :param rand: A random string, you can use it to verify opaque's integrity.
            If not given, callback's opaque will be ignored.
            If given, callback's opaque need to be the same string.
        """
        threading.Thread.__init__(self, name="libvirtEventListener")
        self.result = None
        self.rand = rand
        self.logger = logger
        self.event_id = event_id
        self.event_type = event_type
        self.event_detail = event_detail
        self.event_source = event_source

    def callback(self, conn, source, event_type, event_detail, opaque):
        random = opaque
        logger = self.logger
        if hasattr(source, 'name'):
            src_name = source.name()
        else:
            src_name = str(source)
        if hasattr(source, 'UUIDString'):
            src_idtype, src_id = 'UUID: ', source.UUIDString()
        elif hasattr(source, 'ID'):
            src_idtype, src_id = 'ID: ', str(source.ID())
        else:
            src_idtype, src_id = 'NO ID Avaliable', ''

        logger.info("Got EVENT: From %s (%s%s), Type:%s, Detail:%s" %
                    (src_name, src_idtype, src_id, event_type, event_detail))

        if random != self.rand:
            logger.error("Callback's opaque is currupted !")
            return
        if self.event_type is not None and event_type != self.event_type:
            logger.error("Wrong event type!")
            return
        if self.event_detail is not None and event_detail != self.event_detail:
            logger.error("Wrong event detail!")
            return
        if self.event_source is not None and source.name() != self.event_source:
            logger.error("Wrong event source!")
            return
        logger.info("Just as expected!")
        self.result = True
        return

    def run(self):
        while self.result is None:
            time.sleep(1)

    def stop(self):
        self.result = False


class eventListenerThreadThreshold(threading.Thread):
    def __init__(self, event_source, event_id, threshold, logger, rand=None):
        threading.Thread.__init__(self, name="libvirtEventListener")
        self.result = None
        self.rand = rand
        self.logger = logger
        self.event_id = event_id
        self.event_source = event_source
        self.threshold = threshold

    def callbackThreshold(self, conn, source, dev, path, threshold, excess, opaque):
        random = opaque
        logger = self.logger
        if hasattr(source, 'name'):
            src_name = source.name()
        else:
            src_name = str(source)
        if hasattr(source, 'UUIDString'):
            src_idtype, src_id = 'UUID: ', source.UUIDString()
        elif hasattr(source, 'ID'):
            src_idtype, src_id = 'ID: ', str(source.ID())
        else:
            src_idtype, src_id = 'NO ID Avaliable', ''

        logger.info("Got EVENT: From %s (%s%s), Threshold:%s" %
                    (src_name, src_idtype, src_id, threshold))

        if random != self.rand:
            logger.error("Callback's opaque is currupted !")
            return
        if self.event_source is not None and source.name() != self.event_source:
            logger.error("Wrong event source!")
            return
        if self.threshold is not None and str(threshold) != self.threshold:
            logger.error("Wrong threshold!")
            return

        logger.info("Just as expected!")
        self.result = True

    def run(self):
        while self.result is None:
            time.sleep(1)

    def stop(self):
        self.result = False


###############################################################
# Following class is a wrap up of the event loop
# from libvirt-python/examples/event-test.py
###############################################################
#
# This general purpose event loop will support waiting for file handle
# I/O and errors events, as well as scheduling repeatable timers with
# a fixed interval.
#
# It is a pure python implementation based around the poll() API
#
class virEventLoopPureThread(threading.Thread):
    """
    To use this standalone pure event loop,
    Init a instance, regist and run it. Remember to stop the running thread
    before test ends.
    eg:
        loop = virEventLoopPure(logger)
        try:
            loop.regist(libvirt)
            loop.start()
            # Run test here
        finally:
            loop.stop()
    """
    # This class contains the data we need to track for a
    # single file handle

    class virEventLoopPureHandle:

        def __init__(self, handle, fd, events, cb, opaque):
            self.handle = handle
            self.fd = fd
            self.events = events
            self.cb = cb
            self.opaque = opaque

        def get_id(self):
            return self.handle

        def get_fd(self):
            return self.fd

        def get_events(self):
            return self.events

        def set_events(self, events):
            self.events = events

        def dispatch(self, events):
            self.cb(self.handle,
                    self.fd,
                    events,
                    self.opaque)

    # This class contains the data we need to track for a
    # single periodic timer
    class virEventLoopPureTimer:

        def __init__(self, timer, interval, cb, opaque):
            self.timer = timer
            self.interval = interval
            self.cb = cb
            self.opaque = opaque
            self.lastfired = 0

        def get_id(self):
            return self.timer

        def get_interval(self):
            return self.interval

        def set_interval(self, interval):
            self.interval = interval

        def get_last_fired(self):
            return self.lastfired

        def set_last_fired(self, now):
            self.lastfired = now

        def dispatch(self):
            self.cb(self.timer,
                    self.opaque)

    def __init__(self, logger):
        threading.Thread.__init__(self, name="libvirtEventLoop-Pure")
        self.poll = select.poll()
        self.pipetrick = os.pipe()
        self.pendingWakeup = False
        self.runningPoll = False
        self.nextHandleID = 1
        self.nextTimerID = 1
        self.handles = []
        self.timers = []
        self.quit = False
        self.logger = logger
        if version_compare("libvirt-python", 3, 7, 0, logger):
            self.cleanup = []

        # The event loop can be used from multiple threads at once.
        # Specifically while the main thread is sleeping in poll()
        # waiting for events to occur, another thread may come along
        # and add/update/remove a file handle, or timer. When this
        # happens we need to interrupt the poll() sleep in the other
        # thread, so that it'll see the file handle / timer changes.
        #
        # Using OS level signals for this is very unreliable and
        # hard to implement correctly. Thus we use the real classic
        # "self pipe" trick. A anonymous pipe, with one end registered
        # with the event loop for input events. When we need to force
        # the main thread out of a poll() sleep, we simple write a
        # single byte of data to the other end of the pipe.
        self.logger.debug("Self pipe watch %d write %d" % (self.pipetrick[0],
                                                           self.pipetrick[1]))
        self.poll.register(self.pipetrick[0], select.POLLIN)

    # Calculate when the next timeout is due to occurr, returning
    # the absolute timestamp for the next timeout, or 0 if there is
    # no timeout due
    def next_timeout(self):
        next = 0
        for t in self.timers:
            last = t.get_last_fired()
            interval = t.get_interval()
            if interval < 0:
                continue
            if next == 0 or (last + interval) < next:
                next = last + interval

        return next

    # Lookup a virEventLoopPureHandle object based on file descriptor
    def get_handle_by_fd(self, fd):
        for h in self.handles:
            if h.get_fd() == fd:
                return h
        return None

    # Lookup a virEventLoopPureHandle object based on its event loop ID
    def get_handle_by_id(self, handleID):
        for h in self.handles:
            if h.get_id() == handleID:
                return h
        return None

    # This is the heart of the event loop, performing one single
    # iteration. It asks when the next timeout is due, and then
    # calcuates the maximum amount of time it is able to sleep
    # for in poll() pending file handle events.
    #
    # It then goes into the poll() sleep.
    #
    # When poll() returns, there will zero or more file handle
    # events which need to be dispatched to registered callbacks
    # It may also be time to fire some periodic timers.
    #
    # Due to the coarse granularity of schedular timeslices, if
    # we ask for a sleep of 500ms in order to satisfy a timer, we
    # may return upto 1 schedular timeslice early. So even though
    # our sleep timeout was reached, the registered timer may not
    # technically be at its expiry point. This leads to us going
    # back around the loop with a crazy 5ms sleep. So when checking
    # if timeouts are due, we allow a margin of 20ms, to avoid
    # these pointless repeated tiny sleeps.
    def run_once(self):
        sleep = -1
        self.runningPoll = True

        if version_compare("libvirt-python", 3, 7, 0, self.logger):
            for opaque in self.cleanup:
                libvirt.virEventInvokeFreeCallback(opaque)
            self.cleanup = []

        try:
            next = self.next_timeout()
            #self.logger.debug("Next timeout due at %d" % next)
            if next > 0:
                now = int(time.time() * 1000)
                if now >= next:
                    sleep = 0
                else:
                    sleep = (next - now) / 1000.0

            #self.logger.debug("Poll with a sleep of %d" % sleep)
            events = self.poll.poll(sleep)

            # Dispatch any file handle events that occurred
            for (fd, revents) in events:
                # See if the events was from the self-pipe
                # telling us to wakup. if so, then discard
                # the data just continue
                if fd == self.pipetrick[0]:
                    self.pendingWakeup = False
                    data = os.read(fd, 1)
                    continue

                h = self.get_handle_by_fd(fd)
                if h:
                    #self.logger.debug("Dispatch fd %d handle %d events %d" %
                    #                  (fd, h.get_id(), revents))
                    h.dispatch(self.events_from_poll(revents))

            now = int(time.time() * 1000)
            for t in self.timers:
                interval = t.get_interval()
                if interval < 0:
                    continue

                want = t.get_last_fired() + interval
                # Deduct 20ms, since scheduler timeslice
                # means we could be ever so slightly early
                if now >= (want - 20):
                    #self.logger.debug("Dispatch timer %d now %s want %s" %
                    #                  (t.get_id(), str(now), str(want)))
                    t.set_last_fired(now)
                    t.dispatch()

        except (os.error, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise
        finally:
            self.runningPoll = False

    # Actually the event loop forever
    def run_loop(self):
        self.quit = False
        while not self.quit:
            self.run_once()

    def interrupt(self):
        if self.runningPoll and not self.pendingWakeup:
            self.pendingWakeup = True
            os.write(self.pipetrick[1], 'c'.encode())

    # Registers a new file handle 'fd', monitoring  for 'events' (libvirt
    # event constants), firing the callback  cb() when an event occurs.
    # Returns a unique integer identier for this handle, that should be
    # used to later update/remove it
    def add_handle(self, fd, events, cb, opaque):
        handleID = self.nextHandleID + 1
        self.nextHandleID = self.nextHandleID + 1

        h = self.virEventLoopPureHandle(handleID, fd, events, cb, opaque)
        self.handles.append(h)

        self.poll.register(fd, self.events_to_poll(events))
        self.interrupt()

        #self.logger.debug("Add handle %d fd %d events %d" %
        #                  (handleID, fd, events))

        return handleID

    # Registers a new timer with periodic expiry at 'interval' ms,
    # firing cb() each time the timer expires. If 'interval' is -1,
    # then the timer is registered, but not enabled
    # Returns a unique integer identier for this handle, that should be
    # used to later update/remove it
    def add_timer(self, interval, cb, opaque):
        timerID = self.nextTimerID + 1
        self.nextTimerID = self.nextTimerID + 1

        h = self.virEventLoopPureTimer(timerID, interval, cb, opaque)
        self.timers.append(h)
        self.interrupt()

        #self.logger.debug("Add timer %d interval %d" % (timerID, interval))

        return timerID

    # Change the set of events to be monitored on the file handle
    def update_handle(self, handleID, events):
        h = self.get_handle_by_id(handleID)
        if h:
            h.set_events(events)
            self.poll.unregister(h.get_fd())
            self.poll.register(h.get_fd(), self.events_to_poll(events))
            self.interrupt()

            #self.logger.debug("Update handle %d fd %d events %d" %
            #                  (handleID, h.get_fd(), events))

    # Change the periodic frequency of the timer
    def update_timer(self, timerID, interval):
        for h in self.timers:
            if h.get_id() == timerID:
                h.set_interval(interval)
                self.interrupt()

                #self.logger.debug("Update timer %d interval %d" %
                #                  (timerID, interval))
                break

    # Stop monitoring for events on the file handle
    def remove_handle(self, handleID):
        handles = []
        for h in self.handles:
            if h.get_id() == handleID:
                self.poll.unregister(h.get_fd())
                if version_compare("libvirt-python", 3, 7, 0, self.logger):
                    self.cleanup.append(h.opaque)
                #self.logger.debug("Remove handle %d fd %d" %
                #                  (handleID, h.get_fd()))
            else:
                handles.append(h)
        self.handles = handles
        self.interrupt()

    # Stop firing the periodic timer
    def remove_timer(self, timerID):
        timers = []
        for h in self.timers:
            if version_compare("libvirt-python", 3, 7, 0, self.logger):
                if h.get_id() != timerID:
                    timers.append(h)
                else:
                    self.cleanup.append(h.opaque)
            else:
                if h.get_id() != timerID:
                    timers.append(h)
        self.timers = timers
        self.interrupt()

    # Convert from libvirt event constants, to poll() events constants
    def events_to_poll(self, events):
        ret = 0
        if events & libvirt.VIR_EVENT_HANDLE_READABLE:
            ret |= select.POLLIN
        if events & libvirt.VIR_EVENT_HANDLE_WRITABLE:
            ret |= select.POLLOUT
        if events & libvirt.VIR_EVENT_HANDLE_ERROR:
            ret |= select.POLLERR
        if events & libvirt.VIR_EVENT_HANDLE_HANGUP:
            ret |= select.POLLHUP
        return ret

    # Convert from poll() event constants, to libvirt events constants
    def events_from_poll(self, events):
        ret = 0
        if events & select.POLLIN:
            ret |= libvirt.VIR_EVENT_HANDLE_READABLE
        if events & select.POLLOUT:
            ret |= libvirt.VIR_EVENT_HANDLE_WRITABLE
        if events & select.POLLNVAL:
            ret |= libvirt.VIR_EVENT_HANDLE_ERROR
        if events & select.POLLERR:
            ret |= libvirt.VIR_EVENT_HANDLE_ERROR
        if events & select.POLLHUP:
            ret |= libvirt.VIR_EVENT_HANDLE_HANGUP
        return ret

    def regist(self, libvirt):
        # Now glue an instance of the general event loop into libvirt's event loop
        # These next set of 6 methods are the glue between the official
        # libvirt events API, and our particular impl of the event loop
        #
        # There is no reason why the 'virEventLoopPure' has to be used.
        # An application could easily may these 6 glue methods hook into
        # another event loop such as GLib's, or something like the python
        # Twisted event framework.

        def virEventAddHandleImpl(fd, events, cb, opaque):
            return self.add_handle(fd, events, cb, opaque)

        def virEventUpdateHandleImpl(handleID, events):
            return self.update_handle(handleID, events)

        def virEventRemoveHandleImpl(handleID):
            return self.remove_handle(handleID)

        def virEventAddTimerImpl(interval, cb, opaque):
            return self.add_timer(interval, cb, opaque)

        def virEventUpdateTimerImpl(timerID, interval):
            return self.update_timer(timerID, interval)

        def virEventRemoveTimerImpl(timerID):
            return self.remove_timer(timerID)

        # This tells libvirt what event loop implementation it
        # should use
        libvirt.virEventRegisterImpl(virEventAddHandleImpl,
                                     virEventUpdateHandleImpl,
                                     virEventRemoveHandleImpl,
                                     virEventAddTimerImpl,
                                     virEventUpdateTimerImpl,
                                     virEventRemoveTimerImpl)

    def unregist(self, libvirt):
        # Not used yet
        pass

    def start(self):
        self.setDaemon(True)
        threading.Thread.start(self)

    def run(self):
        self.run_loop()

    def stop(self):
        self.quit = True
        self.interrupt()


def eventLoopPure(logger):
    eventLoop = virEventLoopPureThread(logger)
    eventLoop.regist(libvirt)
    eventLoop.start()

    return 0
