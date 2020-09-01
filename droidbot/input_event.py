#!/usr/bin/env python
# coding: utf-8

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

from .intent import Intent

POSSIBLE_KEYS = [
    'BACK',
    'HOME',
    'MENU'
]

KEY_KeyEvent = 'key'
KEY_TouchEvent = 'touch'
KEY_LongTouchEvent = 'long_touch'
KEY_SwipeEvent = 'swipe'
KEY_ScrollEvent = 'scroll'
KEY_SetTextEvent = 'set_text'
KEY_IntentEvent = 'intent'
KEY_ExitEvent = 'exit'
KEY_NopEvent = 'nop'


class EventLog(object):
    """
    Save an event to local file system.
    """

    def __init__(self, device, app, event, tag=None):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device
        self.app = app

        self.event = event
        if not tag:
            tag = datetime.now().strftime('%d-%m-%Y_%H%M%S')
        self.tag = tag

        self.from_state = None
        self.to_state = None
        self.event_str = None

    def to_dict(self):
        return {
            'tag': self.tag,
            'event': self.event.to_dict(),
            'start_state': self.from_state.state_str,
            'stop_state': self.to_state.state_str,
            'event_str': self.event_str
        }

    def save2dir(self):
        # Save event.
        if not self.device.output_dir:
            return
        else:
            output_dir = os.path.join(self.device.output_dir, 'events')

        try:
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
            event_json_file_path = os.path.join(output_dir, 'event_{0}.json'.format(self.tag))
            with open(event_json_file_path, 'w') as event_json_file:
                json.dump(self.to_dict(), event_json_file, indent=2)
        except Exception as e:
            self.logger.warning('Unable to save event to directory: {0}'.format(e))

    def save_views(self):
        # Save views.
        views = self.event.get_views()
        if views:
            for view_dict in views:
                self.from_state.save_view_img(view_dict=view_dict)

    def start(self):
        """
        Start sending event.
        """
        self.from_state = self.device.get_current_state()
        self.event_str = self.event.get_event_str(self.from_state)
        self.logger.info('Input: {0}'.format(self.event_str))
        # self.logger.info("EVENT {}".format(self.event))
        self.device.send_event(self.event)  # send event

    def stop(self, is_replaying: bool = False):
        """
        Finish sending event.
        """
        self.to_state = self.device.get_current_state()
        if not is_replaying:
            self.save2dir()
            self.save_views()


class InputEvent(ABC):
    """
    The base class of all events.
    """

    def to_dict(self):
        return self.__dict__

    def to_json(self):
        return json.dumps(self.to_dict())

    def __str__(self):
        return self.to_dict().__str__()

    @abstractmethod
    def send(self, device):
        """
        Send this event to the device.

        :param device: Instance of Device where to send the event.
        """
        raise NotImplementedError()

    @staticmethod
    def from_dict(event_dict: dict):
        if not isinstance(event_dict, dict):
            return None
        if 'event_type' not in event_dict:
            return None
        event_type = event_dict['event_type']
        if event_type == KEY_KeyEvent:
            return KeyEvent(event_dict=event_dict)
        elif event_type == KEY_TouchEvent:
            return TouchEvent(event_dict=event_dict)
        elif event_type == KEY_LongTouchEvent:
            return LongTouchEvent(event_dict=event_dict)
        elif event_type == KEY_SwipeEvent:
            return SwipeEvent(event_dict=event_dict)
        elif event_type == KEY_ScrollEvent:
            return ScrollEvent(event_dict=event_dict)
        elif event_type == KEY_SetTextEvent:
            return SetTextEvent(event_dict=event_dict)
        elif event_type == KEY_IntentEvent:
            return IntentEvent(event_dict=event_dict)
        elif event_type == KEY_ExitEvent:
            return ExitEvent()
        elif event_type == KEY_NopEvent:
            return NopEvent()

    @abstractmethod
    def get_event_str(self, state):
        raise NotImplementedError()

    def get_views(self):
        return []


class KeyEvent(InputEvent):
    """
    A key pressing event.
    """

    def __init__(self, name=None, event_dict=None):
        self.event_type = KEY_KeyEvent
        self.name = name

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        device.key_press(self.name)

    def get_event_str(self, state):
        return '{0}(state={1}, name={2})'.format(self.__class__.__name__, state.state_str, self.name)


