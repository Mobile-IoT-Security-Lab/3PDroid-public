#!/usr/bin/env python
# coding: utf-8

import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from p3detector.prediction_model import PredictionModel
import shutil
from .input_event import InputEvent, KeyEvent, SetTextEvent, IntentEvent, ExitEvent, NopEvent
from .utg import UTG
import lxml.etree as etree

# This is needed in order to have reproducible results.
random.seed(42)

if 'EXPLORATION_REPLAY_FAIL_INTERVAL' in os.environ:
    EXPLORATION_REPLAY_FAIL_INTERVAL = os.environ['EXPLORATION_REPLAY_FAIL_INTERVAL']
else:
    EXPLORATION_REPLAY_FAIL_INTERVAL = 5

# Max number of action attempts.
MAX_NUM_ATTEMPTS = 5

# Max number of steps outside the app.
MAX_NUM_STEPS_OUTSIDE = 3
MAX_NUM_STEPS_OUTSIDE_KILL = 6

# Input event flags.
EVENT_FLAG_START_APP = '+start_app'
EVENT_FLAG_STOP_APP = '+stop_app'
EVENT_FLAG_EXPLORE = '+explore'
EVENT_FLAG_NAVIGATE = '+navigate'
MEAN_WORD_POLICY = 10
TRESHOLD_PROBABILITY_PP = 0.1

