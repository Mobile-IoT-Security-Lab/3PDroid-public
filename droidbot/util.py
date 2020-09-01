#!/usr/bin/env python
# coding: utf-8

import hashlib
import subprocess
from typing import List


def get_available_devices() -> List[str]:
    """
    Get a list with the device serials connected via adb.

    :return: A list of strings, each string is a device serial number.
    """
    output = subprocess.check_output(['adb', 'devices'], stderr=subprocess.STDOUT).strip().decode()

    devices = []
    for line in output.splitlines():
        tokens = line.strip().split()
        if len(tokens) == 2 and tokens[1] == 'device':
            # Add to the list the ip and port of the device.
            devices.append(tokens[0])
    return devices


def list_to_html_table(dict_data):
    table = '<table class="table">\n'
    for (key, value) in dict_data:
        table += '<tr><th>{0}</th><td>{1}</td></tr>\n'.format(key, value)
    table += '</table>'
    return table


def get_string_md5(input_string: str) -> str:
    return hashlib.md5(input_string.encode()).hexdigest()
