#!/usr/bin/env python
# coding: utf-8

import logging
import os
import re
import shutil
import socket
from collections import OrderedDict
from datetime import datetime
from typing import Optional, List

from . import util
from .adapter.adb import ADB
from .adapter.droidbot_app import DroidBotApp
from .adapter.droidbot_ime import DroidBotIme
from .adapter.droidbot_web_socket import DroidBotWebSocket
from .adapter.user_input_monitor import UserInputMonitor
from .app import App
from .device_state import DeviceState
from .intent import Intent
from .smart_input import SmartInput


class Device(object):
    """
    The class representing the device on which the application is running.
    """

    def __init__(self, app, output_dir: str = None, device_serial: str = None,
                 replay: bool = False, smart_input: bool = False):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        # Find a connected device.
        all_devices = util.get_available_devices()
        if len(all_devices) == 0:
            raise RuntimeError('No Android device connected, unable to continue')
        if device_serial and any(device_serial in device for device in all_devices):
            self.serial = device_serial
        else:
            self.serial = all_devices[0]

        # If an output directory was specified, make sure it exists.
        if output_dir and not os.path.isdir(output_dir) and not replay:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self.logger.error('Unable to create output directory "{0}": {1}'.format(output_dir, e))
                raise

        self.app = app

        # Smart input generator.
        self.smart_input_generator = None
        if smart_input and not replay:
            try:
                self.smart_input_generator = SmartInput(self.app.apk_path)
            except Exception:
                self.logger.warning('Smart input generation unavailable')

        self.output_dir = output_dir
        self.replay = replay

        # Basic device information.
        self.connected = True
        self.settings = {}
        self.sdk_version = None
        self.display_info = None
        self.last_know_state = None
        self.used_ports = []

        # Adapters.
        self.droidbot_ime = DroidBotIme(device=self)
        self.droidbot_app = DroidBotApp(device=self)
        self.user_input_monitor = UserInputMonitor(device=self)
        self.adb = ADB(device=self)
        self.droidbot_web_socket = DroidBotWebSocket(device=self)

        self.adapters = OrderedDict([
            (self.droidbot_ime, True),
            (self.droidbot_app, True),
            (self.user_input_monitor, not self.replay),
            (self.adb, True),
            (self.droidbot_web_socket, True)
        ])

    def connect(self):
        """
        Establish connections on this device.
        """
        for adapter in self.adapters:
            adapter_enabled = self.adapters[adapter]
            if not adapter_enabled:
                continue
            adapter.connect()

        self.check_connectivity()
        self.connected = True

    def disconnect(self):
        """
        Disconnect current device.
        """
        self.connected = False
        for adapter in self.adapters:
            adapter_enabled = self.adapters[adapter]
            if not adapter_enabled:
                continue
            adapter.disconnect()

        if self.output_dir:
            temp_dir = os.path.join(self.output_dir, 'temp')
            if os.path.isdir(temp_dir):
                shutil.rmtree(temp_dir)

    def check_connectivity(self):
        """
        Log the status of the adapters connected to the device.
        """
        for adapter in self.adapters:
            adapter_name = adapter.__class__.__name__
            adapter_enabled = self.adapters[adapter]
            if not adapter_enabled:
                self.logger.info('{0} is not enabled'.format(adapter_name))
            else:
                if adapter.check_connectivity():
                    self.logger.info('{0} is enabled and connected'.format(adapter_name))
                else:
                    self.logger.info('{0} is enabled but not connected'.format(adapter_name))

    def set_up(self):
        """
        Set up connections on this device.
        """
        self.wait_for_device()
        for adapter in self.adapters:
            adapter_enabled = self.adapters[adapter]
            if not adapter_enabled:
                continue
            adapter.set_up()

    def tear_down(self):
        for adapter in self.adapters:
            adapter_enabled = self.adapters[adapter]
            if not adapter_enabled:
                continue
            adapter.tear_down()

    def wait_for_device(self):
        """
        Wait until the device is ready to be used through adb.
        """
        self.logger.info('Waiting for device')
        try:
            self.adb.run_cmd(['wait-for-device'])
        except Exception as e:
            self.logger.error('Error while waiting for device: {0}'.format(e))
            raise

    def get_top_activity_name(self):
        """
        The the current displayed activity.
        """
        r = self.adb.shell(['dumpsys', 'activity', 'activities'])
        activity_line_re = re.compile(r'\* Hist #\d+: ActivityRecord{\S+ \S+ (\S+) t\d+}')
        m = activity_line_re.search(r)
        if m:
            return m.group(1)
        self.logger.warning('Unable to get top activity name')
        return None

    def is_foreground(self, app):
        """
        Check if the app is currently in foreground.

        :param app: Package name of the app (as string) or an App object.
        :return: True if the app is in foreground, false otherwise.
        """

        # Get application's package name.
        if isinstance(app, str):
            package_name = app
        elif isinstance(app, App):
            package_name = app.get_package_name()
        else:
            return False

        top_activity_name = self.get_top_activity_name()
        if not top_activity_name:
            return False
        return top_activity_name.startswith(package_name)

    def get_sdk_version(self):
        """
        Get version of the device's SDK.
        """
        if not self.sdk_version:
            self.sdk_version = self.adb.get_sdk_version()
        return self.sdk_version

    def get_display_info(self, refresh=True) -> dict:
        """
        Get device display information, including width, height and density.

        :param refresh: If set to True, refresh the display info instead of using the old values.
        """
        if not self.display_info or refresh:
            self.display_info = self.adb.get_display_info()
        return self.display_info

    def get_width(self, refresh=False):
        display_info = self.get_display_info(refresh=refresh)
        width = 0
        if 'width' in display_info:
            width = display_info['width']
        elif not refresh:
            width = self.get_width(refresh=True)
        else:
            self.logger.warning('Width not found in display info')
        return width

    def get_height(self, refresh=False):
        display_info = self.get_display_info(refresh=refresh)
        height = 0
        if 'height' in display_info:
            height = display_info['height']
        elif not refresh:
            height = self.get_width(refresh=True)
        else:
            self.logger.warning('Height not found in display info')
        return height

    def send_intent(self, intent):
        """
        Send an intent to device through am (ActivityManager).

        :param intent: The intent (as list of strings) or an Intent object.
        """
        if not self.adb:
            raise RuntimeError('Adb not connected, unable to send intent')
        if not intent:
            raise TypeError('Unable to send an empty intent')
        if isinstance(intent, Intent):
            cmd = intent.get_cmd()
        else:
            cmd = intent

        intent_result = self.adb.shell(cmd)

        # If this is a start intent, check if it was successful, otherwise remove it from
        # the list of start intents (some intents might try to use disabled main activities
        # that are not detected as disabled during the static analysis of the manifest).
        for start_intent in self.app.start_intents:
            if cmd == start_intent.get_cmd() and \
                    'error: activity class' in intent_result.lower() and 'does not exist' in intent_result.lower():
                self.logger.warning('{0} is not a valid start intent and will not be used anymore'.format(intent))
                self.app.start_intents.remove(start_intent)
                break

        return intent_result

    def send_event(self, event):
        """
        Send one event (InputEvent) to device.

        :param event: The InputEvent to be sent.
        """
        event.send(self)

    def get_task_activities(self) -> dict:
        """
        Get current tasks and corresponding activities.

        :return: A dictionary mapping each task id to a list of activities, from top to down.
        """
        task_to_activities = {}

        lines = self.adb.shell(['dumpsys', 'activity', 'activities']).splitlines()
        activity_line_re = re.compile(r'\* Hist #\d+: ActivityRecord{\S+ \S+ (\S+) t(\d+)}')

        for line in lines:
            line = line.strip()
            if line.startswith('Task id #'):
                task_id = line[9:]
                task_to_activities[task_id] = []
            elif line.startswith('* Hist #'):
                m = activity_line_re.match(line)
                if m:
                    activity = m.group(1)
                    task_id = m.group(2)
                    if task_id not in task_to_activities:
                        task_to_activities[task_id] = []
                    task_to_activities[task_id].append(activity)

        return task_to_activities

    def get_current_activity_stack(self) -> Optional[List[str]]:
        """
        Get current activity stack.

        :return: A list of strings, each string is an activity name (the first is the top activity).
        """
        task_to_activities = self.get_task_activities()
        top_activity = self.get_top_activity_name()
        if top_activity:
            for task_id in task_to_activities:
                activities = task_to_activities[task_id]
                if len(activities) > 0 and activities[0] == top_activity:
                    return activities
            self.logger.warning('Unable to get current activity stack')
            return [top_activity]
        else:
            return None

    def get_service_names(self) -> List[str]:
        """
        Get current running services.

        :return: List of running services.
        """
        services = []
        dat = self.adb.shell(['dumpsys', 'activity', 'services'])
        lines = dat.splitlines()
        service_re = re.compile('^.+ServiceRecord{.+ ([A-Za-z0-9_.]+)/([A-Za-z0-9_.]+)}')

        for line in lines:
            m = service_re.search(line)
            if m:
                package = m.group(1)
                service = m.group(2)
                services.append('{0}/{1}'.format(package, service))
        return services

    def install_app(self, app):
        """
        Install an app to device.

        :param app: App instance to install.
        """
        if not isinstance(app, App):
            raise TypeError('The app to install has to be an instance of App object')
        if not self.adb:
            raise RuntimeError('Adb not connected, unable to install app')

        package_name = app.get_package_name()
        install_cmd = ['install', '-r']
        if self.get_sdk_version() >= 23:
            install_cmd.append('-g')
        install_cmd.append(app.apk_path)

        self.logger.info('Installing application into device')
        install_output = self.adb.run_cmd(install_cmd)

        try:
            install_result = install_output.splitlines()[-1]
        except Exception:
            install_result = None

        if not install_result or install_result.lower().strip() != 'success':
            raise RuntimeError('Unable to install app: {0}'.format(install_result))

        dumpsys_lines = []
        dumpsys_result = self.adb.shell(['dumpsys', 'package', package_name])
        if dumpsys_result:
            dumpsys_lines = dumpsys_result.splitlines()

        if self.output_dir and not self.replay:
            package_info_file_name = os.path.join(
                self.output_dir, 'dumpsys_package_{0}.txt'.format(app.get_package_name()))
            with open(package_info_file_name, 'w') as package_info_file:
                package_info_file.writelines(dumpsys_lines)

        self.logger.info('Application installed: {0}'.format(package_name))
        self.logger.info('Main activities: {0}'.format(app.get_main_activities()))

    def uninstall_app(self, app):
        """
        Uninstall an app from device.

        :param app: Package name of the app (as string) or an App object.
        """
        if not self.adb:
            raise RuntimeError('Adb not connected, unable to uninstall app')
        if isinstance(app, App):
            package_name = app.get_package_name()
        else:
            package_name = app

        if package_name in self.adb.get_installed_apps():
            self.logger.info('Uninstalling application from device')
            self.adb.run_cmd(['uninstall', package_name])

    def get_app_pid(self, app) -> Optional[int]:
        """
        Get application's pid (process id).

        :param app: Package name of the app (as string) or an App object.
        :return: Application's pid.
        """
        if isinstance(app, App):
            package = app.get_package_name()
        else:
            package = app

        name2pid = {}
        ps_out = self.adb.shell(['ps'])
        ps_out_lines = ps_out.splitlines()
        ps_out_head = ps_out_lines[0].split()
        if ps_out_head[1] != 'PID' or ps_out_head[-1] != 'NAME':
            self.logger.warning('Output format error from ps command: {0}'.format(ps_out_head))
        for ps_out_line in ps_out_lines[1:]:
            segs = ps_out_line.split()
            if len(segs) < 4:
                continue
            pid = int(segs[1])
            name = segs[-1]
            name2pid[name] = pid

        if package in name2pid:
            return name2pid[package]

        possible_pids = []
        for name in name2pid:
            if name.startswith(package):
                possible_pids.append(name2pid[name])
        if len(possible_pids) > 0:
            return min(possible_pids)

        return None

    def pull_file(self, remote_file, local_file):
        """
        Extract a file from the device.

        :param remote_file: The path to the file on the device.
        :param local_file: The destination path of the file on the host machine.
        """
        self.adb.run_cmd(['pull', remote_file, local_file])

    def take_screenshot(self):
        if not self.output_dir or self.replay:
            return None

        tag = datetime.now().strftime('%d-%m-%Y_%H%M%S')
        local_image_dir = os.path.join(self.output_dir, 'temp')
        if not os.path.isdir(local_image_dir):
            os.makedirs(local_image_dir)

        local_image_path = os.path.join(local_image_dir, 'screen_{0}.png'.format(tag))
        remote_image_path = '/sdcard/screen_{0}.png'.format(tag)
        self.adb.shell(['screencap', '-p', remote_image_path])
        self.pull_file(remote_image_path, local_image_path)
        self.adb.shell(['rm', remote_image_path])

        return local_image_path

    def get_views(self):
        if self.droidbot_app and self.adapters[self.droidbot_app]:
            views = self.droidbot_app.get_views()
            if views:
                return views
            else:
                self.logger.warning('Failed to get views using Accessibility')

        self.logger.warning('Failed to get current views')
        return None

    def get_current_state(self):
        self.logger.debug('Getting current device state')
        views = self.get_views()
        foreground_activity = self.get_top_activity_name()
        activity_stack = self.get_current_activity_stack()
        background_services = self.get_service_names()
        screenshot_path = self.take_screenshot()
        current_state = DeviceState(self, views=views, foreground_activity=foreground_activity,
                                    activity_stack=activity_stack, background_services=background_services,
                                    screenshot_path=screenshot_path)
        self.logger.debug('Finished getting current device state')
        self.last_know_state = current_state
        if not current_state:
            self.logger.warning('Failed to get current state')
        return current_state

    def get_last_known_state(self):
        return self.last_know_state

    def get_host_random_port(self) -> int:
        """
        Get a random port on the host machine to establish a connection.

        :return: A port number.
        """
        temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        temp_sock.bind(('', 0))

        port = temp_sock.getsockname()[1]
        temp_sock.close()

        if port in self.used_ports:
            return self.get_host_random_port()

        self.used_ports.append(port)

        return port

    def view_long_touch(self, x, y, duration=2000):
        """
        Simulate a long touch at (x, y).

        :param x: X screen coordinate.
        :param y: Y screen coordinate.
        :param duration: The duration (ms) of the touch operation.
        """
        self.adb.long_touch(x, y, duration)

    def view_drag(self, start_xy, end_xy, duration):
        """
        Send a drag event.

        :param start_xy: Starting point in pixel coordinates, passed as tuple (x, y).
        :param end_xy: Ending point in pixel coordinates, passed as tuple (x, y).
        :param duration: Duration of the drag event.
        """
        self.adb.drag(start_xy, end_xy, duration)

    def view_set_text(self, text):
        if self.droidbot_ime.connected:
            self.droidbot_ime.input_text(text=text, mode=0)

    def key_press(self, key_code):
        self.adb.press(key_code)
