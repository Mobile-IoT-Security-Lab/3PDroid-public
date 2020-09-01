import os
import random_interaction.generic_application_env as generic
from androguard.core.bytecodes import apk
from selenium.common.exceptions import WebDriverException
import hashlib
import logging
import time
import frida_monitoring
from p3detector.prediction_model import PredictionModel

HOME_BUTTON = 82
BACK_BUTTON = 4
MEAN_WORD_POLICY = 10
TRESHOLD_PROBABILITY_PP = 0.1


class RandomInteraction:
    def __init__(self, apk_path: str, max_actions: int = 30, timeout_privacy: int = 60, time_between_action: int = 2,
                 pdetector: PredictionModel = None, md5_app: str = None):
        self.logger = logging.getLogger('{0}.{1}'.format(__name__, self.__class__.__name__))

        if not os.path.isfile(apk_path):
            raise FileNotFoundError('The input application file "{0}" was not found'.format(apk_path))

        self.apk_path = apk_path
        self.timeout_reached = False
        self.max_actions = max_actions
        self.timeout_privacy = timeout_privacy
        self.activities = []
        self.application_dict = {}
        self.app_generic_environment = None
        self.package_name = ""
        self.list_event = []
        self.list_page_visited = []
        self.detected = False
        self.md5_privacy_policy_page = ""
        self.timeout_reached = False
        self.home_button_change_page = False
        self.back_button_change_page = False
        self.time_between_action = time_between_action
        self.pdetector = pdetector
        self.md5_app = md5_app

    def start(self, frida_monitoring=None):

        self.logger.info("Starting RandomInteraction wit the app {} ".format(self.apk_path))
        self.md5_app = self.md5_app
        # Trying to retrieve package information and the associated activities
        try:
            a = apk.APK(self.apk_path)
            self.package_name = a.get_package()
            raw_activities = a.get_activities()
            # Adding activities into dictionary, freed from the package prefix
            for index, _ in enumerate(raw_activities):
                if self.package_name in raw_activities[index]:
                    self.activities.append(raw_activities[index].replace(self.package_name, ''))
                    self.application_dict.update({self.activities[-1]: {'exported': False, 'visited': False}})
        except Exception as e:
            self.logger.error(e)
        try:
            self.app_generic_environment = generic.GenericApplicationEnv(self.application_dict,
                                                                         app=self.apk_path,
                                                                         appPackage=self.package_name)
            if frida_monitoring is not None:
                path_file_monitoring = os.path.join(os.getcwd(), "hook", self.md5_app,
                                                    "frida_api.txt")
                # to do 
                frida_monitoring.start(self.package_name, 0, path_file_monitoring)

            dir_app = self.md5_app
            dir_app_complete = os.path.join(os.getcwd(), "xml_dump", dir_app)
            if not os.path.exists(dir_app_complete):
                os.makedirs(dir_app_complete)
            while len(self.list_event) < self.max_actions and not self.detected:
                activity = self.app_generic_environment.driver.current_activity
                self.logger.info("Current Activity {}".format(activity))
                source_xml = self.app_generic_environment.driver.page_source
                md5_source_xml = hashlib.md5(source_xml.encode('utf-8')).hexdigest()

                if md5_source_xml not in self.list_page_visited:
                    self.logger.info("New page Found --> we need detect if it contains policy page or not")
                    xml_name_file = os.path.join(dir_app_complete, "{0}.xml".format(md5_source_xml))
                    file_output = open(xml_name_file, "w",
                                       encoding="utf-8")
                    file_output.write(source_xml)
                    file_output.close()
                    self.list_page_visited.append(md5_source_xml)

                    prepr_text = self.pdetector.preprocess_data(xml_name_file)
                    self.logger.info(prepr_text)
                    # self.logger.info(prepr_text[0].split(" "), len(prepr_text[0].split(" ")))
                    if len(prepr_text[0].split(" ")) > MEAN_WORD_POLICY:
                        self.logger.info(
                            "Page with more than {} words, check if it is privacy policy page or not ".format(
                                MEAN_WORD_POLICY))
                        probability_privacy_policy = float(self.pdetector.predict(prepr_text))
                        self.logger.info("The current page is privacy policy page with {0:.2f}% of probability ".format(
                            (1 - probability_privacy_policy) * 100))

                        self.detected = True if probability_privacy_policy < TRESHOLD_PROBABILITY_PP else False
                    else:
                        self.logger.info("The current page has less than {} word, so it is not a privacy policy page ".
                                         format(MEAN_WORD_POLICY))

                        self.detected = False

                    if self.detected:
                        self.md5_privacy_policy_page = md5_source_xml

                    else:
                        action = self.app_generic_environment.action_space.sample()
                        self.app_generic_environment.step(action)
                        self.list_event.append(action)

                else:
                    self.logger.info("Old page, we have already analyzed it")
                    action = self.app_generic_environment.action_space.sample()
                    self.app_generic_environment.step(action)
                    self.list_event.append(action)

            if self.detected:
                self.logger.info("Privacy Policy Page detected")
                #  1) we need to detect if the privacy page contains explicit acceptance
                # ToDO

                #  2) add timeout check,
                self.logger.info("Check if the app has a timeout mechanism for the privacy policy")
                time.sleep(self.timeout_privacy)
                source_xml = self.app_generic_environment.driver.page_source
                md5_source_xml = hashlib.md5(source_xml.encode('utf-8')).hexdigest()

                if md5_source_xml != self.md5_privacy_policy_page:
                    self.logger.info("The app has a timeout mechanism")
                    self.timeout_reached = True
                else:
                    self.logger.info("The privacy policy is still there")

                # HOME BUTTON
                self.logger.info("Check if the pressing of the HOME button changes the privacy policy page")
                self.app_generic_environment.driver.press_keycode(HOME_BUTTON)
                time.sleep(self.time_between_action)
                self.app_generic_environment.driver.launch_app()
                time.sleep(self.time_between_action)
                source_xml = self.app_generic_environment.driver.page_source
                md5_source_xml = hashlib.md5(source_xml.encode('utf-8')).hexdigest()
                if md5_source_xml != self.md5_privacy_policy_page:
                    self.logger.info("Home button change the privacy policy page")
                    self.home_button_change_page = True

                # BACK BUTTON
                self.logger.info("Check if the pressing of the BACK button changes the privacy policy page")
                self.app_generic_environment.driver.press_keycode(BACK_BUTTON)
                time.sleep(self.time_between_action)
                self.app_generic_environment.driver.launch_app()
                time.sleep(self.time_between_action)
                # check that the page of privacy policies is still there
                source_xml_1 = self.app_generic_environment.driver.page_source
                md5_source_xml_1 = hashlib.md5(source_xml_1.encode('utf-8')).hexdigest()
                # now perform last action
                self.app_generic_environment.step(self.list_event[-1])
                time.sleep(self.time_between_action)
                source_xml = self.app_generic_environment.driver.page_source
                md5_source_xml = hashlib.md5(source_xml.encode('utf-8')).hexdigest()

                if md5_source_xml != self.md5_privacy_policy_page or md5_source_xml_1 != self.md5_privacy_policy_page:
                    self.logger.info("Back button change the privacy policy page")
                    self.back_button_change_page = True

            self.app_generic_environment.driver.quit()

        except WebDriverException as e:
            self.logger.error(str(e.msg))

