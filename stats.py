import json


class Statistic:

    def __init__(self, type_interaction: str):
        self.list_max_actions = []
        self.type_interaction = type_interaction
        self.apps_with_timeout = 0
        self.apps_privacy_policy_page_detected = 0
        self.apps_with_home_buttons_accepts = 0
        self.apps_with_back_buttons_accepts = 0
        self.stats_permission = {}
        self.stats_trackers = {}
        self.apps_cleaned = 0
        self.apps_not_analyzed = 0
        self.api_privacy_relevant_invoked = []
        self.apps_not_compliant = 0
        self.app_compliant = 0
        self.dict_to_write_stats = {}

    def update_stats_permission(self, list_permissions):
        for permission in list_permissions:
            if permission in self.stats_permission:
                self.stats_permission[permission] += 1
            else:
                self.stats_permission[permission] = 1

    def update_stats_trackers(self, list_trackers):
        for tracker in list_trackers:
            if tracker in self.stats_trackers:
                self.stats_trackers[tracker] += 1
            else:
                self.stats_trackers[tracker] = 1

    def add_api_privacy_relevant_invoked(self, n_api_privacy_relevant):
        self.api_privacy_relevant_invoked.append(n_api_privacy_relevant)

    def add_app_cleaned(self):
        self.apps_cleaned += 1

    def add_app_not_analyzed(self):
        self.apps_not_analyzed += 1

    def add_app_compliant(self):
        self.app_compliant += 1

    def add_app_not_compliant(self):
        self.apps_not_compliant += 1

    def update_value_dynamic_analysis(self, result_app):

        self.apps_with_timeout += 1 if result_app.timeout_reached else 0
        self.apps_privacy_policy_page_detected += 1 if result_app.detected else 0
        self.apps_with_home_buttons_accepts += 1 if result_app.home_button_change_page else 0
        self.apps_with_back_buttons_accepts += 1 if result_app.back_button_change_page else 0

    def write_on_file(self, path_file: str, app_analyzed: int):
        mean_actions = sum(self.list_max_actions) / len(self.list_max_actions) if len(self.list_max_actions) > 0 else 0
        mean_api_privacy_relevant = sum(self.api_privacy_relevant_invoked) / len(self.api_privacy_relevant_invoked) if \
            len(self.api_privacy_relevant_invoked) > 0 else 0
        # len_file_inside = glob.glob(path_file.rsplit("_", 1)[0] + "*")
        # if len_file_inside > 0:
        #    path_file = path_file.replace(".txt", "_" + str(len_file_inside + 1) + ".txt")
        self.dict_to_write_stats = {
            "Apps Analyzed": app_analyzed,
            "Type of Interaction": self.type_interaction,
            "Apps with privacy policy page": self.apps_privacy_policy_page_detected,
            "Apps with timeout mechanism": self.apps_with_timeout,
            "Apps with home button accepts": self.apps_with_home_buttons_accepts,
            "Apps with back button accepts": self.apps_with_back_buttons_accepts,
            "Apps cleaned": self.apps_cleaned,
            "Apps not analyzed": self.apps_not_analyzed,
            "Apps compliant": self.app_compliant,
            "Apps not compliant": self.apps_not_compliant,
            "Mean action to reach privacy policy page": mean_actions,
            "Mean api invoked (privacy relevant)": mean_api_privacy_relevant
        }

        with open(path_file, "w") as stats_file:
            json.dump(self.dict_to_write_stats, stats_file, indent=4)

    def get_dict_to_write_stats(self):
        return str(self.dict_to_write_stats)

    def write_stats_permissions(self, path_file: str):
        key_reorderd = sorted(self.stats_permission, key=self.stats_permission.get, reverse=True)
        dict_reordered = {}
        for k in key_reorderd:
            dict_reordered[k] = self.stats_permission[k]
        with open(path_file, "w") as stats_file:
            json.dump(dict_reordered, stats_file, indent=4)

    def write_stats_trackers(self, path_file: str):
        key_reorderd = sorted(self.stats_trackers, key=self.stats_trackers.get, reverse=True)
        dict_reordered = {}
        for k in key_reorderd:
            dict_reordered[k] = self.stats_trackers[k]
        with open(path_file, "w") as stats_file:
            json.dump(dict_reordered, stats_file, indent=4)
