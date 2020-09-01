import os
import xml.dom.minidom
from tqdm import tqdm


def pretty_xml_print(list_of_files: list):
    for index in tqdm(range(0, len(list_of_files))):
        file_name = list_of_files[index]
        if file_name.endswith(".xml"):
            try:
                dom = xml.dom.minidom.parse(file_name)
                file_object = open(file_name, "w")
                file_object.write(dom.toprettyxml())
                file_object.close()
            except Exception:
                pass


if __name__ == "__main__":
    dir_name = os.path.join(os.getcwd(), "xml_dump")
    list_of_files = list()
    for (dirpath, dirnames, filenames) in os.walk(dir_name):
        list_of_files += [os.path.join(dirpath, file) for file in filenames]

    pretty_xml_print(list_of_files)

    dir_name = os.path.join(os.getcwd(), "privacypoliciesxml")
    list_of_files = list()
    for (dirpath, dirnames, filenames) in os.walk(dir_name):
        list_of_files += [os.path.join(dirpath, file) for file in filenames]

    pretty_xml_print(list_of_files)
