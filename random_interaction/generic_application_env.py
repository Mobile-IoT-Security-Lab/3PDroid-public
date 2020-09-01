import gym
import os
import numpy
import time
from multiprocessing import Process, Queue
from appium import webdriver
import string
import random
from gym import spaces
from datetime import datetime
import xml.etree.ElementTree as ET
import logging


class GenericApplicationEnv(gym.Env):

    # Appium configuration parameters
    def __init__(self, application_dict, app, appPackage='', appActivity='', register_sequence=True):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        self.register_sequence = register_sequence
        if self.register_sequence:
            # Generating a queue to communicate this the writing process
            self.queue = Queue()
            self.queue.put(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + '\n')
            self.queue.put('Current Application: ' + app + 'Current Activity: ' + appActivity + '\n')
            # Generating a process that runs in parallel
            # sequence_process = Process(name='register_sequence', target=register_sequence_process, args=(self.queue,))
            # sequence_process.daemon = True
            # sequence_process.start()

        desired_caps = {'platformName': '',
                         'platformVersion': '',
                         'udid': '',
                         'deviceName': '',
                         'app': app,
                         'appPackage': appPackage,
                         'appActivity': appActivity,
                         'isHeadless': ''}

        # Desired capabilities, the must reflect the emulator/smartphone used see gitHub for more information
        with open(os.path.join(os.getcwd(), "random_interaction", "config.txt")) as f:
            for line in f:
                (key, val) = line.split(' ', 1)
                try:
                    if key == 'isHeadless':
                        if val == 'True':
                            desired_caps[key] = True
                        elif val == 'False':
                            desired_caps[key] = False
                    else:
                        desired_caps[key] = val.rsplit('\n')[0]
                except KeyError:
                    self.logger.error('Wrong File Format')
                    exit(1)

        self.logger.info(desired_caps)

        # after this the app is installed
        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        # Finding all clickable elements
        self.return_clickable_elements()
        # Obtaining current Activity
        self.current_activity = self.driver.current_activity
        # Obtaining reference to external dictionary
        self.application_dict = application_dict
        # Adding each button in self.buttons into the dictionary
        self.add_buttons_to_dictionary()
        # self.driver.implicitly_wait(5000)
        # Defining Gym Spaces
        self.action_space = spaces.Discrete(len(self.buttons))
        # self.observation_space = spaces.MultiDiscrete([9, 9, 18])

    def step(self, action_number):

        # Some issue can occur with views (disappearing elements, slow page loading etc.), try statement is useful to
        # not stop the execution flow
        try:
            attribute = self.buttons[action_number].get_attribute('resource-id')
            if attribute is not None:
                # We save in dictionary only buttons with a resource-id associated
                self.update_button_value_dictionary(attribute)
            # We save the action in queue
            if self.register_sequence:
                self.register(action_number, attribute)

            if self.buttons[action_number].get_attribute('className') != 'android.widget.EditText':
                self.buttons[action_number].click()
                # update buttons
            else:
                r_string = self.generate_random_string()
                # prima del sendKeys bisognerebbe inserire il click sul campo ?
                self.buttons[action_number].send_keys(r_string)
                # update buttons
                if self.register_sequence:
                    self.queue.put('string :' + r_string + '\n')
        except Exception as e:
            self.logger.error(str(e))
        # Useful to let the page load
        time.sleep(1.5)
        # Updates self.current_activity and updates buttons
        self.check_activity()

    def update_buttons(self):
        try:
            self.return_clickable_elements()
            # Updating action space dimension
            self.action_space.n = len(self.buttons)
            '''
            if self.action_space.n == 0:
                # retry until we have buttons
                self.update_buttons()
            '''
        except Exception as e:
            self.logger.error(e)

    def get_action_space(self):
        return self.action_space.n

    def generate_random_string(self):
        func_select = numpy.random.randint(0, 2)
        n = numpy.random.randint(1, 9)
        if func_select == 0:
            # numbers + letters
            return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))
        elif func_select == 1:
            # numbers
            return ''.join(random.choices(string.digits, k=n))
        elif func_select == 2:
            # letters
            return ''.join(random.choices(string.ascii_lowercase, k=n))

    def return_clickable_elements(self):
        # Searching for clickable elements in XML/HTML source page
        tree = ET.fromstring(self.driver.page_source)
        elements = tree.findall(".//*[@clickable='true']")
        # Obtaining the related classes
        tags = list(set([element.tag for element in elements]))
        self.buttons = []
        # Appending all buttons
        for class_name in tags:
            buttons = self.driver.find_elements_by_class_name(class_name)
            # Conversion to list
            buttons = buttons if type(buttons) == list else [buttons]
            self.buttons = self.buttons + buttons

    def check_activity(self):
        # Updating current activity
        if self.current_activity != self.driver.current_activity:
            self.current_activity = self.driver.current_activity
            if self.current_activity == '.Launcher':
                self.logger.info('An error occurred, Relaunching Application ...')
                if self.register_sequence:
                    self.queue.put(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + '\n')
                    self.queue.put('An error occurred, Relaunching Application ...\n')
                self.reset()
        try:
            self.application_dict[self.current_activity].update({'visited': True})
            self.logger.info(self.current_activity)
        except KeyError:
            self.application_dict.update(
                {self.current_activity: {'visited': True, 'possible-external-activity': True}})
        # Updating buttons
        self.update_buttons()

    def register(self, action_number, attribute):
        if attribute is None:
            attribute = self.buttons[action_number].get_attribute('className')
        # SAving actual action
        self.queue.put('action: ' + attribute + ' Activity: ' + str(self.driver.current_activity) + '\n')

    def update_button_value_dictionary(self, attribute):
        self.application_dict[self.current_activity].update({attribute: True})

    def add_buttons_to_dictionary(self):
        try:
            for item in self.buttons:
                attribute = item.get_attribute('resource-id')
                if attribute is not None:
                    self.application_dict[self.current_activity].update({attribute: False})
        except Exception as e:
            self.logger.error(e)

    def reset(self):
        self.driver.reset()
        self.update_buttons()
        return [0, 0, 0]
