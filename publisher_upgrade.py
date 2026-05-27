"""
publisher_upgrade.py
====================
Draait op VM1.

Verstuurt berichten op stijgende frequentie.
Elk blok duurt exact 1 seconde — bij 1000hz worden 1000 berichten
verstuurd in 1 seconde, bij 2000hz worden 2000 berichten verstuurd
in 1 seconde, enzovoort.

Het precieze timing gebeurt via een busy-wait lus op basis van
time.perf_counter() zodat elk bericht op het juiste moment verstuurd wordt.

Berichtformaat: VOLGNUMMER|HZ|VERZENDTIJD_US
Stopbericht:    STOP|TOTAAL

Gebruik:
  python3 publisher_upgrade.py --topic chatter1 --start-hz 1000 --delta-hz 1000 --max-hz 10000
"""

import argparse
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--topic",    type=str,   default="chatter1")
    p.add_argument("--start-hz", type=float, default=1000.0)
    p.add_argument("--delta-hz", type=float, default=1000.0)
    p.add_argument("--max-hz",   type=float, default=10000.0)
    return p.parse_args()


class Publisher(Node):

    def __init__(self, topic, start_hz, delta_hz, max_hz):
        super().__init__("publisher")

        self.topic    = topic
        self.delta_hz = delta_hz
        self.max_hz   = max_hz
        self.pub      = self.create_publisher(String, topic, 1000)

        self.get_logger().info(
            f"Publisher | topic=/{topic} | "
            f"{start_hz:.0f}hz -> {max_hz:.0f}hz stap {delta_hz:.0f}hz"
        )
        self.get_logger().info("Wacht 3 seconden zodat de receiver klaar is...")

        # Wacht 3 seconden dan start de meting
        self._wacht = self.create_timer(3.0, self._start)
        self._start_hz = start_hz

    def _start(self):
        self._wacht.cancel()
        self.get_logger().info("Start met versturen.")

        volgnummer = 0
        hz = self._start_hz

        while hz <= self.max_hz:
            aantal = int(hz)          # aantal berichten in dit blok = hz
            interval = 1.0 / hz       # tijd tussen berichten in seconden

            self.get_logger().info(f"Blok start | {hz:.0f}hz | {aantal} berichten in 1 seconde")

            blok_start = time.perf_counter()

            for i in range(aantal):
                # Busy-wait: wacht tot het juiste moment voor dit bericht
                doel = blok_start + i * interval
                while time.perf_counter() < doel:
                    pass

                # Verzendtijd in microseconden
                verzendtijd_us = time.time_ns() // 1000

                msg = String()
                msg.data = f"{volgnummer}|{hz:.1f}|{verzendtijd_us}"
                self.pub.publish(msg)

                volgnummer += 1

            blok_duur = time.perf_counter() - blok_start
            self.get_logger().info(
                f"Blok klaar | {hz:.0f}hz | duur={blok_duur:.3f}s | "
                f"verstuurd={aantal}"
            )

            hz += self.delta_hz

        # Alle blokken klaar: stuur stopbericht
        time.sleep(0.1)  # kleine pauze zodat laatste berichten aankomen
        stop = String()
        stop.data = f"STOP|{volgnummer}"
        self.pub.publish(stop)
        self.get_logger().info(f"Klaar. Totaal verstuurd: {volgnummer} berichten.")
        rclpy.shutdown()


def main():
    args = parse_args()
    rclpy.init()
    node = Publisher(
        topic    = args.topic,
        start_hz = args.start_hz,
        delta_hz = args.delta_hz,
        max_hz   = args.max_hz,
    )
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
