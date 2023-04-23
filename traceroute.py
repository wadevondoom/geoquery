import logging
import sys
from datetime import datetime
from scapy.all import sr, IP, ICMP, UDP
import json

logging.basicConfig(level=logging.INFO)


class Traceroute:
    def __init__(self, target, protocol="icmp", max_hops=30, timeout=2, attempts=3):
        self.target = target
        self.protocol = protocol.lower()
        self.max_hops = max_hops
        self.timeout = timeout
        self.attempts = attempts

        if self.protocol not in ("udp", "icmp"):
            raise ValueError("Protocol must be either 'udp' or 'icmp'")

    def run(self):
        result = []

        transport_layer = UDP(dport=33434) if self.protocol == "udp" else ICMP()

        for ttl in range(1, self.max_hops + 1):
            hop_result = {"ip": None, "rtts": []}
            destination_reached = False

            for _ in range(self.attempts):
                packet = IP(dst=self.target, ttl=ttl) / transport_layer
                ans, _ = sr(packet, timeout=self.timeout, verbose=0)

                if not ans:
                    hop_result["rtts"].append(None)
                else:
                    reply = ans[0][1]
                    rtt = (ans[0][1].time - ans[0][0].sent_time) * 1000
                    hop_result["ip"] = reply.src
                    hop_result["rtts"].append(rtt)

                    if (
                        self.protocol == "udp"
                        and reply.haslayer(ICMP)
                        and reply[ICMP].type == 3
                        and reply[ICMP].code == 3
                    ):
                        destination_reached = True
                    elif self.protocol == "icmp" and reply.type == 0:
                        destination_reached = True

            result.append(hop_result)

            if destination_reached:
                break

        return result

    def to_json(self, results, workerid):
        utc_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        traceroute_data = {
            "traceroute": {
                "workerid": workerid,
                "timestamp": utc_time,
                "target": self.target,
                "hops": [
                    {
                        "id": i + 1,
                        "ip": hop["ip"] if hop["ip"] else "",
                        "rtts": [
                            round(rtt, 2) if rtt is not None else None
                            for rtt in hop["rtts"]
                        ],
                    }
                    for i, hop in enumerate(results)
                ],
            }
        }
        return json.dumps(traceroute_data, indent=2)

    def to_standard(self, results, workerid):
        utc_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        output = f"Traceroute to (target: {self.target}, workerid: {workerid}, timestamp: {utc_time})\n"
        for i, hop in enumerate(results):
            hop_line = f"{i + 1}  {hop['ip'] if hop['ip'] else '*'}"
            for rtt in hop["rtts"]:
                if rtt is not None:
                    hop_line += f"  {round(rtt, 2)} ms"
                else:
                    hop_line += "  *"
            output += hop_line + "\n"
        return output


if __name__ == "__main__":
    if len(sys.argv) < 4:
        logging.debug("Usage: python scapy_traceroute.py <target> <protocol> <output>")
        sys.exit(1)

    target = sys.argv[1]
    protocol = sys.argv[2]
    output_format = sys.argv[3]

    if protocol.lower() not in ("udp", "icmp"):
        logging.debug("Error: Protocol must be either 'udp' or 'icmp'")
        sys.exit(1)

    if output_format.lower() not in ("json", "standard"):
        logging.debug("Error: Output format must be either 'json' or 'standard'")
        sys.exit(1)

    logging.info(f"Traceroute to {target} using {protocol.upper()}:")

    tracer = Traceroute(target, protocol)

    results = tracer.run()

    workerid = "BLAH123eee"

    if output_format.lower() == "json":
        output = tracer.to_json(results, workerid)
    elif output_format.lower() == "standard":
        output = tracer.to_standard(results, workerid)
    else:
        output = tracer.to_standard(results, workerid)

    logging.info(output)
