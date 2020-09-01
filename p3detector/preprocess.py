import os
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


class Preprocess:

    @staticmethod
    def preprocess_and_write_dataset(path):
        files = []
        path = os.path.join(os.getcwd(), path)
        for r, d, f in os.walk(path):
            for file in f:
                if '.txt' in file:
                    files.append(os.path.join(r, file))
        count = 0
        for file in files:
            f = open(file)
            soup = BeautifulSoup(f)

            # CCleaner B|
            for script in soup(['a', 'i', 'head', 'title', 'footer', 'iframe', 'br',
                                'img', 'input', 'script', 'style', 'option', 'link']):
                script.extract()
            text = soup.get_text()
            text = text.replace('\n', ' ')
            text = text.replace('\t', ' ')
            text = " ".join(text.split())
            text.encode('ascii', errors='ignore').decode()
            temp_file = open(os.path.join(os.getcwd(), 'dataset_clear/not_policies_clear', '') + str(count) + '.txt',
                             'a+')
            temp_file.write(text)
            temp_file.close()
            f.close()
            count = count + 1

    @staticmethod
    def preprocess_xml(path):
        assert type(path) == str, 'PD DAVIDE, UNA STRING IN INGRESSO, VERRAI INVESTITO DA UN PELATO '
        tree = ET.parse(path)
        # Obtaining the text
        xml_text = ""
        for elem in tree.iter():
            try:
                xml_text = xml_text + ' ' + str(elem.attrib['text']) + str(elem.attrib['content-desc'])
            except:
                pass
        xml_text = xml_text.replace('\n', ' ')
        xml_text = xml_text.replace('\t', ' ')
        xml_text = " ".join(xml_text.split())
        xml_text.encode('ascii', errors='ignore').decode()
        return [str(xml_text)]

    @staticmethod
    def preprocess_page(complete_path):
        assert type(complete_path) == str, 'PD DAVIDE, UNA STRING IN INGRESSO, VERRAI INVESTITO DA UN PELATO '
        file = open(complete_path, 'r')
        soup = BeautifulSoup(file)
        for script in soup(['a', 'i', 'head', 'title', 'footer', 'iframe', 'br',
                            'img', 'input', 'script', 'style', 'option', 'link']):
            script.extract()
        text = soup.get_text()
        text = text.replace('\n', ' ')
        text = text.replace('\t', ' ')
        text = " ".join(text.split())
        text.encode('ascii', errors='ignore').decode()
        file.close()
        return [str(text)]
