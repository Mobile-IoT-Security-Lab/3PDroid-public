#!/usr/bin/env python
# coding: utf-8

import copy
import json
import math
import os
import shutil
from datetime import datetime
from typing import List

from PIL import Image

from .input_event import InputEvent, TouchEvent, LongTouchEvent, ScrollEvent, SetTextEvent
from .smart_input import SmartInput
from .util import get_string_md5


class DeviceState(object):
    """
    The current state of the device.
    """

    def __init__(self, device, views, foreground_activity, activity_stack, background_services,
                 tag=None, screenshot_path=None):
        self.device = device
        self.foreground_activity = foreground_activity
        self.activity_stack = activity_stack if isinstance(activity_stack, list) else []
        self.background_services = background_services
        if not tag:
            tag = datetime.now().strftime('%d-%m-%Y_%H%M%S')
        self.tag = tag
        self.screenshot_path = screenshot_path
        self.views = self.parse_views(views)
        self.view_tree = {}
        self.assemble_view_tree(self.view_tree, self.views)
        self.generate_view_strings()
        self.state_str = self.get_state_str()
        self.structure_str = self.get_content_free_state_str()
        self.search_content = self.get_search_content()
        self.possible_events = None

    def to_dict(self):
        state = {'tag': self.tag,
                 'state_str': self.state_str,
                 'state_str_content_free': self.structure_str,
                 'foreground_activity': self.foreground_activity,
                 'activity_stack': self.activity_stack,
                 'background_services': self.background_services,
                 'views': self.views}
        return state

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    def parse_views(self, raw_views):
        views = []
        if not raw_views or len(raw_views) == 0:
            return views

        for view_dict in raw_views:
            views.append(view_dict)
        return views

    def assemble_view_tree(self, root_view, views):
        if not len(self.view_tree):
            self.view_tree = copy.deepcopy(views[0])
            self.assemble_view_tree(self.view_tree, views)
        else:
            children = list(enumerate(root_view['children']))
            if not len(children):
                return
            for i, j in children:
                root_view['children'][i] = copy.deepcopy(self.views[j])
                self.assemble_view_tree(root_view['children'][i], views)

    def generate_view_strings(self):
        for view_dict in self.views:
            self.get_view_str(view_dict)

    @staticmethod
    def calculate_depth(views):
        root_view = None
        for view in views:
            if DeviceState.safe_dict_get(view, 'parent') == -1:
                root_view = view
                break
        DeviceState.assign_depth(views, root_view, 0)

    @staticmethod
    def assign_depth(views, view_dict, depth):
        view_dict['depth'] = depth
        for view_id in DeviceState.safe_dict_get(view_dict, 'children', []):
            DeviceState.assign_depth(views, views[view_id], depth + 1)

    def get_state_str(self):
        state_str_raw = self.get_state_str_raw()
        return get_string_md5(state_str_raw)

    def get_state_str_raw(self):
        view_signatures = set()
        for view in self.views:
            view_signature = self.get_view_signature(view)
            if view_signature:
                view_signatures.add(view_signature)
        return '{0}{{{1}}}'.format(self.foreground_activity, ','.join(sorted(view_signatures)))

    def get_content_free_state_str(self):
        view_signatures = set()
        for view in self.views:
            view_signature = self.get_content_free_view_signature(view)
            if view_signature:
                view_signatures.add(view_signature)
        state_str = '{0}{{{1}}}'.format(self.foreground_activity, ','.join(sorted(view_signatures)))
        return get_string_md5(state_str)

    def get_search_content(self):
        words = [','.join(self.get_property_from_all_views('resource_id')),
                 ','.join(self.get_property_from_all_views('text'))]
        return '\n'.join(words)

    def get_property_from_all_views(self, property_name: str):
        property_values = set()
        for view in self.views:
            property_value = self.safe_dict_get(view, property_name, None)
            if property_value:
                property_values.add(property_value)
        return property_values

    def save2dir(self):
        try:
            if not self.device.output_dir:
                return
            else:
                output_dir = os.path.join(self.device.output_dir, 'states')

            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)

            dest_state_json_path = os.path.join(output_dir, 'state_{0}.json'.format(self.tag))
            dest_screenshot_path = os.path.join(output_dir, 'screen_{0}.png'.format(self.tag))
            with open(dest_state_json_path, 'w') as state_json_file:
                state_json_file.write(self.to_json())
            shutil.copyfile(self.screenshot_path, dest_screenshot_path)
            self.screenshot_path = dest_screenshot_path
        except Exception as e:
            self.device.logger.warning(e)

    def save_view_img(self, view_dict):
        try:
            if not self.device.output_dir:
                return
            else:
                output_dir = os.path.join(self.device.output_dir, 'views')

            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)

            view_str = view_dict['view_str']
            view_file_path = os.path.join(output_dir, 'view_{0}.png'.format(view_str))

            # The image already exists.
            if os.path.isfile(view_file_path):
                return

            # Load the original image.
            view_bound = view_dict['bounds']
            original_img = Image.open(self.screenshot_path)
            # View bound should be in original image bound.
            view_img = original_img.crop((min(original_img.width - 1, max(0, view_bound[0][0])),
                                          min(original_img.height - 1, max(0, view_bound[0][1])),
                                          min(original_img.width, max(0, view_bound[1][0])),
                                          min(original_img.height, max(0, view_bound[1][1]))))
            view_img.save(view_file_path)
        except Exception as e:
            self.device.logger.warning(e)

    @staticmethod
    def get_view_signature(view_dict: dict):
        """
        Get the signature of the given view.

        :param view_dict: An element of the list DeviceState.views.
        :return: A string containing the signature of the view.
        """

        if 'signature' in view_dict:
            return view_dict['signature']

        view_text = DeviceState.safe_dict_get(view_dict, 'text', 'None')
        if not view_text or len(view_text) > 50:
            view_text = 'None'
        content_description = DeviceState.safe_dict_get(view_dict, 'content_description', 'None')
        if content_description:
            content_description = content_description[:30]
        signature = '[class]{0}[resource_id]{1}[text]{2}[content]{3}[{4},{5},{6}]'.format(
            DeviceState.safe_dict_get(view_dict, 'class', 'None'),
            DeviceState.safe_dict_get(view_dict, 'resource_id', 'None'),
            view_text,
            content_description,
            DeviceState.key_if_true(view_dict, 'enabled'),
            DeviceState.key_if_true(view_dict, 'checked'),
            DeviceState.key_if_true(view_dict, 'selected'))
        view_dict['signature'] = signature
        return signature

    @staticmethod
    def get_content_free_view_signature(view_dict: dict):
        """
        Get the content-free signature of the given view.

        :param view_dict: An element of the list DeviceState.views.
        :return: A string containing the content-free signature of the view.
        """

        if 'content_free_signature' in view_dict:
            return view_dict['content_free_signature']
        content_free_signature = '[class]{0}[resource_id]{1}'.format(
            DeviceState.safe_dict_get(view_dict, 'class', 'None'),
            DeviceState.safe_dict_get(view_dict, 'resource_id', 'None'))
        view_dict['content_free_signature'] = content_free_signature
        return content_free_signature

    def get_view_str(self, view_dict: dict):
        """
        Get a string representation of the given view.

        :param view_dict: An element of the list DeviceState.views.
        :return: A string representation of the view.
        """

        if 'view_str' in view_dict:
            return view_dict['view_str']

        view_signature = self.get_view_signature(view_dict)
        parent_strings = []
        for parent_id in self.get_all_ancestors(view_dict):
            parent_strings.append(self.get_view_signature(self.views[parent_id]))
        parent_strings.reverse()
        child_strings = []
        for child_id in self.get_all_children(view_dict):
            child_strings.append(self.get_view_signature(self.views[child_id]))
        child_strings.sort()
        view_str = 'Activity:{0}\nSelf:{1}\nParents:{2}\nChildren:{3}'.format(
            self.foreground_activity, view_signature, '//'.join(parent_strings), '||'.join(child_strings))
        view_str = get_string_md5(view_str)
        view_dict['view_str'] = view_str
        return view_str

    def get_view_structure(self, view_dict: dict):
        """
        Get the structure of the given view.

        :param view_dict: An element of the list DeviceState.views.
        :return: A dict representing the view structure.
        """
        if 'view_structure' in view_dict:
            return view_dict['view_structure']
        width = self.get_view_width(view_dict)
        height = self.get_view_height(view_dict)
        class_name = self.safe_dict_get(view_dict, 'class', "None")
        children = {}

        root_x = view_dict['bounds'][0][0]
        root_y = view_dict['bounds'][0][1]

        child_view_ids = self.safe_dict_get(view_dict, 'children')
        if child_view_ids:
            for child_view_id in child_view_ids:
                child_view = self.views[child_view_id]
                child_x = child_view['bounds'][0][0]
                child_y = child_view['bounds'][0][1]
                relative_x, relative_y = child_x - root_x, child_y - root_y
                children['({0},{1})'.format(relative_x, relative_y)] = self.get_view_structure(child_view)

        view_structure = {
            '{0}({1}*{2})'.format(class_name, width, height): children
        }
        view_dict['view_structure'] = view_structure
        return view_structure

    @staticmethod
    def key_if_true(view_dict: dict, key):
        return key if (key in view_dict and view_dict[key]) else ''

    @staticmethod
    def safe_dict_get(view_dict: dict, key, default=None):
        return view_dict[key] if (key in view_dict) else default

    @staticmethod
    def get_view_center(view_dict: dict):
        """
        Get the center point in a view.

        :param view_dict: An element of the list DeviceState.views.
        :return: A tuple of integers representing the coordinates of the view's center.
        """

        bounds = view_dict['bounds']
        return (bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2

    @staticmethod
    def get_view_width(view_dict: dict):
        """
        Get the width of a view.

        :param view_dict: An element of the list DeviceState.views.
        :return: An integer representing the width of the view.
        """

        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][0] - bounds[1][0]))

    @staticmethod
    def get_view_height(view_dict: dict):
        """
        Get the height of a view.

        :param view_dict: An element of the list DeviceState.views.
        :return: An integer representing the height of the view.
        """

        bounds = view_dict['bounds']
        return int(math.fabs(bounds[0][1] - bounds[1][1]))

    def get_all_ancestors(self, view_dict: dict):
        """
        Get the view ids of the given view's ancestors.

        :param view_dict: An element of the list DeviceState.views.
        :return: List of integers (each being an ancestor node id).
        """
        result = []
        parent_id = self.safe_dict_get(view_dict, 'parent', -1)
        if 0 <= parent_id < len(self.views):
            result.append(parent_id)
            result += self.get_all_ancestors(self.views[parent_id])
        return result

    def get_all_children(self, view_dict: dict):
        """
        Get the view ids of the given view's children.

        :param view_dict: An element of the list DeviceState.views.
        :return: List of integers (each being a child node id).
        """
        children = self.safe_dict_get(view_dict, 'children')
        if not children:
            return set()
        children = set(children)
        for child in children.copy():
            children_of_child = self.get_all_children(self.views[child])
            children.update(children_of_child)
        return children

    def get_app_activity_depth(self, app):
        """
        Get the depth of the app's activity in the activity stack.
        :param app: App object instance.
        :return: The depth of app's activity (-1 if the activity was not found).
        """
        depth = 0
        for activity_str in self.activity_stack:
            if app.package_name in activity_str:
                return depth
            depth += 1
        return -1

    def get_possible_input(self) -> List[InputEvent]:
        """
        Get a list of possible input events for this state.

        :return: List of InputEvent.
        """
        if self.possible_events:
            return self.possible_events
        self.possible_events = []
        enabled_view_ids = []
        for view_dict in self.views:
            # Exclude navigation bar (if exists).
            if self.safe_dict_get(view_dict, 'enabled') and \
                    self.safe_dict_get(view_dict, 'resource_id') != 'android:id/navigationBarBackground':
                enabled_view_ids.append(view_dict['temp_id'])

        # This should make the buttons at the bottom of the page "preferred" (menu buttons at the top of the page
        # should be explored last).
        enabled_view_ids.reverse()

        for view_id in enabled_view_ids:
            # Ignore this view if it seems to be outside of the screen.
            view_center = self.get_view_center(self.views[view_id])
            if view_center[0] > self.device.get_width() or view_center[1] > self.device.get_height():
                self.device.logger.warning('View "{0}" is out of the screen so it will be ignored'
                                           .format(self.get_view_str(self.views[view_id])))
                continue

            # Editable fields first.
            if self.safe_dict_get(self.views[view_id], 'editable'):
                resource_id = self.views[view_id].get('resource_id', None)
                if resource_id:
                    try:
                        resource_id = resource_id.split(':id/')[1]
                    except Exception:
                        pass

                if self.device.smart_input_generator:
                    test_string = self.device.smart_input_generator.get_smart_input_for_id(resource_id)
                else:
                    test_string = SmartInput.default

                # Don't set the text if it's redundant.
                if self.views[view_id].get('text', None) != test_string:
                    self.possible_events.insert(0, SetTextEvent(view=self.views[view_id], text=test_string))

                # Avoid other actions (apart from setting text) on editable elements.
                continue

            if self.safe_dict_get(self.views[view_id], 'clickable'):
                self.possible_events.append(TouchEvent(view=self.views[view_id]))

            if self.safe_dict_get(self.views[view_id], 'scrollable'):
                self.possible_events.append(ScrollEvent(view=self.views[view_id], direction='DOWN'))
                self.possible_events.append(ScrollEvent(view=self.views[view_id], direction='RIGHT'))
                self.possible_events.append(ScrollEvent(view=self.views[view_id], direction='UP'))
                self.possible_events.append(ScrollEvent(view=self.views[view_id], direction='LEFT'))

            if self.safe_dict_get(self.views[view_id], 'checkable'):
                self.possible_events.append(TouchEvent(view=self.views[view_id]))

            if self.safe_dict_get(self.views[view_id], 'long_clickable'):
                self.possible_events.append(LongTouchEvent(view=self.views[view_id]))

        ####################################################################################################
        # TODO #############################################################################################
        ####################################################################################################

        # # There are no events to show to the user.
        # if not self.possible_events:
        #     return self.possible_events
        #
        # # Send over socket the list of possible actions (in order to let the user choose the action to perform).
        # self.device.droidbot_web_socket.send_over_socket(json.dumps([e.to_dict() for e in self.possible_events]))
        #
        # self.device.logger.info('Waiting for the user to choose the action to perform')
        #
        # try:
        #     input_event = InputEvent.from_dict(self.device.droidbot_web_socket.receive_from_socket())
        #     if not input_event:
        #         raise ValueError('Invalid input event')
        #     self.possible_events = [input_event]
        # except Exception as e:
        #     self.device.logger.warning('Unable to get input from user, proceeding with automatic input')

        ####################################################################################################
        # TODO #############################################################################################
        ####################################################################################################

        return self.possible_events
