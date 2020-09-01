# Random-Interaction-Appium

This tool allows to randomly interact with unknown Android applications. 
 
# Requirements

- Appium (Desktop or command line version)

- Android Emulator or Android Smartphone

- Install the Python packages:

``` pip3 install -r requirements.txt```

- Configure the file ```config.txt``` inserting the informations about you device in the following way (i.e.):

```
platformName Android
platformVersion 7.0
udid emulator-5554
deviceName Pixel API 24
isHeadless True
```


# Usage

- Launch Appium server

- Launch the Emulator using the command:

```emulator @device_name``` 

Add the flag if you want to run it in headless mode:

```no-window```

- Now you can launch ```Random-Interaction-Appium``` using the command:

``` python3 random_interaction.py```

Add the flag ```--activities```to sequentially launch all activities in the application

# Known problems

Androguard supports only API 28 or below

