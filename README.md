# 3PDroid

[![Python Version](https://img.shields.io/badge/Python-3.7.5-green.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3%20%26%20%20Commercial-blue)

**3PDroid** is a Python tool for verifying if an Android app complies with the Google Play privacy guidelines described [here](https://play.google.com/about/privacy-security-deception/). **3PDroid** is based on a combination of static analysis, dynamic analysis, and machine learning techniques to assess if an Android app complies with the Google Play privacy guidelines or not. 

---
## ❱ Publication 
More details about **3PDroid** can be found in the paper "[On the (Un)Reliability of Privacy Policies in Android Apps](https://arxiv.org/abs/2004.08559)"

Please use the following bibtex entry to cite our work:

```BibTex
@InProceedings{3pdroid,
  author = {Luca Verderame and Davide Caputo and Andrea Romdhana and Alessio Merlo},
  title = {On the (Un)Reliability of Privacy Policies in Android Apps},
  booktitle = {Proc. of the IEEE International Joint Conference on Neural Networks (IJCNN 2020)},
  month = {July},
  year = {2020},
  address = {Glasgow, UK}
}
```
---
## ❱ Requirements
- Tested only on Ubuntu 18.04 and Ubuntu 20.04
- Use python 3.7.5
- Install virtualenv
  ```console
  $ pip3 install virtualenv
  ```
- Download [Oracle VirtualBox](https://www.virtualbox.org/)
- Download emulator 
  * [Androidx86](https://www.android-x86.org/releases/releasenote-6-0-r3.html) (recommended) or [Genymotion](https://www.genymotion.com/):
- Setup emulator (if needed)
    * Obtain root permissions (if needed)
    * emulator with nat e forward ports 5555 and 5554
    * emulator with bridged adapter 
    * install droidbot app ([download](https://github.com/honeynet/droidbot/tree/master/droidbot/resources))
- Enable accessibility services
- Add adb path in PATH environment variable
- Download nltk resources
  ```python
  import nltk
  nltk.download("stopwords")
  nltk.download("punkt")
  ```
---
**OPTIONAL**, if you want to use appium and the random modality (default is Droidbot)

- Download appium
  ```console
  $ npm install -g appium
  $ npm install -g appium-doctor
  ```
- Verify appium installation
  ```console
  $ appium-doctor --android
  ```
---

## ❱ Start Analysis
1. Create Virtualenv
  ```console
  $ virtualenv -p python3 venv
  ```
2. Enable Virtualenv
  ```console
  $ source venv/bin/activate
  ```
3. Install Requirements
  ```console
  $ pip install -r requirements
  ```
3. Start Emulator Manager 
  ```console
  $ python3 emulator_manager.py
  ```
4. Move apps to analyze within **apps** dir
5. Start experiments
  ```console
  $ python3 3Pdroid.py -t 10 -m 20 --type Droidbot --emulator-name AndroidEmulator -d \home\user\path\3PDroid\apps
  ```
--- 
## ❱ After Analysis

- Check if the apps with privacy policy contain explicit acceptance or not
  ```console
  $ python3 explicit_acceptance_policy_page.py
  ```
- Update results with some new data and stats
  ```console
  $ python3 update_stats_experiments.py
  ```
- CREvaluator (see  "[On the (Un)Reliability of Privacy Policies in Android Apps](https://arxiv.org/abs/2004.08559)" for more information)
  ```console
  $ python3 CREvaluator.py
  ```

---
## ❱ License

This tool is available under a dual license: a commercial one required for closed source projects or commercial projects, and an AGPL license for open-source projects.

Depending on your needs, you must choose one of them and follow its policies. A detail of the policies and agreements for each license type is available in the [LICENSE.COMMERCIAL](LICENSE.COMMERCIAL) and [LICENSE](LICENSE) files.