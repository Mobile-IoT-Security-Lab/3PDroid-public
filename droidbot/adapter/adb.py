#!/usr/bin/env python
# coding: utf-8

import logging
import re
import subprocess
from typing import List

from .adapter import Adapter


class ADB(Adapter):
    """
    Interface for sending commands through adb: https://developer.android.com/studio/command-line/adb.
    """

    VERSION_SDK_PROPERTY = 'ro.build.version.sdk'

    def __init__(self, device):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device

        self.cmd_prefix = ['adb', '-s', device.serial]

    def connect(self):
        """
        Connect adb.
        """
        self.logger.info('{0} connected'.format(self.__class__.__name__))

    def disconnect(self):
        """
        Disconnect adb.
        """
        self.logger.info('{0} disconnected'.format(self.__class__.__name__))

    def check_connectivity(self):
        """
        Check if adb is connected.

        :return: True if adb is connected, false otherwise.
        """
        output = self.run_cmd(['get-state'])
        return output.startswith('device')

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def run_cmd(self, cmd_as_list: List[str]) -> str:
        """
        Run adb command and return the output as a string.

        :param cmd_as_list: The command to execute formatted as a list of strings.
        :return: The output of the command.
        """
        if not isinstance(cmd_as_list, list):
            raise TypeError('The commands should be passed as a list of strings')

        complete_cmd = self.cmd_prefix + cmd_as_list
        self.logger.debug('Running command "{0}"'.format(complete_cmd))
        output = subprocess.check_output(complete_cmd, stderr=subprocess.STDOUT).strip().decode()
        self.logger.debug('Command "{0}" returned: {1}'.format(complete_cmd, output))

        return output

    def shell(self, cmd_as_list: List[str]) -> str:
        """
        Run adb shell command and return the output as a string.

        :param cmd_as_list: The command to execute formatted as a list of strings.
        :return: The output of the command.
        """
        if not isinstance(cmd_as_list, list):
            raise TypeError('The commands should be passed as a list of strings')

        shell_cmd = ['shell'] + cmd_as_list

        return self.run_cmd(shell_cmd)

    def get_property(self, property_name) -> str:
        """
        Get the value of a property.

        :param property_name: The name of the property.
        :return: The value of the property.
        """
        return self.shell(['getprop', property_name])

    def get_sdk_version(self) -> int:
        """
        Get the version of the SDK installed on the device (e.g., 23 for Android Marshmallow).

        :return: An int with the version number.
        """
        return int(self.get_property(ADB.VERSION_SDK_PROPERTY))

    # The following methods are taken from AndroidViewClient project.
    # https://github.com/dtmilano/AndroidViewClient.
    def get_display_info(self) -> dict:
        """
        This is a method to obtain display dimensions and density.
        """
        display_info = {}
        logical_display_re = re.compile(r'.*DisplayViewport{valid=true, .*orientation=(?P<orientation>\d+),'
                                        r' .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*')
        dumpsys_display_result = self.shell(['dumpsys', 'display'])
        if dumpsys_display_result:
            for line in dumpsys_display_result.splitlines():
                m = logical_display_re.search(line, 0)
                if m:
                    for prop in ['width', 'height', 'orientation']:
                        display_info[prop] = int(m.group(prop))

        if 'width' not in display_info or 'height' not in display_info:
            physical_display_re = re.compile(r'Physical size: (?P<width>\d+)x(?P<height>\d+)')
            m = physical_display_re.search(self.shell(['wm', 'size']))
            if m:
                for prop in ['width', 'height']:
                    display_info[prop] = int(m.group(prop))

        if 'width' not in display_info or 'height' not in display_info:
            display_re = re.compile(r'\s*mUnrestrictedScreen=\((?P<x>\d+),(?P<y>\d+)\) (?P<width>\d+)x(?P<height>\d+)')
            display_width_height_re = re.compile(r'\s*DisplayWidth=(?P<width>\d+) *DisplayHeight=(?P<height>\d+)')
            for line in self.shell(['dumpsys', 'window']).splitlines():
                m = display_re.search(line, 0)
                if not m:
                    m = display_width_height_re.search(line, 0)
                if m:
                    for prop in ['width', 'height']:
                        display_info[prop] = int(m.group(prop))

        if 'orientation' not in display_info:
            surface_orientation_re = re.compile(r'SurfaceOrientation:\s+(\d+)')
            output = self.shell(['dumpsys', 'input'])
            m = surface_orientation_re.search(output)
            if m:
                display_info['orientation'] = int(m.group(1))

        density = None
        float_re = re.compile(r'[-+]?\d*\.\d+|\d+')
        d = self.get_property('ro.sf.lcd_density')
        if float_re.match(d):
            density = float(d)
        else:
            d = self.get_property('qemu.sf.lcd_density')
            if float_re.match(d):
                density = float(d)
            else:
                physical_density_re = re.compile(r'Physical density: (?P<density>[\d.]+)', re.MULTILINE)
                m = physical_density_re.search(self.shell(['wm', 'density']))
                if m:
                    density = float(m.group('density'))
        if density:
            display_info['density'] = density

        display_info_keys = {'width', 'height', 'orientation', 'density'}
        if not display_info_keys.issuperset(display_info):
            self.logger.warning('Unable to get {0}'.format(display_info_keys))

        return display_info

    def get_enabled_accessibility_services(self) -> List[str]:
        """
        Get a list with the enabled accessibility services.

        :return: A list with the enabled service names, using the format <package_name>/<service_name>.
        """
        pass
        output = self.shell(['settings', 'get', 'secure', 'enabled_accessibility_services'])
        output = re.sub(r'(?m)^WARNING:.*\n?', '', output)
        return output.strip().split(':') if output.strip() else []

    def get_installed_apps(self) -> dict:
        """
        Get the package names and the apk paths of the applications installed on the device.

        :return: A dictionary, each key is a package name and each value is the path to the apk file.
        """
        app_lines = self.shell(['pm', 'list', 'packages', '-f']).splitlines()
        app_line_re = re.compile('package:(?P<apk_path>.+)=(?P<package>[^=]+)')
        package_to_path = {}
        for app_line in app_lines:
            m = app_line_re.match(app_line)
            if m:
                package_to_path[m.group('package')] = m.group('apk_path')
        return package_to_path

    def get_orientation(self):
        """
        Get device orientation.

        :return: Device orientation.
        """
        display_info = self.get_display_info()
        if 'orientation' in display_info:
            return display_info['orientation']
        else:
            return -1

    def get_display_density(self):
        """
        Get device display density.

        :return: Get device display density.
        """
        display_info = self.get_display_info()
        if 'density' in display_info:
            return display_info['density']
        else:
            return -1.0

    def press(self, key_code: str):
        """
        Press a key.

        :param key_code: The name of the key to press.
        """
        self.shell(['input', 'keyevent', key_code])

    def long_touch(self, x, y, duration=2000):
        """
        Send a long touch command at (x, y).

        :param x: X screen coordinate.
        :param y: Y screen coordinate.
        :param duration: The duration (ms) of the touch operation.
        """
        self.drag((x, y), (x, y), duration, -1)

    def drag(self, start_xy, end_xy, duration, orientation=-1):
        """
        Send a drag event.

        :param start_xy: Starting point in pixel coordinates, passed as tuple (x, y).
        :param end_xy: Ending point in pixel coordinates, passed as tuple (x, y).
        :param duration: Duration of the drag event.
        :param orientation: Orientation (-1 for undefined).
        """

        def transform_point_by_orientation(xy, orientation_orig, orientation_dest):
            (x, y) = xy
            if orientation_orig != orientation_dest:
                if orientation_dest == 1:
                    _x = x
                    x = self.get_display_info()['width'] - y
                    y = _x
                elif orientation_dest == 3:
                    _x = x
                    x = y
                    y = self.get_display_info()['height'] - _x
            return x, y

        (x0, y0) = start_xy
        (x1, y1) = end_xy

        if orientation == -1:
            orientation = self.get_orientation()

        (x0, y0) = transform_point_by_orientation((x0, y0), orientation, self.get_orientation())
        (x1, y1) = transform_point_by_orientation((x1, y1), orientation, self.get_orientation())

        self.shell(['input', 'touchscreen', 'swipe', str(x0), str(y0), str(x1), str(y1), str(duration)])
