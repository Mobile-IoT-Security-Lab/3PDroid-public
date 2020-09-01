import os
import json
from tqdm import tqdm
import sys
from loguru import logger
from nltk.tokenize import sent_tokenize
from pickle import load
from langdetect import detect
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from sklearn.svm import LinearSVC, SVC
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from nltk import ngrams

logger.remove()
logger.add(sys.stdout, level="INFO")
def start_cr_evaluator():
    path_to_store_result = os.path.join(os.getcwd(), "cr_evaluator_results")
    os.makedirs(path_to_store_result, exist_ok=True)

    logger.info("Start Analysis to find all privacy policy page without explicit acceptance")
    # All dir inside log directory
    path_log = os.path.join(os.getcwd(), "logs")
    dir_inside_log = [x[0] for x in os.walk(path_log)]
    dir_inside_log.pop(0)
    logger.info("Load ML Model for each practices and performed_not_performed and third_party_first_party")
    file_json_configuration_model = os.path.join(os.getcwd(), "resources", "cr_evaluator_model",
                                                 "configuration_cr_evaluator.json")
    dict_model_name_path = json.load(open(file_json_configuration_model, "r"))

    for key, item in dict_model_name_path.items():
        item["model"] = load(open(os.path.join(os.getcwd(), item["path_model"]), "rb"))

    dict_md5_app_privacy_policy_page = {}

    for dir_app in tqdm(dir_inside_log, file=sys.stdout):
        md5_app = dir_app.split(os.sep)[-1]
        json_file = os.path.join(dir_app, f"{md5_app}.json")

        if os.path.exists(json_file):
            analysis_json = json.load(open(json_file))

            if "privacy_policy_page_detected" in analysis_json and analysis_json["privacy_policy_page_detected"]:
                md5_privacy_policy_page = analysis_json["privacy_policy_page_md5"]

                dict_md5_app_privacy_policy_page[md5_app] = {
                    "md5_privacy_policy_page": md5_privacy_policy_page,
                    "content_xml_privacy_policy_page": "",
                    "content_cleaned_privacy_policy_page": ""
                }

                ################################### LOAD CONTENT PRIVACY POLICY PAGE ###################################

                dir_privacy_policy_page = os.path.join(os.getcwd(), "privacypoliciesxml")
                file_name_xml = os.path.join(dir_privacy_policy_page, f"{md5_app}_{md5_privacy_policy_page}.xml")
                file_name_cleaned = os.path.join(dir_privacy_policy_page,
                                                 f"{md5_app}_{md5_privacy_policy_page}_cleaned.txt")
                content_file_xml = ""
                content_cleaned_privacy_policy_page = ""

                if os.path.exists(file_name_xml):
                    file_object = open(file_name_xml, "r", encoding="utf-8", errors='ignore')
                    content_file_xml = file_object.read()
                    file_object.close()
                if os.path.exists(file_name_cleaned):
                    file_object = open(file_name_cleaned, "r", encoding="utf-8", errors='ignore')
                    content_cleaned_privacy_policy_page = file_object.read()
                    file_object.close()
                dict_md5_app_privacy_policy_page[md5_app]["content_xml_privacy_policy_page"] = content_file_xml
                dict_md5_app_privacy_policy_page[md5_app][
                    "content_cleaned_privacy_policy_page"] = content_cleaned_privacy_policy_page

                ################################### ANALYZE THE CONTENT ###################################

                # 1) Divide the privacy policy page content in sentences
                # 2) Detect if PP is in english language
                # 3) Detect if at least one privacy relevant information is treated
                # 4) Detect if the relevant information is performed or not
                # 5) Detetct if the relevant information is third party or not
                # recovery model
                logger.debug("Start ML Detection")
                language = detect(dict_md5_app_privacy_policy_page[md5_app]["content_cleaned_privacy_policy_page"])
                logger.debug(f"The language of text is {language}")
                dict_result_cr_evaluator = {
                    "md5_app": f"{md5_app}",
                    "md5_privacy_policy": f"{dict_md5_app_privacy_policy_page[md5_app]['md5_privacy_policy_page']}",
                    "language": language,
                    "number_of_sentences": "",
                    "list_sentences": [],
                    "analysis_sentence": [],
                    # "privacy_information_performed_or_not": [],
                    # "privacy_information_first_party_third_party": [],
                    "permission_requested": analysis_json["permission_requested"],
                    "trackers_inside": analysis_json["trackers_inside"],
                    "policy_page_compliant": []
                }
                if language == "en":
                    list_sentences = sent_tokenize(
                        dict_md5_app_privacy_policy_page[md5_app]["content_cleaned_privacy_policy_page"],
                        language="english"
                    )

                    use_list_filtered = False
                    use_ngrams = True
                    if use_list_filtered:
                        list_sentences_filtered = list(filter(lambda sentence: len(sentence.split(" ")) > 5, list_sentences))

                    elif use_ngrams:
                        n = 2
                        ngrams_list_of_tuple = ngrams(list_sentences, n)
                        list_sentences_filtered = [" ".join(grams) for grams in ngrams_list_of_tuple ]

                    else:
                        list_sentences_filtered = list_sentences

                    dict_result_cr_evaluator["list_sentences"] = list_sentences_filtered
                    dict_result_cr_evaluator["number_of_sentences"] = len(list_sentences_filtered)
                    logger.debug(f"The text is composed by {len(list_sentences_filtered)} sentences")
                    for sentence in list_sentences_filtered:
                        logger.debug(f"Analyzing: {sentence}")
                        privacy_information_single_sentence = []
                        dict_analysis_sentence = {
                            "sentence": sentence,
                            "privacy_information": [],
                            "privacy_information_performed_or_not": "",
                            "privacy_information_first_party_third_party": ""
                        }
                        for key, model_dict in dict_model_name_path.items():
                            if key not in ["performed_not_performed", "third_party_first_party"]:
                                # here use the model
                                model_actual = model_dict["model"]
                                predict = model_actual.predict([sentence])
                                if f"performed_{key}" == predict[0]:
                                    logger.debug(f"In the actual sentence the {predict[0]} is treated")
                                    privacy_information_single_sentence.append(f"{key}")

                        if len(privacy_information_single_sentence) > 0:

                            # Store results
                            dict_analysis_sentence["privacy_information"].append(privacy_information_single_sentence)
                            # performed not performed
                            model_performed_not_performed = dict_model_name_path["performed_not_performed"]["model"]
                            predict_performed = model_performed_not_performed.predict([sentence])
                            logger.debug(f"The privacy information is {predict_performed[0]} in this sentence")
                            dict_analysis_sentence["privacy_information_performed_or_not"] = predict_performed[0]

                            # first or third party
                            model_third_party_first_party = dict_model_name_path["third_party_first_party"]["model"]
                            predict_third_party_first_party = model_third_party_first_party.predict([sentence])
                            logger.debug(
                                f"The privacy information is {predict_performed[0]} by {predict_third_party_first_party[0]}")
                            dict_analysis_sentence["privacy_information_first_party_third_party"] = predict_third_party_first_party[0]
                            dict_result_cr_evaluator["analysis_sentence"].append(dict_analysis_sentence)
                        else:
                            logger.debug("The actual sentence is cleaned")
                            dict_analysis_sentence["privacy_information"].append(None)
                            dict_analysis_sentence["privacy_information_performed_or_not"] = None
                            dict_analysis_sentence["privacy_information_first_party_third_party"] = None
                            dict_result_cr_evaluator["analysis_sentence"].append(dict_analysis_sentence)

                json.dump(dict_result_cr_evaluator, open(os.path.join(path_to_store_result, f"{md5_app}.json"), "w"),
                          indent=4)


if __name__ == "__main__":
    start_cr_evaluator()
