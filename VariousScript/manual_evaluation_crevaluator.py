import os
import glob
import json

if __name__ == '__main__':

    mapping_practices_permission = json.load(
        open(os.path.join(os.getcwd(), "resources", "cr_evaluator_model", "mapping_practices_permissions.json"),"r"))
    list_md5_app = glob.glob(os.path.join(os.getcwd(), "cr_to_manual_analyze", "*.json"))
    dict_result_app = dict()

    for path_app in list_md5_app:
        json_result_md5 = json.load(open(path_app, "r"))
        list_permissions = json_result_md5["permission_requested"]
        md5_app = path_app.rsplit(os.sep, 1)[-1].split(".json")[0]
        dict_result_app[md5_app] = {}
        print(md5_app)
        result_md5 = {}
        for permission in list_permissions:
            result_md5["list_sentences"] = json_result_md5["list_sentences"]
            result_md5[permission] = []
            for key, value in mapping_practices_permission.items():

                if permission in value:

                    analysis_sentences = json_result_md5["analysis_sentence"]

                    for sentence in analysis_sentences:

                        if sentence["privacy_information_performed_or_not"] == "performed" and \
                                key in sentence["privacy_information"][0]:
                            result_md5[permission].append(f"{key} PERF")

                        elif sentence["privacy_information_performed_or_not"] == "not_performed" and \
                                key in sentence["privacy_information"][0]:
                            result_md5[permission].append(f"{key} NP")

                        else:
                            result_md5[permission].append(f"{key} NIL")
            dict_result_app[md5_app] = result_md5

    json.dump(dict_result_app, open(os.path.join(os.getcwd(),"cr_to_manual_analyze", "results.json"),"w"), indent=4)
