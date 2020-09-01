#!/usr/bin/env python
# coding: utf-8

import copy
import json
import logging
import os
import socket
import struct
import threading
import time
from typing import Optional, List

from .adapter import Adapter

DROIDBOT_APP_PACKAGE = 'io.github.ylimit.droidbotapp'
ACCESSIBILITY_SERVICE = '{0}/io.github.privacystreams.accessibility.PSAccessibilityService'.format(DROIDBOT_APP_PACKAGE)
DROIDBOT_APP_REMOTE_ADDRESS = 'tcp:7336'
DROIDBOT_APP_PACKET_HEAD_LEN = 6
MAX_NUM_GET_VIEWS = 30

if 'GET_VIEW_WAIT_TIME' in os.environ:
    GET_VIEW_WAIT_TIME = os.environ['GET_VIEW_WAIT_TIME']
else:
    GET_VIEW_WAIT_TIME = 2


class DroidBotApp(Adapter):
    """
    The class representing a connection with the DroidBot app on the device.
    """

    def __init__(self, device):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device

        self.connected = False

        self.host = 'localhost'
        self.port = self.device.get_host_random_port()

        self.sock = None
        self.last_acc_event = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Forward host port to remote port.
            self.device.adb.run_cmd(['forward', 'tcp:{0}'.format(self.port), DROIDBOT_APP_REMOTE_ADDRESS])
            self.sock.connect((self.host, self.port))
            threading.Thread(target=self.listen_messages, daemon=True).start()
        except Exception as e:
            self.connected = False
            self.logger.error('Failed to connect with DroidBot app: {0}'.format(e))
            raise

    def disconnect(self):
        self.connected = False
        self.logger.info('{0} disconnected'.format(self.__class__.__name__))

        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                self.logger.warning('Unable to close connection with DroidBot app: {0}'.format(e))
        try:
            self.device.adb.run_cmd(['forward', '--remove', 'tcp:{0}'.format(self.port)])
        except Exception as e:
            self.logger.warning('Unable to remove adb forwarding: {0}'.format(e))

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

        while ACCESSIBILITY_SERVICE not in self.device.get_service_names():
            self.logger.warning('Please enable accessibility for DroidBot app manually')
            time.sleep(2)

    def tear_down(self):
        self.device.uninstall_app(DROIDBOT_APP_PACKAGE)

    def sock_read(self, message_length) -> bytes:
        buffer = None
        while message_length:
            packet = self.sock.recv(message_length)
            if not packet:
                raise EOFError()
            if not buffer:
                buffer = packet
            else:
                buffer += packet
            message_length -= len(packet)
        return buffer

    def read_head(self) -> tuple:
        header = self.sock_read(DROIDBOT_APP_PACKET_HEAD_LEN)
        data = struct.unpack('>BBI', header)
        return data

    def listen_messages(self):
        self.connected = True
        self.logger.info('{0} connected'.format(self.__class__.__name__))

        try:
            while self.connected:
                _, _, message_len = self.read_head()
                message = self.sock_read(message_len).decode()
                self.handle_message(message)
        except Exception as e:
            if self.connected:
                # This was only a socket error, so restart the communication.
                self.logger.warning('Error during the socket communication: {0}'.format(e))
                self.logger.info('Restarting communication over socket with DroidBot app')
                self.last_acc_event = None
                self.disconnect()
                self.connect()
            else:
                # The communication was intentionally stopped.
                return

    def handle_message(self, message):
        acc_event_idx = message.find('AccEvent >>> ')
        if acc_event_idx >= 0:
            if acc_event_idx > 0:
                self.logger.warning('Invalid data before packet header: {0}'.format(message[:acc_event_idx]))
            body = json.loads(message[acc_event_idx + len('AccEvent >>> '):])
            self.last_acc_event = body
            return

        rotation_idx = message.find('rotation >>> ')
        if rotation_idx >= 0:
            if rotation_idx > 0:
                self.logger.warning('Invalid data before packet header: {0}'.format(message[:rotation_idx]))
            return

        raise IOError('Unexpected message from DroidBot app: {0}'.format(message))

    def get_views(self) -> Optional[List[dict]]:
        get_views_times = 0
        while not self.last_acc_event or 'root_node' not in self.last_acc_event or not self.last_acc_event['root_node']:
            self.logger.warning('last_acc_event is None, waiting')
            get_views_times += 1
            if get_views_times >= MAX_NUM_GET_VIEWS:
                self.logger.warning('Cannot get last_acc_event that is not None')
                return None
            time.sleep(GET_VIEW_WAIT_TIME)

        if 'view_list' in self.last_acc_event:
            return self.last_acc_event['view_list']

        view_tree = copy.deepcopy(self.last_acc_event['root_node'])
        if not view_tree:
            return None
        view_tree['parent'] = -1
        view_list = []
        self._view_tree_to_list(view_tree, view_list)
        self.last_acc_event['view_list'] = view_list
        return view_list

    def _view_tree_to_list(self, view_tree, view_list):
        tree_id = len(view_list)
        view_tree['temp_id'] = tree_id

        bounds = [[-1, -1], [-1, -1]]
        bounds[0][0] = view_tree['bounds'][0]
        bounds[0][1] = view_tree['bounds'][1]
        bounds[1][0] = view_tree['bounds'][2]
        bounds[1][1] = view_tree['bounds'][3]
        width = bounds[1][0] - bounds[0][0]
        height = bounds[1][1] - bounds[0][1]
        view_tree['size'] = '{0}*{1}'.format(width, height)
        view_tree['bounds'] = bounds

        view_list.append(view_tree)
        children_ids = []
        for child_tree in view_tree['children']:
            child_tree['parent'] = tree_id
            self._view_tree_to_list(child_tree, view_list)
            children_ids.append(child_tree['temp_id'])
        view_tree['children'] = children_ids
