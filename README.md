# ROS2 Latency Measurement - Python

## Vereisten
- ROS2 Jazzy
- Ubuntu 24.04
- Python 3

## Installatie
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Gebruik
# VM3 - receiver starten
python3 receiver_upgrade.py --topic chatter1

# VM1 - publisher starten
python3 publisher_upgrade.py --topic chatter1 --start-hz 100 --delta-hz 100 --max-hz 1300

# VM3 - grafiek genereren
python3 createGraphs_upgrade.py --input latency_results.csv
