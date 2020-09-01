#!/usr/bin/env python
# coding: utf-8

import hashlib
import logging
import os
from typing import List, Set

from androguard.core.bytecodes.apk import APK

from .intent import Intent


class App(object):
    """
    The class representing the application to be analyzed.
    """

    def __init__(self, apk_path: str):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        if not os.path.isfile(apk_path):
            raise FileNotFoundError('The input application file "{0}" was not found'.format(apk_path))

        self.apk_path = apk_path

        self.apk = APK(self.apk_path)

        self.hashes = self.get_hashes()

        self.package_name = self.apk.get_package()
        self.main_activities = self.apk.get_main_activities()

        # This is the variable that holds the list of intents that should be used to start the app. Every
        # time an intent is used to start the app, the code should check if the intent is valid (it starts
        # an existing activity), if it's not valid then the intent should be removed from this list.
        self.start_intents = self.get_start_intents()

        self.permissions = self.apk.get_permissions()
        self.activities = self.apk.get_activities()
        self.possible_broadcasts = self.get_possible_broadcasts()

    def get_hashes(self, block_size=65536) -> List[str]:
        """
        Calculate MD5, SHA1 and SHA256 hashes of the input application file.

        :param block_size: The size of the block used for the hash functions.
        :return: A list containing the MD5, SHA1 and SHA256 hashes of the input application file.
        """
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        with open(self.apk_path, 'rb') as filename:
            for chunk in iter(lambda: filename.read(block_size), b''):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                sha256_hash.update(chunk)
        return [md5_hash.hexdigest(), sha1_hash.hexdigest(), sha256_hash.hexdigest()]

    def get_package_name(self) -> str:
        """
        Get the package name of the current application.

        :return: The package name of the current application.
        """
        return self.package_name

    def get_main_activities(self) -> List[str]:
        """
        Get the main activities of the current application.

        :return: A list with the main activities of the current application.
        """
        return self.main_activities

    def get_start_intents(self) -> List[Intent]:
        """
        Get a list of intents to start the main activities of the current application. This method
        should be called only during initialization, after that use start_intents variable.

        :return: A list of intents to start the main activities of the current application.
        """
        list_of_intents: List[Intent] = []
        for activity in self.get_main_activities():
            list_of_intents.append(Intent(suffix='{0}/{1}'.format(self.package_name, activity)))
        if list_of_intents:
            return list_of_intents

        raise RuntimeError('This application has no main activity that can be used')

    def get_stop_intent(self):
        """
        Get an intent to stop the current application.

        :return: An intent to stop the current application.
        """
        return Intent(prefix='force-stop', suffix=self.package_name)

    def get_possible_broadcasts(self) -> Set[Intent]:
        """
        Get the intents to trigger the broadcast receivers in the current application.

        :return: A set with the intents to trigger the broadcast receivers in the current application.
        """
        possible_broadcasts = set()
        for receiver in self.apk.get_receivers():
            intent_filters = self.apk.get_intent_filters('receiver', receiver)
            actions = intent_filters['action'] if 'action' in intent_filters else []
            categories = intent_filters['category'] if 'category' in intent_filters else []
            categories.append(None)
            for action in actions:
                for category in categories:
                    intent = Intent(prefix='broadcast', action=action, category=category)
                    possible_broadcasts.add(intent)
        return possible_broadcasts
