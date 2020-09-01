#!/usr/bin/env python
# coding: utf-8

import logging
import os
import time

from .input_event import EventLog, InputEvent, ExitEvent
from .input_policy import UtgGreedySearchPolicy, UtgReplayPolicy
from p3detector.prediction_model import PredictionModel

if 'DEFAULT_EVENT_INTERVAL' in os.environ:
    DEFAULT_EVENT_INTERVAL = os.environ['DEFAULT_EVENT_INTERVAL']
else:
    DEFAULT_EVENT_INTERVAL = 2


class InputManager(object):
    """
    The class managing all events sent during the application stimulation.
    """

    def __init__(self, device, app, replay: bool = False, max_actions: int = 30, timeout_privacy: int = 60,
                 pdetector: PredictionModel = None, md5_app=None):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device
        self.app = app
        self.replay = replay
        self.max_actions = max_actions
        self.timeout_privacy = timeout_privacy
        self.enabled = True

        self.events = []
        self.event_interval = DEFAULT_EVENT_INTERVAL
        self.exit_event_received = False
        self.pdetector = pdetector
        self.md5_app = md5_app

        if self.replay:
            self.policy = UtgReplayPolicy(self.device, self.app, self.max_actions, self.timeout_privacy,
                                          self.pdetector, self.md5_app, self.device.output_dir)
        else:
            self.policy = UtgGreedySearchPolicy(self.device, self.app, self.max_actions, self.timeout_privacy,
                                                self.pdetector, self.md5_app)

    def add_event(self, event: InputEvent):
        """
        Add one event to the event list.

        :param event: The event to be added, should be an instance of a subclass of InputEvent.
        """
        if not event:
            return

        if isinstance(event, ExitEvent):
            self.exit_event_received = True

        self.events.append(event)

        event_log = EventLog(self.device, self.app, event)
        event_log.start()  # send event
        time.sleep(self.event_interval)  # sleep between two event
        event_log.stop(is_replaying=self.replay)

    def start(self):
        """
        Start sending events.
        """
        self.logger.info('Start sending events')

        self.policy.start(self)

        self.stop()
        self.logger.info('Finished sending events')

    def stop(self):
        """
        Stop sending events.
        """
        self.enabled = False
