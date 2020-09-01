#!/usr/bin/env python
# coding: utf-8

from abc import ABC, abstractmethod


class Adapter(ABC):

    @abstractmethod
    def connect(self):
        raise NotImplementedError()

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError()

    @abstractmethod
    def check_connectivity(self):
        raise NotImplementedError()

    @abstractmethod
    def set_up(self):
        raise NotImplementedError()

    @abstractmethod
    def tear_down(self):
        raise NotImplementedError()
