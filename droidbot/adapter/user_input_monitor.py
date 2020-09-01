#!/usr/bin/env python
# coding: utf-8

import logging
import os
import subprocess
import threading

from .adapter import Adapter


class UserInputMonitor(Adapter):
    """
    The class representing a connection with the device through `getevent`, which is able to
    get raw user input from device.
    """

    def __init__(self, device):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device

        self.connected = False

        self.process = None

        if not device.output_dir:
            self.out_file = None
        else:
            self.out_file = os.path.join(device.output_dir, 'user_input.txt')

    def connect(self):
        try:
            self.process = subprocess.Popen(['adb', '-s', self.device.serial, 'shell', 'getevent', '-lt'],
                                            stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        except Exception:
            self.process = None

        threading.Thread(target=self.handle_output, daemon=True).start()

    def disconnect(self):
        self.connected = False

        if self.process:
            self.process.terminate()

        self.logger.info('{0} disconnected'.format(self.__class__.__name__))

    def check_connectivity(self):
        return self.connected

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def handle_output(self):
        self.connected = True
        self.logger.info('{0} connected'.format(self.__class__.__name__))

        if self.out_file:
            with open(self.out_file, 'w') as destination_file:
                while self.connected:
                    if not self.process:
                        continue
                    line = self.process.stdout.readline().decode()
                    destination_file.write(line)

            self.logger.info('{0} disconnected'.format(self.__class__.__name__))
