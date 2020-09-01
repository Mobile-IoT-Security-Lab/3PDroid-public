#x-terminal-emulator -e "bash -c 'echo -e \"\033[1m\nThis terminal runs the emulator manager script on the host machine\n\n\033[0m\" && \
#                      source venv/bin/activate && python3 emulator_manager.py || read -rsn1 -p \"Press any key to exit\"'"


echo "START 3PDroid Analysis"
# source venv/bin/activate
PATH=$PATH:/home/dave/Android/Sdk/platform-tools/adb python3 3PDroid.py -t 10 -m 20 -d /home/approver/3PDroid/apps --type Droidbot --emulator-name AndroidEmulator | tee -a output_anlysis.log