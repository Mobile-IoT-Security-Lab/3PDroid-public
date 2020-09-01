#!/usr/bin/env python
# coding: utf-8

from typing import List


class Intent(object):
    """
    The class representing an intent event.
    """

    def __init__(self, prefix='start', action=None, data_uri=None, mime_type=None, category=None,
                 component=None, flag=None, extra_keys=None, extra_string=None, extra_boolean=None,
                 extra_int=None, extra_long=None, extra_float=None, extra_uri=None, extra_component=None,
                 extra_array_int=None, extra_array_long=None, extra_array_float=None, flags=None, suffix=''):
        self.event_type = 'intent'
        self.prefix = prefix
        self.action = action
        self.data_uri = data_uri
        self.mime_type = mime_type
        self.category = category
        self.component = component
        self.flag = flag
        self.extra_keys = extra_keys
        self.extra_string = extra_string
        self.extra_boolean = extra_boolean
        self.extra_int = extra_int
        self.extra_long = extra_long
        self.extra_float = extra_float
        self.extra_uri = extra_uri
        self.extra_component = extra_component
        self.extra_array_int = extra_array_int
        self.extra_array_long = extra_array_long
        self.extra_array_float = extra_array_float
        self.flags = flags
        self.suffix = suffix

        self.cmd = None
        self.get_cmd()

    def get_cmd(self) -> List[str]:
        """
        Convert the intent to an actionable command.

        :return: The command to start the intent, returned as list of strings.
        """
        if self.cmd:
            return self.cmd

        cmd = ['am']

        if self.prefix:
            if isinstance(self.prefix, list):
                cmd.extend(self.prefix)
            elif isinstance(self.prefix, str):
                cmd.append(self.prefix)

        if self.action:
            cmd.append('-a')
            if isinstance(self.action, list):
                cmd.extend(self.action)
            elif isinstance(self.action, str):
                cmd.append(self.action)

        if self.data_uri:
            cmd.append('-d')
            if isinstance(self.data_uri, list):
                cmd.extend(self.data_uri)
            elif isinstance(self.data_uri, str):
                cmd.append(self.data_uri)

        if self.mime_type:
            cmd.append('-t')
            if isinstance(self.mime_type, list):
                cmd.extend(self.mime_type)
            elif isinstance(self.mime_type, str):
                cmd.append(self.mime_type)

        if self.category:
            cmd.append('-c')
            if isinstance(self.category, list):
                cmd.extend(self.category)
            elif isinstance(self.category, str):
                cmd.append(self.category)

        if self.component:
            cmd.append('-n')
            if isinstance(self.component, list):
                cmd.extend(self.component)
            elif isinstance(self.component, str):
                cmd.append(self.component)

        if self.flag:
            cmd.append('-f')
            if isinstance(self.flag, list):
                cmd.extend(self.flag)
            elif isinstance(self.flag, str):
                cmd.append(self.flag)

        if self.extra_keys:
            for key in self.extra_keys:
                cmd.extend(['--esn', '"{0}"'.format(key)])

        if self.extra_string:
            for key in list(self.extra_string.keys()):
                cmd.extend(['-e', '"{0}"'.format(key), '"{0}"'.format(self.extra_string[key])])

        if self.extra_boolean:
            for key in list(self.extra_boolean.keys()):
                cmd.extend(['-ez', '"{0}"'.format(key), str(self.extra_boolean[key])])

        if self.extra_int:
            for key in list(self.extra_int.keys()):
                cmd.extend(['-ei', '"{0}"'.format(key), str(self.extra_int[key])])

        if self.extra_long:
            for key in list(self.extra_long.keys()):
                cmd.extend(['-el', '"{0}"'.format(key), str(self.extra_long[key])])

        if self.extra_float:
            for key in list(self.extra_float.keys()):
                cmd.extend(['-ef', '"{0}"'.format(key), str(self.extra_float[key])])

        if self.extra_uri:
            for key in list(self.extra_uri.keys()):
                cmd.extend(['-eu', '"{0}"'.format(key), '"{0}"'.format(self.extra_uri[key])])

        if self.extra_component:
            for key in list(self.extra_component.keys()):
                cmd.extend(['-ecn', '"{0}"'.format(key), self.extra_component[key]])

        if self.extra_array_int:
            for key in list(self.extra_array_int.keys()):
                cmd.extend(['-eia', '"{0}"'.format(key), ','.join(self.extra_array_int[key])])

        if self.extra_array_long:
            for key in list(self.extra_array_long.keys()):
                cmd.extend(['-ela', '"{0}"'.format(key), ','.join(self.extra_array_long[key])])

        if self.extra_array_float:
            for key in list(self.extra_array_float.keys()):
                cmd.extend(['-efa', '"{0}"'.format(key), ','.join(self.extra_array_float[key])])

        if self.flags:
            cmd.extend(self.flags)

        if self.suffix:
            if isinstance(self.suffix, list):
                cmd.extend(self.suffix)
            elif isinstance(self.suffix, str):
                cmd.append(self.suffix)

        self.cmd = cmd

        return self.cmd