class InputPolicy(ABC):
    """
    The class responsible for generating events to stimulate app behaviour.
    """

    def __init__(self, device, app, max_actions, timeout_privacy, pdetector: PredictionModel, md5_app=None):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.device = device
        self.app = app
        self.list_event = list()
        self.list_page_visited = list()
        self.max_actions = max_actions
        self.timeout_privacy = timeout_privacy
        self.current_state = None
        self.md5_privacy_policy_page = ""
        self.back_button_change_page = False
        self.home_button_change_page = False
        self.timeout_reached = False
        self.detected = False
        self.pdetector = pdetector
        self.md5_app = md5_app
        self.content_privacy_policy_page = None

    def start(self, input_manager):
        """
        Start producing events.

        :param input_manager: Instance of InputManager.
        """

        count = 0
        # dir_app = self.app.package_name.replace(".","_")
        dir_app = self.md5_app
        dir_app_complete = os.path.join(os.getcwd(), "xml_dump", dir_app)
        if not os.path.exists(dir_app_complete):
            os.makedirs(dir_app_complete)

        while input_manager.enabled \
                and not self.detected \
                and len(self.list_event) < self.max_actions:

            # Start the stimulation by going to the home screen and then start the app.
            if count == 0:
                event = KeyEvent(name='HOME')
                self.device.send_event(event)
                count += 1
                continue

            if count == 1:
                event = IntentEvent(intent=self.app.start_intents[0])
            else:
                event = self.generate_event()

            input_manager.add_event(event)  # send event to device
            count += 1  # add event, if the count == 2 --> start app first time
            if count == 2:  # waiting open first app page
                time.sleep(2)
            self.logger.info("Add event to list_event")
            self.list_event.append(event)

            # if the analysis go out from app's surface we do not analyze the content of the page
            if self.device.is_foreground(self.app.get_package_name()):
                if self.device.get_current_state().state_str not in self.list_page_visited:

                    self.logger.info("New page Found --> we need detect if it contains policy page or not")
                    self.list_page_visited.append(
                        self.device.get_current_state().state_str)  # add md5 to list_page visited
                    self.device.adb.shell(['uiautomator dump'])
                    try:
                        md5_page = self.device.get_current_state().state_str
                        xml_name_file = os.path.join(dir_app_complete,
                                                     "{0}.xml".format(md5_page))
                        # mCurrentFocus=Window{1316822 u0 com.android.browser/com.android.browser.BrowserActivity}
                        try:
                            self.device.pull_file("/sdcard/window_dump.xml", xml_name_file)  # dump xml page on host dir

                        except Exception as e:
                            self.logger.error("Error occured when try to dump screenshot image {}".format(e))

                        # etree.tostring(file, pretty_print=True)

                        prepr_text = self.pdetector.preprocess_data(xml_name_file)
                        if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:

                            self.logger.info("Page with more than {} words, check if it is privacy policy page or not "
                                             .format(MEAN_WORD_POLICY))
                            self.logger.info("Content page: {}".format(prepr_text))
                            probability_privacy_policy = float(self.pdetector.predict(prepr_text))

                            self.logger.info("The current page is privacy policy page with {0:.2f}% of probability "
                                             .format((1 - probability_privacy_policy) * 100))

                            self.detected = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False
                            if self.detected:
                                self.content_privacy_policy_page = prepr_text[0]
                                try:
                                    self.device.adb.shell(["screencap -p /sdcard/screen.png"])

                                    self.device.pull_file("/sdcard/screen.png",
                                                      os.path.join(os.getcwd(), "screenshot_pages",
                                                                   "{}.png".format(
                                                                       md5_page)))
                                except Exception as e:
                                    self.logger.error("Error occured when try to dump screenshot image {}".format(e))
                        else:
                            self.logger.info(
                                "The current page has less than {} word, so it is not probably a privacy policy page ".
                                format(MEAN_WORD_POLICY))
                            self.detected = False

                        if self.detected:
                            self.md5_privacy_policy_page = md5_page

                    except Exception as e:
                        self.logger.error("Exception as {}".format(e))


                else:
                    self.logger.info("Old page, we have already analyzed it")
            else:
                self.logger.info("We are outside from the app")

        if not input_manager.enabled and not self.detected:
            # we reach timeout
            self.list_event = [None] * self.max_actions

        if self.detected:
            self.logger.info("Privacy Policy Page detected")

            shutil.copy(os.path.join(dir_app_complete, "{}.xml".format(self.md5_privacy_policy_page)),
                        os.path.join(os.getcwd(), "privacypoliciesxml", "{}_{}.xml".format(self.md5_app,
                                                                                           self.md5_privacy_policy_page))
                        )

            path_file_privacy_policy_content = os.path.join(os.getcwd(), "privacypoliciesxml",
                                                            "{}_{}_cleaned.txt".format(self.md5_app,
                                                                                       self.md5_privacy_policy_page))
            with open(path_file_privacy_policy_content, "w") as privacy_policy_content:
                privacy_policy_content.write(self.content_privacy_policy_page)

            # 1) we need to detect if the privacy page contains explicit acceptance
            # ToDo

            ##################################### TIMEOUT MECHANISM #####################################
            self.logger.info("Check if the app has a timeout mechanism for the privacy policy")
            time.sleep(self.timeout_privacy)
            self.device.adb.shell(['uiautomator dump'])
            xml_name_file_temp = os.path.join(dir_app_complete,"{0}.xml".format("temp"))
            try:
                self.device.pull_file("/sdcard/window_dump.xml", xml_name_file_temp)  # dump xml page on host dir
            except Exception as e:
                self.logger.error("Error occured when try to dump screenshot image {}".format(e))

            detected = False
            prepr_text = self.pdetector.preprocess_data(xml_name_file_temp)
            if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:
                probability_privacy_policy = float(self.pdetector.predict(prepr_text))
                detected = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False
            # current_state = self.device.get_current_state().state_str
            if not detected:
                self.logger.info("The app has a timeout mechanism")
                self.timeout_reached = True
            else:
                self.logger.info("The privacy policy is still there")

            ##################################### CHECK HOME BUTTONS MECHANISM #####################################
            self.logger.info("Check if the pressing of the HOME button changes the privacy policy page")
            event = KeyEvent(name='HOME')
            input_manager.add_event(event)
            # open app again
            event = IntentEvent(intent=self.app.start_intents[0])
            input_manager.add_event(event)
            time.sleep(3)

            self.device.adb.shell(['uiautomator dump'])
            xml_name_file_temp = os.path.join(dir_app_complete, "{0}.xml".format("temp"))
            try:
                self.device.pull_file("/sdcard/window_dump.xml", xml_name_file_temp)  # dump xml page on host dir
            except Exception as e:
                self.logger.error("Error occured when try to dump screenshot image {}".format(e))
            detected = False
            prepr_text = self.pdetector.preprocess_data(xml_name_file_temp)
            if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:
                probability_privacy_policy = float(self.pdetector.predict(prepr_text))
                detected = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False

            # current_state = self.device.get_current_state().state_str
            if not detected:
                self.logger.info("Home button change the privacy policy page")
                self.home_button_change_page = True

            ##################################### CHECK BACK BUTTONS MECHANISM #####################################

            self.logger.info("Check if the pressing of the BACK button changes the privacy policy page")
            event = KeyEvent(name='BACK')
            input_manager.add_event(event)
            # open app again
            event = IntentEvent(intent=self.app.start_intents[0])
            input_manager.add_event(event)
            time.sleep(3)
            self.device.adb.shell(['uiautomator dump'])
            xml_name_file_temp = os.path.join(dir_app_complete, "{0}.xml".format("temp"))
            try:
                self.device.pull_file("/sdcard/window_dump.xml", xml_name_file_temp)  # dump xml page on host dir
            except Exception as e:
                self.logger.error("Error occured when try to dump screenshot image {}".format(e))
            detected_1 = False
            prepr_text = self.pdetector.preprocess_data(xml_name_file_temp)
            if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:
                probability_privacy_policy = float(self.pdetector.predict(prepr_text))
                detected_1 = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False

            event = self.list_event[-1]
            input_manager.add_event(event)
            time.sleep(3)
            self.device.adb.shell(['uiautomator dump'])
            xml_name_file_temp = os.path.join(dir_app_complete, "{0}.xml".format("temp"))
            try:
                self.device.pull_file("/sdcard/window_dump.xml", xml_name_file_temp)  # dump xml page on host dir
            except Exception as e:
                self.logger.error("Error occured when try to dump screenshot image {}".format(e))
            detected_2 = False
            prepr_text = self.pdetector.preprocess_data(xml_name_file_temp)
            if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:
                probability_privacy_policy = float(self.pdetector.predict(prepr_text))
                detected_2 = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False

            if not detected_1 and not detected_2:
                self.logger.info("Back button change the privacy policy page")
                self.back_button_change_page = True

    @abstractmethod
    def generate_event(self):
        raise NotImplementedError()


