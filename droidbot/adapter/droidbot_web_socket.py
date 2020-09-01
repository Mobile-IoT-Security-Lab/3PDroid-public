#!/usr/bin/env python
# coding: utf-8

import json
import logging
import os

import websocket

from .adapter import Adapter

if 'DROIDBOT_SOCKET_URL' in os.environ:
    DROIDBOT_SOCKET_URL = os.environ['DROIDBOT_SOCKET_URL']
else:
    DROIDBOT_SOCKET_URL = 'ws://localhost:8082'


class DroidBotWebSocket(Adapter):
    """
    The class representing a connection with a web socket where to send the results of the app stimulation.
    """

    def __init__(self, device):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device

        self.connected = False

        self.ws = websocket.WebSocket()

    def connect(self):
        try:
            self.ws.connect(DROIDBOT_SOCKET_URL)
            self.connected = True
        except Exception as e:
            self.logger.warning('Failed to connect with DroidBot socket: {0}'.format(e))
            self.connected = False

    def disconnect(self):
        self.connected = False
        self.logger.info('{0} disconnected'.format(self.__class__.__name__))

        if self.ws.connected:
            try:
                self.ws.close()
            except Exception as e:
                self.logger.warning('Unable to close connection with DroidBot socket: {0}'.format(e))

    def check_connectivity(self):
        return self.connected

    def set_up(self):
        pass

    def tear_down(self):
        pass

    def send_over_socket(self, message: str):
        if self.ws.connected:
            try:
                self.ws.send(message)
            except Exception as e:
                self.logger.warning('Unable to send the message to DroidBot socket: {0}'.format(e))
                self.connected = False
        else:
            self.logger.warning('Unable to send the message to DroidBot socket: not connected')

    def receive_from_socket(self) -> dict:
        if self.ws.connected:
            try:
                message = json.loads(self.ws.recv())['data']
                return json.loads(message)
            except Exception as e:
                self.logger.warning('Unable to read message from DroidBot socket: {0}'.format(e))
                self.connected = False
        else:
            self.logger.warning('Unable to read message from DroidBot socket: not connected')
