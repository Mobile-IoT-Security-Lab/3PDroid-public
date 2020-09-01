#!/usr/bin/env python
# coding: utf-8

import datetime
import json
import logging
import os

import networkx as nx

from .util import list_to_html_table


class UTG(object):
    """
    Class representing UI Transition Graph.
    """

    def __init__(self, device, app):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device
        self.app = app

        self.G = nx.DiGraph()

        self.effective_event_strings = set()
        self.ineffective_event_strings = set()
        self.explored_state_strings = set()
        self.reached_state_strings = set()
        self.reached_activities = set()

        self.first_state_str = None
        self.last_state_str = None
        self.last_transition = None
        self.effective_event_count = 0
        self.input_event_count = 0

        self.start_time = datetime.datetime.now()

    def add_transition(self, event, old_state, new_state):
        self.add_node(old_state)
        self.add_node(new_state)

        # Make sure the states are not None.
        if not old_state or not new_state:
            return

        event_str = event.get_event_str(old_state)
        self.input_event_count += 1

        if old_state.state_str == new_state.state_str:
            self.ineffective_event_strings.add(event_str)
            # Delete the transitions including the event from UTG.
            for new_state_str in self.G[old_state.state_str]:
                if event_str in self.G[old_state.state_str][new_state_str]['events']:
                    self.G[old_state.state_str][new_state_str]['events'].pop(event_str)
            if event_str in self.effective_event_strings:
                self.effective_event_strings.remove(event_str)
            return

        self.effective_event_strings.add(event_str)
        self.effective_event_count += 1

        if (old_state.state_str, new_state.state_str) not in self.G.edges():
            self.G.add_edge(old_state.state_str, new_state.state_str, events={})

        self.G[old_state.state_str][new_state.state_str]['events'][event_str] = {
            'event': event,
            'id': self.effective_event_count
        }
        self.last_state_str = new_state.state_str
        self.last_transition = (old_state.state_str, new_state.state_str)
        self.save_utg_to_file()

    def add_node(self, state):
        if not state:
            return
        if state.state_str not in self.G.nodes():
            state.save2dir()
            self.G.add_node(state.state_str, state=state)
            if not self.first_state_str:
                self.first_state_str = state.state_str
        if state.foreground_activity.startswith(self.app.package_name):
            self.reached_activities.add(state.foreground_activity)

    def save_utg_to_file(self):
        """
        Save the current UI Transition Graph to a file.
        """
        if not self.device.output_dir:
            return

        utg_nodes = []
        utg_edges = []
        for state_str in self.G.nodes():
            state = self.G.nodes[state_str]['state']
            package_name = state.foreground_activity.split('/')[0]
            activity_name = state.foreground_activity.split('/')[1]
            short_activity_name = activity_name.split('.')[-1]

            state_desc = list_to_html_table([
                ('package', package_name),
                ('activity', activity_name),
                ('state_str', state.state_str),
                ('structure_str', state.structure_str)
            ])

            utg_node = {
                'id': state_str,
                'shape': 'image',
                'image': os.path.relpath(state.screenshot_path, self.device.output_dir),
                'label': short_activity_name,
                'package': package_name,
                'activity': activity_name,
                'state_str': state_str,
                'structure_str': state.structure_str,
                'title': state_desc,
                'content': '\n'.join([package_name, activity_name, state.state_str, state.search_content])
            }

            if state.state_str == self.first_state_str:
                utg_node['label'] += '\n<FIRST>'
                utg_node['font'] = '14px Arial red'
            if state.state_str == self.last_state_str:
                utg_node['label'] += '\n<LAST>'
                utg_node['font'] = '14px Arial red'

            utg_nodes.append(utg_node)

        for state_transition in self.G.edges():
            from_state = state_transition[0]
            to_state = state_transition[1]

            events = self.G[from_state][to_state]['events']
            event_short_desc = []
            event_list = []

            for event_str, event_info in sorted(iter(events.items()), key=lambda x: x[1]['id']):
                event_short_desc.append((event_info['id'], event_str))
                view_images = ['views/view_{0}.png'.format(view['view_str'])
                               for view in event_info['event'].get_views()]
                event_list.append({
                    'event_str': event_str,
                    'event_id': event_info['id'],
                    'event_type': event_info['event'].event_type,
                    'view_images': view_images
                })

            utg_edge = {
                'from': from_state,
                'to': to_state,
                'id': '{0}-->{1}'.format(from_state, to_state),
                'title': list_to_html_table(event_short_desc),
                'label': ', '.join([str(x['event_id']) for x in event_list]),
                'events': event_list
            }

            utg_edges.append(utg_edge)

        utg = {
            'nodes': utg_nodes,
            'edges': utg_edges,

            'num_nodes': len(utg_nodes),
            'num_edges': len(utg_edges),
            'num_effective_events': len(self.effective_event_strings),
            'num_reached_activities': len(self.reached_activities),
            'test_date': self.start_time.strftime('%d-%m-%Y_%H%M%S'),
            'time_spent': (datetime.datetime.now() - self.start_time).total_seconds(),
            'num_input_events': self.input_event_count,

            'device_serial': self.device.serial,
            'device_sdk_version': self.device.get_sdk_version(),

            'app_sha256': self.app.hashes[2],
            'app_package': self.app.package_name,
            'app_main_activities': list(self.app.main_activities),
            'app_num_total_activities': len(self.app.activities),
        }

        utg_file_path = os.path.join(self.device.output_dir, 'utg.js')
        with open(utg_file_path, 'w') as utg_file:
            utg_file.write('var utg = \n')
            utg_file.write(json.dumps(utg, indent=2))

    def is_event_explored(self, event, state):
        event_str = event.get_event_str(state)
        return event_str in self.effective_event_strings or event_str in self.ineffective_event_strings

    def is_state_explored(self, state):
        if state.state_str in self.explored_state_strings:
            return True
        for possible_event in state.get_possible_input():
            if not self.is_event_explored(possible_event, state):
                return False
        self.explored_state_strings.add(state.state_str)
        return True

    def is_state_reached(self, state):
        if state.state_str in self.reached_state_strings:
            return True
        self.reached_state_strings.add(state.state_str)
        return False

    def get_reachable_states(self, current_state):
        reachable_states = []
        for target_state_str in nx.descendants(self.G, current_state.state_str):
            target_state = self.G.nodes[target_state_str]['state']
            reachable_states.append(target_state)
        return reachable_states

    def get_event_path(self, current_state, target_state):
        path_events = []
        try:
            states = nx.shortest_path(G=self.G, source=current_state.state_str, target=target_state.state_str)
            if not isinstance(states, list) or len(states) < 2:
                self.logger.warning('Unable to get the path from "{0}" to "{0}"'.format(current_state.state_str,
                                                                                        target_state.state_str))
            start_state = states[0]
            for state in states[1:]:
                edge = self.G[start_state][state]
                edge_event_strings = list(edge['events'].keys())
                path_events.append(edge['events'][edge_event_strings[0]]['event'])
                start_state = state
        except Exception:
            self.logger.warning('Cannot find a path from "{0}" to "{0}"'.format(current_state.state_str,
                                                                                target_state.state_str))
        return path_events
