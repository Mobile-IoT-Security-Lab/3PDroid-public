#!/usr/bin/env python
# coding: utf-8

import logging
import os

from .adapter import Adapter

DROIDBOT_APP_PACKAGE = 'io.github.ylimit.droidbotapp'
IME_SERVICE = '{0}/.DroidBotIME'.format(DROIDBOT_APP_PACKAGE)


class DroidBotIme(Adapter):
    """
    The class representing a connection with the DroidBot IME service on the device.
    """

    def __init__(self, device):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device

        self.connected = False

    def connect(self):
        ime_enabled = self.device.adb.shell(['ime', 'enable', IME_SERVICE])
        if ime_enabled.endswith(('already enabled', 'now enabled')):
            ime_selected = self.device.adb.shell(['ime', 'set', IME_SERVICE])
            if ime_selected.endswith('selected'):
                self.connected = True
                self.logger.info('{0} connected'.format(self.__class__.__name__))
                return

        self.logger.warning('Failed to connect DroidBotIME')

    def disconnect(self):
        self.connected = False
        ime_disable = self.device.adb.shell(['ime', 'disable', IME_SERVICE])
        if ime_disable.endswith('now disabled'):
            self.logger.info('{0} disconnected'.format(self.__class__.__name__))
            return

        self.logger.warning('Failed to disconnect DroidBotIME')

    def check_connectivity(self):
        return self.connected

    def set_up(self):
        if DROIDBOT_APP_PACKAGE in self.device.adb.get_installed_apps():
            self.logger.debug('DroidBot app is already installed')
        else:
            # Install DroidBot app.
            try:
                droidbot_app_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                 'resources', 'droidbotApp.apk')
                install_cmd = ['install', droidbot_app_path]
                self.device.adb.run_cmd(install_cmd)
                self.logger.debug('DroidBot app installed')
            except Exception as e:
                self.logger.warning('Failed to install DroidBot app: {0}'.format(e))

    def tear_down(self):
        self.device.uninstall_app(DROIDBOT_APP_PACKAGE)

    def input_text(self, text: str, mode: int = 0):
        """
        Input text into target device.

        :param text: Text to insert.
        :param mode: 0 to set text, 1 to append text.
        """
        input_cmd = ['am', 'broadcast', '-a', 'DROIDBOT_INPUT_TEXT', '--es', 'text',
                     '"{0}"'.format(text), '--ei', 'mode', str(mode)]
        self.device.adb.shell(input_cmd)
