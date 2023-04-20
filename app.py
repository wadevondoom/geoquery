import socket
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os
from icmplib import ping, multiping, traceroute, resolve
from statistics import pstdev

db_conn = os.environ.get("DBCONN")
client = MongoClient(db_conn)
db = client["geo_locality_db"]
probes_collection = db["probes"]

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ip_address = request.form.get("ip_address")
        if not ip_address:
            return render_template("index.html", error="IP address cannot be empty.")
        # Run the probe and store the results in the database
        try:
            run_probe(ip_address)
        except Exception as e:
            return render_template("index.html", error=f"Error running probe: {e}")
        return render_template("index.html", success=True)
    return render_template("index.html", success=None)


def run_probe(ip_address):
    try:
        host = ping(ip_address, count=4, interval=1, timeout=2, privileged=False)

        if host.is_alive:
            print(f"{host.address} is up!")
        else:
            print(f"{host.address} is down!")

        hops = traceroute(
            ip_address, count=5, interval=0.05, timeout=2, first_hop=1, max_hops=30
        )
        traceroute_data = []
        last_distance = 0

        for hop in hops:
            traceroute_data.append(
                {
                    "distance": hop.distance,
                    "address": hop.address,
                    "avg_rtt": hop.avg_rtt,
                    "min_rtt": hop.min_rtt,
                    "packets_sent": hop.packets_sent,
                    "packets_received": hop.packets_received,
                }
            )

            if last_distance + 1 != hop.distance:
                print("Some gateways are not responding")
                print(f"{hop.distance}    {hop.address}    {hop.avg_rtt} ms")

            last_distance = hop.distance

        rtt_values = [host.min_rtt, host.max_rtt, host.avg_rtt]
        rtt_std_dev = pstdev(rtt_values) if len(rtt_values) >= 2 else 0

        host_data = {
            "address": host.address,
            "rtt_min": host.min_rtt,
            "rtt_max": host.max_rtt,
            "rtt_avg": host.avg_rtt,
            "rtt_std_dev": rtt_std_dev,
            "packet_loss": host.packet_loss,
            "jitter": host.jitter,
        }

        probe_location = get_probe_location(ip_address)

        probe_data = {
            "host": host_data,
            "traceroute": traceroute_data,
            "probe_location": probe_location,
        }

        probes_collection.insert_one(probe_data)
        print(f"Probe data stored in database: {probe_data}")

    except Exception as e:
        print(f"Error during probe: {e}")


def get_probe_location(pIp):
    # TODO: Implement function to get IP address location
    return {
        "latitude": 49.2827,
        "longitude": -123.1207,
        "city": "Vancouver",
        "region_name": "British Columbia",
        "country_name": "Canada",
    }


@app.route("/data", methods=["GET"])
def data():
    try:
        probe_data = list(probes_collection.find())
        return render_template("data.html", probe_data=probe_data)
    except Exception as e:
        return render_template("data.html", error=f"Error retrieving data: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)