class UtgBasedInputPolicy(InputPolicy):
    """
    State-based input policy.
    """

    def __init__(self, device, app, max_actions, timeout_privacy, pdetector: PredictionModel, md5_app: str):
        super().__init__(device, app, max_actions, timeout_privacy, pdetector, md5_app)

        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.last_event = None
        self.last_state = None
        self.utg = UTG(device=device, app=app)

    def generate_event(self):
        # Get current device state.
        self.current_state = self.device.get_current_state()
        if not self.current_state:
            time.sleep(5)
            return KeyEvent(name='BACK')

        self.update_utg()

        event = self.generate_event_based_on_utg()

        self.last_state = self.current_state
        self.last_event = event
        return event

    def update_utg(self):
        self.utg.add_transition(self.last_event, self.last_state, self.current_state)

    @abstractmethod
    def generate_event_based_on_utg(self):
        raise NotImplementedError()


class UtgGreedySearchPolicy(UtgBasedInputPolicy):
    """
    Depth first strategy to explore UI.
    """

    def __init__(self, device, app, max_actions, timeout_privacy, pdetector: PredictionModel, md5_app: str):
        super().__init__(device, app, max_actions, timeout_privacy, pdetector, md5_app)

        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.nav_target = None
        self.nav_num_steps = -1
        self.num_restarts = 0
        self.num_steps_outside = 0
        self.num_nop_actions = 0
        self.num_same_action_in_row = 0
        self.shuffle_actions = False
        self.event_trace = ''
        self.missed_states = set()

    def generate_event_based_on_utg(self):
        self.logger.info('Current state: {0}'.format(self.current_state.state_str))

        if self.current_state.state_str in self.missed_states:
            self.missed_states.remove(self.current_state.state_str)

        if self.current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack.
            start_app_intent = self.app.start_intents[0]

            if self.event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.event_trace.endswith(EVENT_FLAG_START_APP):
                self.num_restarts += 1
                self.logger.info('The app has been restarted {0} times'.format(self.num_restarts))
            else:
                self.num_restarts = 0

            if not self.event_trace.endswith(EVENT_FLAG_START_APP):
                if self.num_restarts >= MAX_NUM_ATTEMPTS:
                    # If the app had been restarted too many times.
                    self.logger.warning('The app has been restarted too many times')
                    return ExitEvent()
                else:
                    # Start the app.
                    self.event_trace += EVENT_FLAG_START_APP
                    self.logger.info('Trying to start the app')
                    return IntentEvent(intent=start_app_intent)

        elif self.current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground.
            self.num_steps_outside += 1

            if self.num_steps_outside >= MAX_NUM_STEPS_OUTSIDE:
                # Kill the contacts app if the analysis gets stuck into it.
                if self.current_state.foreground_activity.startswith('com.android.contacts'):
                    self.logger.info('Got stuck in contacts app, killing it')
                    self.device.adb.shell(['am', 'force-stop', 'com.android.contacts'])

                # If the app has not been in foreground for too long.
                if self.num_steps_outside >= MAX_NUM_STEPS_OUTSIDE_KILL:
                    # Kill the app (it will be restarted).
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(intent=stop_app_intent)
                    self.logger.info('Out of the app, killing it')
                else:
                    # Try to go back.
                    go_back_event = KeyEvent(name='BACK')
                    self.logger.info('Out of the app, trying to go back')

                self.event_trace += EVENT_FLAG_NAVIGATE
                return go_back_event

        else:
            # The app is in foreground.
            self.num_steps_outside = 0

        # Get all possible input events.
        possible_events = self.current_state.get_possible_input()

        # There are no event candidates (maybe the application is still loading). A nop event will be used
        # so that the application can continue loading. If too many nop events are used in sequence, maybe
        # the application is stuck.
        if not possible_events:
            if self.num_nop_actions >= MAX_NUM_ATTEMPTS:
                self.logger.warning('Too many nop actions in sequence, maybe the application is stuck')
            else:
                self.num_nop_actions += 1
                return NopEvent()

        self.num_nop_actions = 0

        # The same action has been executed for too many times, so let's try randomizing the actions.
        if not self.shuffle_actions and self.num_same_action_in_row >= MAX_NUM_ATTEMPTS:
            self.logger.warning('Same action has been executed for too many times, next actions will be shuffled')
            self.shuffle_actions = True

        if self.shuffle_actions:
            edit_text_actions = [input_event for input_event in possible_events
                                 if isinstance(input_event, SetTextEvent)]
            other_actions = [input_event for input_event in possible_events
                             if not isinstance(input_event, SetTextEvent)]

            random.shuffle(other_actions)

            # Edit field actions have precedence.
            possible_events = edit_text_actions + other_actions

        # Depth-first exploration: if all the other events were already explored, try to go back.
        # noinspection PyTypeChecker
        possible_events.append(KeyEvent(name='BACK'))

        # If there is an unexplored event, try that event.
        for input_event in possible_events:
            if not self.utg.is_event_explored(event=input_event, state=self.current_state):
                if self.last_event and input_event and \
                        self.last_event.get_event_str(self.current_state) == \
                        input_event.get_event_str(self.current_state):
                    self.num_same_action_in_row += 1
                else:
                    self.num_same_action_in_row = 0

                self.logger.info('Trying an unexplored event')
                self.event_trace += EVENT_FLAG_EXPLORE
                return input_event

        # If we are here, it means there are no unexplored events for this state. Let's try navigating into another
        # state from where to trigger unexplored events (if any).

        target_state = self.get_nav_target(self.current_state)
        if target_state:
            event_path = self.utg.get_event_path(current_state=self.current_state, target_state=target_state)
            if event_path and len(event_path) > 0:
                if self.last_event and event_path and \
                        self.last_event.get_event_str(self.current_state) == \
                        event_path[0].get_event_str(self.current_state):
                    self.num_same_action_in_row += 1
                else:
                    self.num_same_action_in_row = 0
                self.logger.info('Navigating to {0}, {1} steps left'.format(target_state.state_str, len(event_path)))
                self.event_trace += EVENT_FLAG_NAVIGATE
                return event_path[0]

        # If an exploration target can't be found, stop the app.
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info('Cannot find an exploration target, trying to restart the app')
        self.event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)

    def get_nav_target(self, current_state):
        # If last event is a navigation event.
        if self.nav_target and self.event_trace.endswith(EVENT_FLAG_NAVIGATE):
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.nav_target)
            if event_path and 0 < len(event_path) <= self.nav_num_steps:
                # If last navigation was successful, use current navigation target.
                self.nav_num_steps = len(event_path)
                return self.nav_target
            else:
                # If last navigation failed, add navigation target to missing states.
                self.missed_states.add(self.nav_target.state_str)

        reachable_states = self.utg.get_reachable_states(current_state)

        for state in reachable_states:
            # Only consider foreground states.
            if state.get_app_activity_depth(self.app) != 0:
                continue
            # Do not consider missed states.
            if state.state_str in self.missed_states:
                continue
            # Do not consider explored states.
            if self.utg.is_state_explored(state):
                continue
            self.nav_target = state
            event_path = self.utg.get_event_path(current_state=current_state, target_state=self.nav_target)
            if len(event_path) > 0:
                self.nav_num_steps = len(event_path)
                return state

        self.nav_target = None
        self.nav_num_steps = -1
        return None


