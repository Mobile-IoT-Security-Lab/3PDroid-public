#!/usr/bin/env python
# coding: utf-8

import logging
import os
import shutil
import threading
import frida_monitoring
from .app import App
from .device import Device
from .input_manager import InputManager
from p3detector.prediction_model import PredictionModel

class DroidBot(object):
    """
    The main class of DroidBot.
    """

    def __init__(self, apk_path: str, timeout: int = 0, output_dir: str = None, device_serial: str = None,
                 replay: bool = False, smart_input: bool = False, max_actions: int = 30, timeout_privacy: int = 60,
                 pdetector: PredictionModel = None, md5_app: str = None):

        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        # Make sure the input application exists.
        if not os.path.isfile(apk_path):
            raise FileNotFoundError('The input application file "{0}" was not found'.format(apk_path))

        # If an output directory was specified, make sure it exists and copy the resources into it.
        if output_dir and not os.path.isdir(output_dir) and not replay:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self.logger.error('Unable to create output directory "{0}": {1}'.format(output_dir, e))
                raise

            html_index_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'index.html')
            stylesheets_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'stylesheets')
            target_stylesheets_dir = os.path.join(output_dir, 'stylesheets')

            shutil.copy(html_index_path, output_dir)
            shutil.copytree(stylesheets_path, target_stylesheets_dir)

        self.apk_path = apk_path
        self.output_dir = output_dir

        self.enabled = True

        self.timeout = timeout
        self.timeout_reached = False
        self.timer = None

        self.max_actions = max_actions
        self.timeout_privacy = timeout_privacy

        self.app = None
        self.device = None
        self.input_manager = None
        self.pdetector = pdetector
        self.md5_app = md5_app

        try:
            self.app = App(self.apk_path)
            self.device = Device(app=self.app, output_dir=self.output_dir, device_serial=device_serial,
                                 replay=replay, smart_input=smart_input)
            self.input_manager = InputManager(device=self.device, app=self.app, replay=replay,
                                              max_actions=self.max_actions, timeout_privacy=self.timeout_privacy,
                                              pdetector=self.pdetector, md5_app=self.md5_app)
        except Exception as e:
            self.logger.error('Error during DroidBot initialization: {0}'.format(e))
            self.stop()
            raise

    def start(self, frida_monitoring=None):
        """
        Start interacting with the application.
        """
        self.logger.info('Starting DroidBot and the interaction with the application')
        try:
            if self.timeout:
                self.logger.info('DroidBot will time out after {0} seconds'.format(self.timeout))
                self.timer = threading.Timer(self.timeout, self.timeout_stop)
                self.timer.daemon = True
                self.timer.start()

            self.device.set_up()
            self.device.connect()
            self.device.install_app(self.app)
            if frida_monitoring is not None:
                path_file_monitoring = os.path.join(os.getcwd(), "hook", self.md5_app,
                                                    "frida_api.txt")
                frida_monitoring.start(self.app.package_name, 0, path_file_monitoring)
            self.input_manager.start()
        except KeyboardInterrupt:
            if not self.input_manager.exit_event_received:
                self.logger.warning('DroidBot interrupted by user')
        except Exception as e:
            if not self.timeout_reached:
                self.logger.error('Error during DroidBot execution: {0}'.format(e))
                raise
        finally:
            if self.enabled:
                self.stop()
                self.logger.info('DroidBot stopped')

    def stop(self):
        """
        Stop the DroidBot instance.
        """
        if self.enabled:
            self.enabled = False

            if self.timer and self.timer.is_alive():
                self.timer.cancel()

            if self.input_manager:
                self.input_manager.stop()

            if self.device:
                self.device.disconnect()

    def timeout_stop(self):
        self.timeout_reached = True

        if self.timeout:
            self.logger.warning('DroidBot timed out after {0} seconds'.format(self.timeout))

        if self.timer and self.timer.is_alive():
            self.timer.cancel()

        if self.input_manager:
            # Stop sending events, DroidBot will exit gracefully.
            self.input_manager.stop()