class UIEvent(InputEvent):
    """
    This class describes an UI event for an app, such as touch, scroll etc.
    """

    @abstractmethod
    def send(self, device):
        raise NotImplementedError()

    @abstractmethod
    def get_event_str(self, state):
        raise NotImplementedError()

    @staticmethod
    def get_xy(x, y, view):
        if x and y:
            return x, y
        if view:
            # Import is here and not at the top of the file to avoid circular dependency.
            from .device_state import DeviceState
            return DeviceState.get_view_center(view_dict=view)
        return x, y


class TouchEvent(UIEvent):
    """
    A touch on screen event.
    """

    def __init__(self, x=None, y=None, view=None, event_dict=None):
        self.event_type = KEY_TouchEvent
        self.x = x
        self.y = y
        self.view = view

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        x, y = UIEvent.get_xy(x=self.x, y=self.y, view=self.view)
        device.view_long_touch(x=x, y=y, duration=200)

    def get_event_str(self, state):
        if self.view:
            return '{0}(state={1}, view={2})'.format(self.__class__.__name__, state.state_str, self.view['view_str'])
        elif self.x and self.y:
            return '{0}(state={1}, x={2}, y={3})'.format(self.__class__.__name__, state.state_str, self.x, self.y)
        else:
            raise TypeError('Invalid {0}'.format(self.__class__.__name__))

    def get_views(self):
        return [self.view] if self.view else []


class LongTouchEvent(UIEvent):
    """
    A long touch on screen event.
    """

    def __init__(self, x=None, y=None, view=None, duration=2000, event_dict=None):
        self.event_type = KEY_LongTouchEvent
        self.x = x
        self.y = y
        self.view = view
        self.duration = duration

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        x, y = UIEvent.get_xy(x=self.x, y=self.y, view=self.view)
        device.view_long_touch(x=x, y=y, duration=self.duration)

    def get_event_str(self, state):
        if self.view:
            return '{0}(state={1}, view={2}, duration={3})'.format(
                self.__class__.__name__, state.state_str, self.view['view_str'], self.duration)
        elif self.x and self.y:
            return '{0}(state={1}, x={2}, y={3}, duration={4})'.format(
                self.__class__.__name__, state.state_str, self.x, self.y, self.duration)
        else:
            raise TypeError('Invalid {0}'.format(self.__class__.__name__))

    def get_views(self):
        return [self.view] if self.view else []


class SwipeEvent(UIEvent):
    """
    A drag gesture on screen event.
    """

    def __init__(self,
                 start_x=None, start_y=None, start_view=None,
                 end_x=None, end_y=None, end_view=None,
                 duration=1000, event_dict=None):
        self.event_type = KEY_SwipeEvent

        self.start_x = start_x
        self.start_y = start_y
        self.start_view = start_view

        self.end_x = end_x
        self.end_y = end_y
        self.end_view = end_view

        self.duration = duration

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        start_x, start_y = UIEvent.get_xy(x=self.start_x, y=self.start_y, view=self.start_view)
        end_x, end_y = UIEvent.get_xy(x=self.end_x, y=self.end_y, view=self.end_view)
        device.view_drag((start_x, start_y), (end_x, end_y), self.duration)

    def get_event_str(self, state):
        if self.start_view:
            start_view_str = 'state={0}, start_view={1}'.format(state.state_str, self.start_view['view_str'])
        elif self.start_x and self.start_y:
            start_view_str = 'state={0}, start_x={1}, start_y={2}'.format(state.state_str, self.start_x, self.start_y)
        else:
            raise TypeError('Invalid {0}'.format(self.__class__.__name__))

        if self.end_view:
            end_view_str = 'end_view={0}'.format(self.end_view['view_str'])
        elif self.end_x and self.end_y:
            end_view_str = 'end_x={0}, end_y={1}'.format(self.end_x, self.end_y)
        else:
            raise TypeError('Invalid {0}'.format(self.__class__.__name__))

        return '{0}({1}, {2}, duration={3})'.format(
            self.__class__.__name__, start_view_str, end_view_str, self.duration)

    def get_views(self):
        views = []
        if self.start_view:
            views.append(self.start_view)
        if self.end_view:
            views.append(self.end_view)
        return views


