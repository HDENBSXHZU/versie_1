"""
receiver_upgrade.py
===================
Draait op VM3.

Ontvangt berichten van publisher_upgrade.py en berekent per blok:
  - Gemiddelde latentie, std, min, max
  - Pakketverlies via volgnummers
  - Gemiddeld CPU-gebruik via psutil
  - Gemiddeld geheugengebruik via psutil

Berichtformaat: VOLGNUMMER|HZ|VERZENDTIJD_US
Stopbericht:    STOP|TOTAAL

Installatie psutil:
  pip3 install psutil --break-system-packages

CSV kolommen:
  topic, hz, block_nr,
  verstuurd, ontvangen, berichten_verloren, pct_ontvangen,
  avg_latency_ms, std_latency_ms, min_latency_ms, max_latency_ms,
  cpu_percent, mem_mb

Gebruik:
  python3 receiver_upgrade.py --topic chatter1
  python3 receiver_upgrade.py --topic chatter1 --output meting.csv
"""

import argparse
import csv
import math
import os
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

try:
    import psutil
    psutil.cpu_percent(interval=None)  # initialiseer zodat eerste meting correct is
    HEEFT_PSUTIL = True
except ImportError:
    HEEFT_PSUTIL = False
    print("[receiver] psutil niet gevonden — pip3 install psutil --break-system-packages")


KOLOMMEN = [
    "topic", "hz", "block_nr",
    "verstuurd", "ontvangen", "berichten_verloren", "pct_ontvangen",
    "avg_latency_ms", "std_latency_ms", "min_latency_ms", "max_latency_ms",
    "cpu_percent", "mem_mb",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--topic",  type=str, default="chatter1")
    p.add_argument("--output", type=str, default="latency_results.csv")
    return p.parse_args()


class Receiver(Node):

    def __init__(self, topic, output):
        super().__init__("receiver")

        self.topic = topic

        # Blok data
        self.hz_huidig  = None
        self.eerste_nr  = None
        self.laatste_nr = None
        self.latencies  = []
        self.blok_nr    = 0

        # CPU en geheugen samples
        self.cpu_s = []
        self.mem_s = []

        # CSV
        nieuw = not os.path.isfile(output)
        self._f      = open(output, "a", newline="", buffering=1)
        self._writer = csv.DictWriter(self._f, fieldnames=KOLOMMEN)
        if nieuw:
            self._writer.writeheader()
            self._f.flush()

        self.create_subscription(String, topic, self._ontvang, 1000)

        self.get_logger().info(f"Receiver gestart | /{topic} -> '{output}'")
        if HEEFT_PSUTIL:
            self.get_logger().info("psutil actief — CPU en geheugen worden gemeten")
        else:
            self.get_logger().warning("psutil niet beschikbaar")

    def _meet(self):
        """Voeg een CPU- en geheugensample toe."""
        if not HEEFT_PSUTIL:
            return
        self.cpu_s.append(psutil.cpu_percent(interval=None))
        self.mem_s.append(psutil.virtual_memory().used / 1_048_576)

    def _sluit_blok(self):
        """Bereken statistieken en schrijf naar CSV."""
        n = len(self.latencies)
        if n == 0:
            return

        verstuurd = self.laatste_nr - self.eerste_nr + 1
        verloren  = max(0, verstuurd - n)
        pct       = n / verstuurd * 100 if verstuurd > 0 else 0.0

        gem = sum(self.latencies) / n
        var = sum((x - gem) ** 2 for x in self.latencies) / n
        std = math.sqrt(var)
        mn  = min(self.latencies)
        mx  = max(self.latencies)

        gem_cpu = sum(self.cpu_s) / len(self.cpu_s) if self.cpu_s else 0.0
        gem_mem = sum(self.mem_s) / len(self.mem_s) if self.mem_s else 0.0

        self._writer.writerow({
            "topic":              self.topic,
            "hz":                 f"{self.hz_huidig:.1f}",
            "block_nr":           self.blok_nr,
            "verstuurd":          verstuurd,
            "ontvangen":          n,
            "berichten_verloren": verloren,
            "pct_ontvangen":      f"{pct:.2f}",
            "avg_latency_ms":     f"{gem:.4f}",
            "std_latency_ms":     f"{std:.4f}",
            "min_latency_ms":     f"{mn:.4f}",
            "max_latency_ms":     f"{mx:.4f}",
            "cpu_percent":        f"{gem_cpu:.2f}",
            "mem_mb":             f"{gem_mem:.1f}",
        })
        self._f.flush()

        self.get_logger().info(
            f"Blok {self.blok_nr:3d} | {self.hz_huidig:8.0f}hz | "
            f"verstuurd={verstuurd} ontvangen={n} verloren={verloren} ({pct:.1f}%) | "
            f"gem={gem:.3f}ms std={std:.3f}ms min={mn:.3f}ms max={mx:.3f}ms | "
            f"cpu={gem_cpu:.1f}% mem={gem_mem:.0f}MB"
        )

        # Reset
        self.latencies = []
        self.cpu_s     = []
        self.mem_s     = []
        self.blok_nr  += 1

    def _ontvang(self, msg: String):
        ontvangst_us = time.time_ns() // 1000
        self._meet()

        data = msg.data

        # Stopbericht
        if data.startswith("STOP|"):
            self.get_logger().info("Stopbericht ontvangen — laatste blok afsluiten.")
            self._sluit_blok()
            self._f.close()
            rclpy.shutdown()
            return

        # Parsen: VOLGNUMMER|HZ|VERZENDTIJD_US
        try:
            delen = data.split("|")
            if len(delen) < 3:
                return
            volgnummer  = int(delen[0])
            hz          = float(delen[1])
            verzendtijd = int(delen[2])
        except (ValueError, IndexError):
            return

        latentie_ms = (ontvangst_us - verzendtijd) / 1000.0
        if latentie_ms < 0 or latentie_ms > 10_000:
            return

        # Nieuw blok als hz verandert
        if self.hz_huidig is None:
            self.hz_huidig  = hz
            self.eerste_nr  = volgnummer
            self.laatste_nr = volgnummer
        elif hz != self.hz_huidig:
            self._sluit_blok()
            self.hz_huidig  = hz
            self.eerste_nr  = volgnummer
            self.laatste_nr = volgnummer

        self.latencies.append(latentie_ms)
        if volgnummer > self.laatste_nr:
            self.laatste_nr = volgnummer

    def destroy_node(self):
        if self.latencies:
            print(f"[receiver] Laatste blok wegschrijven ({self.hz_huidig:.0f}hz)...")
            self._sluit_blok()
        if not self._f.closed:
            self._f.close()
        super().destroy_node()


def main():
    args = parse_args()
    rclpy.init()
    node = Receiver(topic=args.topic, output=args.output)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
