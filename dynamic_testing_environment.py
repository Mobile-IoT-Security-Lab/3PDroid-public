#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import os
from droidbot.stimulator import DroidBot
from random_interaction.random_interaction import RandomInteraction
import subprocess
import frida_monitoring
from p3detector.prediction_model import PredictionModel
import json
import sys

if 'LOG_LEVEL' in os.environ:
    log_level = os.environ['LOG_LEVEL']
else:
    log_level = logging.INFO

# Logging configuration.
logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s> [%(levelname)s][%(name)s][%(funcName)s()] %(message)s',
                    datefmt='%d/%m/%Y %H:%M:%S', level=log_level, stream=sys.stdout)


def write_results(result, type_analysis, md5_app, dict_analysis_app):
    file_name = md5_app
    dir_result = os.path.join(os.getcwd(), "logs", file_name)
    if not os.path.exists(dir_result):
        os.makedirs(dir_result)
    md5_privacy_policy_page = result.md5_privacy_policy_page if result.md5_privacy_policy_page != "" else "N.A"
    action_to_remove = 0 if type_analysis == "random" else 1  # -1 to remove intent to start app
    dict_analysis_app["type_analysis"] = type_analysis
    dict_analysis_app["max_actions"] = result.max_actions
    dict_analysis_app["timeout"] = result.timeout_privacy
    dict_analysis_app["privacy_policy_page_detected"] = result.detected
    dict_analysis_app["privacy_policy_page_md5"] = md5_privacy_policy_page
    dict_analysis_app["timeout_privacy_policy_page"] = result.timeout_reached
    dict_analysis_app["home_button_change_privacy_policy_page"] = result.home_button_change_page
    dict_analysis_app["back_button_change_privacy_policy_page"] = result.back_button_change_page
    dict_analysis_app["actions_needed_to_reach_privacy_policy"] = len(result.list_event) - action_to_remove
    with open(os.path.join(dir_result, "{}.json".format(file_name)), "w") as json_file:
        json.dump(dict_analysis_app, json_file, indent=4)
    return dict_analysis_app


def get_cmd_args(args: list = None):
    """
    Parse and return the command line parameters needed for the script execution.
    :param args: List of arguments to be parsed (by default sys.argv is used).
    :return: The command line needed parameters.
    """

    parser = argparse.ArgumentParser(
        prog='python dynamic_testing_environment.py',
        description='Start dynamic testing environment to analyze the app'
    )

    parser.add_argument('-t', '--timeout-privacy', type=int, metavar='TIMEOUT', default=60,
                        help='Timeout to waiting (in seconds) to discover if the privacy page has an expiration')
    parser.add_argument('-m', '--max-actions', type=int, metavar='MAXACTIONS', default=30,
                        help='Maximum actions (in number of events) for the app stimulation')
    parser.add_argument('-a', '--app', type=str, metavar='APP',
                        help='The directory where is the apps')
    parser.add_argument('--type', type=str, metavar='TYPE', default='Droidbot', choices=["random", "Droidbot"],
                        help="The type of app stimulation ")

    return parser.parse_args(args)


def start_analysis(type_analysis: str, app: str, max_actions: int, timeout_privacy: int, pdetector: PredictionModel,
                   md5_app: str = None, frida_monitoring=None, dict_analysis_app: dict = None):
    if type_analysis == "Droidbot":
        logger.info("Start Analysis with Droidbot of {}".format(app))
        droidbot = DroidBot(apk_path=app, timeout=0, max_actions=max_actions,
                            timeout_privacy=timeout_privacy, pdetector=pdetector, md5_app=md5_app)
        if frida_monitoring is not None:
            droidbot.start(frida_monitoring=frida_monitoring)
        else:
            droidbot.start()
        dict_analysis_app = write_results(droidbot.input_manager.policy, "Droidbot", md5_app, dict_analysis_app)
        logger.info("End Analysis with Droidbot of {}".format(app))
        return droidbot.input_manager.policy, dict_analysis_app

    else:
        logger.info("Start Analysis with RandomInteraction of {}".format(app))

        # starting appium
        random_interaction = RandomInteraction(apk_path=app, max_actions=max_actions,
                                               timeout_privacy=timeout_privacy, pdetector=pdetector, md5_app=md5_app)

        # push file to push package.name and hook.json
        if frida_monitoring is not None:
            random_interaction.start(frida_monitoring=frida_monitoring)
        else:
            random_interaction.start()

        dict_analysis_app = write_results(random_interaction, "random", md5_app, dict_analysis_app)
        logger.info("End Analysis with RandomInteraction of {}".format(app))
        return random_interaction, dict_analysis_app


if __name__ == '__main__':
    arguments = get_cmd_args()
    # list_apps = glob.glob(os.path.join(arguments.dir_app, "*.apk"))
    start_analysis(arguments.type, arguments.app, arguments.max_actions, arguments.timeout_privacy)
