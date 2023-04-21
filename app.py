from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os, ipinfo
from icmplib import traceroute
from ping3 import ping as pping
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
        ping_results = [pping(ip_address, timeout=2) for _ in range(4)]
        valid_results = list(filter(None, ping_results))

        host = {
            "address": ip_address,
            "min_rtt": min(valid_results) if valid_results else None,
            "max_rtt": max(valid_results) if valid_results else None,
            "avg_rtt": sum(valid_results) / len(valid_results)
            if valid_results
            else None,
        }

        hops = traceroute(ip_address)
        traceroute_data = []
        last_distance = 0

        for hop in hops:
            traceroute_data.append(
                {
                    "distance": float(hop.distance),
                    "address": hop.address,
                    "avg_rtt": float(hop.avg_rtt),
                    "packet_loss": float(host.packet_loss),
                    "packets_sent": float(hop.packets_sent),
                    "packets_received": float(hop.packets_received),
                }
            )
            print(
                f"Current traceroute_data: {traceroute_data}"
            )  # Add this line to debug

            if last_distance + 1 != hop.distance:
                print("Some gateways are not responding")
                print(f"{hop.distance}    {hop.address}    {hop.avg_rtt} ms")

            last_distance = hop.distance

        rtt_values = list(
            filter(None, [host["min_rtt"], host["max_rtt"], host["avg_rtt"]])
        )
        rtt_std_dev = pstdev(rtt_values) if len(rtt_values) >= 2 else 0.0

        host_data = {
            "address": host["address"],
            "rtt_min": float(host["min_rtt"]) if host["min_rtt"] is not None else None,
            "rtt_max": float(host["max_rtt"]) if host["max_rtt"] is not None else None,
            "rtt_avg": float(host["avg_rtt"]) if host["avg_rtt"] is not None else None,
            "rtt_std_dev": float(rtt_std_dev),
            "packet_loss": float(host.packet_loss),
            "jitter": float(host.jitter),
            "packets_sent": float(host.packets_sent),
            "packets_received": float(host.packets_received),
        }

        probe_location = get_probe_location()

        probe_data = {
            "host": host_data,
            "traceroute": traceroute_data,
            "probe_location": probe_location,
        }

        probes_collection.insert_one(probe_data)
        print(f"Probe data stored in database: {probe_data}")

    except Exception as e:
        print(f"Error during probe: {e}")


def get_probe_location():
    access_token = os.environ.get("IPInfoToken")
    handler = ipinfo.getHandler(access_token)
    details = handler.getDetails()

    return {
        "latitude": details.latitude,
        "longitude": details.longitude,
        "city": details.city,
        "region_name": details.region,
        "country_name": details.country_name,
    }


@app.route("/data", methods=["GET"])
def data():
    try:
        probe_data = list(probes_collection.find())
        return render_template("data.html", probe_data=probe_data)
    except Exception as e:
        return render_template("data.html", error=f"Error retrieving data: {e}")


@app.route("/map", methods=["GET"])
def map():
    return render_template("map.html")


@app.route("/api/probes", methods=["GET"])
def api_probes():
    try:
        probe_data = list(
            probes_collection.find(
                {}, {"_id": 0, "host.address": 1, "probe_location": 1, "traceroute": 1}
            )
        )
        return jsonify(probe_data)
    except Exception as e:
        return jsonify({"error": f"Error retrieving data: {e}"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
