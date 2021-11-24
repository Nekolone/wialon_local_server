import time
from threading import Thread


def selfloop(f):
    def decorator(self):
        while self.loop:
            f(self)
            time.sleep(self.sleep_time)

    return decorator


class Event:
    def __init__(self, function, args=None, predicate=lambda: False, single_use=False, threadable=False, cooldown=0):
        if args is None:
            args = []
        self.predicate = predicate
        self.function = function
        self.args = args
        self.single_use = single_use
        self.threadable = threadable
        self.started_on_thread = False
        self.cooldown = cooldown
        self.cooldown_deadline = time.time() + cooldown
        self.event_group = []


class EventGroup:
    def __init__(self, predicate=lambda: True, cooldown=0):
        self.events = []
        self.predicate = predicate
        self.cooldown = cooldown
        self.cooldown_deadline = time.time() + cooldown

    def add_event(self, event):
        event.event_group = self
        self.events.append(event)


class Eventloop:

    def __init__(self, sleep_time=0.05):
        self.ts = Thread(target=self._check_event_groups)
        self.ct = Thread(target=self._check_thread_status, args=())
        self.loop = True
        self.general_group = EventGroup()
        self.event_groups = [self.general_group]
        self.sleep_time = sleep_time
        self.threads = []

    @selfloop
    def _check_event_groups(self):
        for eg in self.event_groups:
            if not eg.predicate() or eg.cooldown_deadline >= time.time():
                continue
            self._dispatch_event_group(eg)

    def _dispatch_event_group(self, event_group):
        dispatched_events = [self._dispatch_event(e) for e in event_group.events if
                             not e.started_on_thread and e.predicate() and e.cooldown_deadline <= time.time()]
        if len(dispatched_events) != 0:
            self._update_cooldown(event_group)

    def _dispatch_event(self, event):
        self._update_cooldown(event)
        if not event.threadable:
            self._start_function(event)
            return
        self._start_function_on_thread(event)

    def _update_cooldown(self, item):
        item.cooldown_deadline = time.time() + item.cooldown

    @selfloop
    def _check_thread_status(self):
        if len(self.threads) > 100:
            self.stop()
            raise Exception("logical error, to much threads >100")
        for t in [t for t in self.threads]:
            if not t.is_alive():
                t.event.started_on_thread = False
                self.threads.remove(t)

    def _start_function(self, event):
        event.function(*event.args)
        if not event.single_use:
            return
        event.event_group.events.remove(event)

    def _start_function_on_thread(self, event):
        t = Thread(target=event.function, args=event.args)
        t.start()
        if event.single_use:
            event.event_group.events.remove(event)
            return
        t.event = event
        self.threads.append(t)
        event.started_on_thread = True

    def add_event(self, event):
        self.general_group.add_event(event)

    def add_event_group(self, event_group):
        self.event_groups.append(event_group)

    def start(self):
        self.ct.start()
        self.ts.start()

    def join(self):
        self.ts.join()
        self.ct.join()

    def stop(self):
        self.loop = False