class ScrollEvent(UIEvent):
    """
    A swipe gesture (scroll) event.
    """

    def __init__(self, x=None, y=None, view=None, direction='DOWN', event_dict=None):
        self.event_type = KEY_ScrollEvent
        self.x = x
        self.y = y
        self.view = view
        self.direction = direction

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        if self.view:
            from .device_state import DeviceState
            width = DeviceState.get_view_width(view_dict=self.view)
            height = DeviceState.get_view_height(view_dict=self.view)
        else:
            width = device.get_width()
            height = device.get_height()

        x, y = UIEvent.get_xy(x=self.x, y=self.y, view=self.view)
        if not x or not y:
            # If no views and no coordinates are specified, use the screen center coordinate.
            x = width / 2
            y = height / 2

        start_x, start_y = x, y
        end_x, end_y = x, y
        duration = 500

        if self.direction == 'UP':
            start_y -= height * 2 / 5
            end_y += height * 2 / 5
        elif self.direction == 'DOWN':
            start_y += height * 2 / 5
            end_y -= height * 2 / 5
        elif self.direction == 'LEFT':
            start_x -= width * 2 / 5
            end_x += width * 2 / 5
        elif self.direction == 'RIGHT':
            start_x += width * 2 / 5
            end_x -= width * 2 / 5

        device.view_drag((start_x, start_y), (end_x, end_y), duration)

    def get_event_str(self, state):
        if self.view:
            return '{0}(state={1}, view={2}, direction={3})'.format(
                self.__class__.__name__, state.state_str, self.view['view_str'], self.direction)
        elif self.x and self.y:
            return '{0}(state={1}, x={2}, y={3}, direction={4})'.format(
                self.__class__.__name__, state.state_str, self.x, self.y, self.direction)
        else:
            return '{0}(state={1}, direction={2})'.format(self.__class__.__name__, state.state_str, self.direction)

    def get_views(self):
        return [self.view] if self.view else []


class SetTextEvent(UIEvent):
    """
    Set text in target UI event.
    """

    def __init__(self, x=None, y=None, view=None, text=None, event_dict=None):
        self.event_type = KEY_SetTextEvent
        self.x = x
        self.y = y
        self.view = view
        self.text = text

        if event_dict:
            self.__dict__.update(event_dict)

    def send(self, device):
        x, y = UIEvent.get_xy(x=self.x, y=self.y, view=self.view)
        touch_event = TouchEvent(x=x, y=y)
        touch_event.send(device)
        device.view_set_text(self.text)

    def get_event_str(self, state):
        if self.view:
            return '{0}(state={1}, view={2}, text={3})'.format(
                self.__class__.__name__, state.state_str, self.view['view_str'], self.text)
        elif self.x and self.y:
            return '{0}(state={1}, x={2}, y={3}, text={4})'.format(
                self.__class__.__name__, state.state_str, self.x, self.y, self.text)
        else:
            raise TypeError('Invalid {0}()'.format(self.__class__.__name__))

    def get_views(self):
        return [self.view] if self.view else []


class IntentEvent(InputEvent):
    """
    An event describing an intent.
    """

    def __init__(self, intent=None, event_dict=None):
        self.event_type = KEY_IntentEvent

        if not intent and not event_dict:
            raise ValueError('Either intent of event_dict must be provided')

        if event_dict:
            self.__dict__.update(event_dict)
        elif isinstance(intent, Intent):
            self.intent = intent.get_cmd()
        elif isinstance(intent, list):
            self.intent = intent
        else:
            raise TypeError('Intent must either be an instance of Intent or a list of strings')

    def send(self, device):
        device.send_intent(intent=self.intent)

    def get_event_str(self, state):
        return '{0}(intent={1})'.format(self.__class__.__name__, self.intent)


class ExitEvent(InputEvent):
    """
    An event to stop stimulating the application.
    """

    def __init__(self):
        self.event_type = KEY_ExitEvent

    def send(self, device):
        raise KeyboardInterrupt()

    def get_event_str(self, state):
        return '{0}()'.format(self.__class__.__name__)


class NopEvent(InputEvent):
    """
    This event does nothing (can be used as an event placeholder).
    """

    def __init__(self):
        self.event_type = KEY_NopEvent

    def send(self, device):
        pass

    def get_event_str(self, state):
        return '{0}()'.format(self.__class__.__name__)
