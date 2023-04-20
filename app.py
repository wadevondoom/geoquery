from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os, ipinfo, boto3

from icmplib import ping, multiping, traceroute, resolve
import numpy as np
import matplotlib.pyplot as plt

db_conn = os.environ.get("DBCONN")
client = MongoClient(db_conn)
db = client["geo_locality_db"]
probes_collection = db["probes"]

aws_access_key = os.environ.get("AWS_ACCESS_KEY")
aws_secret_key = os.environ.get("AWS_SECRET_KEY")
aws_region = os.environ.get("AWS_REGION")
aws_sqs_queue = os.environ.get("AWS_SQS_QUEUE")

sqs = boto3.resource(
    "sqs",
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region,
)

queue = sqs.get_queue_by_name(QueueName=aws_sqs_queue)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ip_address = request.form.get("ip_address")
        if not ip_address:
            return render_template("index.html", error="IP address cannot be empty.")
        # Push the IP address to the SQS queue
        try:
            response = queue.send_message(MessageBody=ip_address)
        except Exception as e:
            return render_template("index.html", error=f"Error pushing IP to SQS queue: {e}")
        return render_template("index.html", success=True)
    return render_template("index.html", success=None)


def run_probe(ip_address):
    try:
        host = ping(ip_address, count=4, interval=1, timeout=2, privileged=False)

        if host.is_alive:
            print(f"{host.address} is up!")

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


            host_data = {
                "address": host.address,
                "rtt_min": float(host.min_rtt),
                "rtt_max": float(host.max_rtt),
                "rtt_avg": float(host.avg_rtt),
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
        else:
            print(f"{host.address} is down!")

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


def create_rtt_histogram():
    # Fetch all probe data from the database
    probes = probes_collection.find()

    # Extract the average RTT values for all traceroute hops
    avg_rtt_values = [hop["avg_rtt"] for probe in probes for hop in probe["traceroute"]]

    # Create a histogram
    plt.hist(avg_rtt_values, bins="auto", alpha=0.7, rwidth=0.85)
    plt.xlabel("Average RTT (ms)")
    plt.ylabel("Frequency")
    plt.title("Histogram of Average RTT Values")

    # Save the histogram as a PNG file
    plt.savefig("static/images/rtt_histogram.png")


@app.route("/rtt_histogram")
def rtt_histogram():
    create_rtt_histogram()
    return render_template("rtt_histogram.html")


@app.route("/geo_visualizations")
def geo_visualizations():
    # Create histogram of distances
    probes = probes_collection.find()
    distances = [hop["distance"] for probe in probes for hop in probe["traceroute"]]
    plt.hist(distances, bins="auto", alpha=0.7, rwidth=0.85)
    plt.xlabel("Distance (hops)")
    plt.ylabel("Frequency")
    plt.title("Histogram of Traceroute Distances")

    # Create histogram of max RTT
    plt.figure()
    max_rtts = [probe["host"]["rtt_max"] for probe in probes]
    plt.hist(max_rtts, bins="auto", alpha=0.7, rwidth=0.85)
    plt.xlabel("Max RTT (ms)")
    plt.ylabel("Frequency")
    plt.title("Histogram of Max RTT Values")

    # Save both histograms as PNG files
    plt.savefig("static/images/distance_histogram.png")
    plt.savefig("static/images/max_rtt_histogram.png")

    return render_template("geoviz.html")


@app.route("/map", methods=["GET"])
def map():
    return render_template("map.html")


@app.route("/data", methods=["GET"])
def data():
    try:
        probe_data = list(probes_collection.find())
        return render_template("data.html", probe_data=probe_data)
    except Exception as e:
        return render_template("data.html", error=f"Error retrieving data: {e}")


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
    app.run(host="0.0.0.0", debug=True)