class UtgReplayPolicy(InputPolicy):
    """
    Replay an exploration generated by an UTG policy.
    """

    def __init__(self, device, app, max_actions, timeout_privacy, pdetector: PredictionModel, md5_app: str, output_dir):
        super().__init__(device, app, max_actions, timeout_privacy, pdetector, md5_app)

        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        event_dir = os.path.join(output_dir, 'events')

        if not os.path.isdir(event_dir):
            raise NotADirectoryError('"{0}" directory with events to replay does not exist or is not accessible'
                                     .format(event_dir))

        self.event_paths = sorted(map(lambda f: os.path.join(event_dir, f),
                                      filter(lambda f: f.lower().endswith('.json'), os.listdir(event_dir))))

        self.replay_event_skipped = False

        # Skip the first intent used to start the app (already sent by code, so it's not necessary to load it).
        self.event_index = 1

        self.num_replay_attempts = 0
        self.num_nop_actions = 0

    def generate_event(self):
        while self.event_index < len(self.event_paths):
            if self.num_replay_attempts >= MAX_NUM_ATTEMPTS:
                self.logger.error('Exploration event replay retried for too many times')
                return ExitEvent()

            self.num_replay_attempts += 1

            # Get current device state.
            self.current_state = self.device.get_current_state()
            if not self.current_state:
                time.sleep(5)
                self.num_replay_attempts = 0
                return KeyEvent(name='BACK')

            current_event_index = self.event_index
            while current_event_index < len(self.event_paths):
                event_path = self.event_paths[current_event_index]
                with open(event_path, 'r') as f:
                    current_event_index += 1

                    try:
                        event_dict = json.load(f)
                    except Exception as e:
                        self.logger.warning('Unable to load "{0}": {1}'.format(event_path, e))
                        self.replay_event_skipped = True
                        continue

                    if event_dict['start_state'] != self.current_state.state_str:

                        # The current state of the app doesn't match with the start state for replaying the event, maybe
                        # the application is still loading, so try inserting some nop events. If this doesn't work, find
                        # another state in the list of saved states and replay it (some states will be skipped).
                        if self.num_nop_actions >= MAX_NUM_ATTEMPTS:
                            self.logger.warning('Unexpected start state when replaying "{0}", skipping'
                                                .format(event_path))
                            self.replay_event_skipped = True
                            continue
                        else:
                            self.num_replay_attempts = 0
                            self.num_nop_actions += 1
                            return NopEvent()

                    self.logger.info('Replaying event "{0}"'.format(event_path))
                    self.event_index = current_event_index
                    self.num_replay_attempts = 0
                    self.num_nop_actions = 0
                    return InputEvent.from_dict(event_dict['event'])

            time.sleep(EXPLORATION_REPLAY_FAIL_INTERVAL)

        if self.replay_event_skipped:
            self.logger.warning('All exploration events were replayed, however some events have been skipped')
        else:
            self.logger.info('All exploration events were replayed')

        return ExitEvent()
