import os
import glob
import json
import shutil

if __name__ == '__main__':
    md5_app = glob.glob(os.path.join(os.getcwd(),"cr_evaluator_results","*.json"))
    md5_app = list(map(lambda x: x.rsplit(os.sep, 1)[-1].split(".json")[0], md5_app))

    find_md5_app_no_compliant = []
    for md5 in md5_app:
        path_json_results = os.path.join(os.getcwd(), "logs", md5, f"{md5}.json")
        if os.path.exists(path_json_results):
            results = json.load(open(path_json_results, "r"))
            if "app_is_compliant_with_google_play_store" in results and results["app_is_compliant_with_google_play_store"]:
                find_md5_app_no_compliant.append(md5)

    os.makedirs(os.path.join(os.getcwd(), "app_to_analyze"), exist_ok=True)
    for md5 in find_md5_app_no_compliant:
        shutil.copy(os.path.join(os.getcwd(),"cr_evaluator_results",f"{md5}.json"),os.path.join(os.getcwd(),"app_to_analyze",f"{md5}.json") )

    # TODO da analizzare solo sulle 94 apps (vedi check_cr_evaluator)
