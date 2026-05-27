# ROS2 Latency Measurement - Python

## COPY PASTE WAT ER HIERONDER STAAT OM ALLES IN 1 KEER TE DOEN
- git clone https://github.com/HDENBSXHZU/versie_1
- cd versie_1
- python3 -m venv venv
- source venv/bin/activate
- pip install -r requirements.txt
- source /opt/ros/jazzy/setup.bash

## Gebruik
# VM3 - receiver starten
python3 receiver_upgrade.py --topic chatter1

- VM1 - publisher starten
python3 publisher_upgrade.py --topic chatter1 --start-hz 100 --delta-hz 100 --max-hz 1300

- VM3 - grafiek genereren
python3 createGraphs_upgrade.py --input latency_results.csv
