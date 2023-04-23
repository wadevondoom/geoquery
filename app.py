from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from pymongo import MongoClient
import os, ipinfo, random, string
from icmplib import traceroute
from ping3 import ping as pping
from statistics import pstdev
import logging
from logging.handlers import RotatingFileHandler
import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv


# 👆 We're continuing from the steps above. Append this to your server.py file.

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


db_conn = os.environ.get("DBCONN")
client = MongoClient(db_conn)
db = client["geo_locality_db"]
probes_collection = db["probes"]

### Setup app
app = Flask(__name__)
app.config.update(
    {
        "SECRET_KEY": "".join(
            random.choices(
                string.ascii_uppercase + string.ascii_lowercase + string.digits, k=32
            )
        )
    }
)


oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

""" Logging setup """
# Set up logging
log_formatter = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")

# Set up file handler
file_handler = RotatingFileHandler("app.log", maxBytes=1000000, backupCount=5)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_formatter)

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(log_formatter)

# Add handlers to the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


### Login and callback routes

## Login route - required for auth0
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )

## Callback route - required for auth0
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect("/")

## Logout route - required to clear session
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

## Index - Home page route
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        ip_address = request.form.get("ip_address")
        if not ip_address:
            return render_template("index.html", error="IP address cannot be empty.")
        # Run the probe and store the results in the database
        try:
            logger.info("Running probe...")
            run_probe(ip_address)
        except Exception as e:
            logger.error("Error running probe: {e}")
            return render_template("index.html", error=f"Error running probe: {e}")
        return render_template("index.html", success=True)
    return render_template("index.html", success=None, session=session.get('user'))


def run_probe(ip_address):
    try:
        ping_results = [pping(ip_address, timeout=2) for _ in range(4)]
        logger.debug(f"Ping results: {ping_results}")
        valid_results = list(filter(None, ping_results))

        packet_loss = (len(ping_results) - len(valid_results)) / len(ping_results) * 100

        host = {
            "address": ip_address,
            "min_rtt": min(valid_results) if valid_results else None,
            "max_rtt": max(valid_results) if valid_results else None,
            "avg_rtt": sum(valid_results) / len(valid_results) if valid_results else None,
            "packet_loss": packet_loss,
        }

        jitter = host["max_rtt"] - host["min_rtt"] if host["min_rtt"] is not None and host["max_rtt"] is not None else None

        hops = traceroute(ip_address)
        traceroute_data = []
        last_distance = 0

        for hop in hops:

            traceroute_data.append(
                {
                    "distance": float(hop.distance),
                    "address": hop.address,
                    "avg_rtt": float(hop.avg_rtt),
                    "packet_loss": float(host["packet_loss"]),
                    "packets_sent": float(hop.packets_sent),
                    "packets_received": float(hop.packets_received),
                }
            )

            logger.debug(f"Current traceroute_data: {traceroute_data}")

            if last_distance + 1 != hop.distance:
                logger.warning("Some gateways are not responding")
                logger.debug(f"{hop.distance}    {hop.address}    {hop.avg_rtt} ms")

            last_distance = hop.distance

        rtt_values = list(
            filter(None, [host["min_rtt"], host["max_rtt"], host["avg_rtt"]])
        )
        rtt_std_dev = pstdev(rtt_values) if len(rtt_values) >= 2 else 0.0

        host_data = {
            "address": host["address"],
            "rtt_min": float(host["min_rtt"]) * 1000 if host["min_rtt"] is not None else None,
            "rtt_max": float(host["max_rtt"]) * 1000 if host["max_rtt"] is not None else None,
            "rtt_avg": float(host["avg_rtt"]) * 1000 if host["avg_rtt"] is not None else None,
            "rtt_std_dev": float(rtt_std_dev) * 1000,
            "packet_loss": float(host["packet_loss"]),
            "jitter": float(jitter) * 1000 if jitter is not None else None,
        }

        probe_location = get_probe_location()
        logger.debug("probe_location")

        probe_data = {
            "host": host_data,
            "traceroute": traceroute_data,
            "probe_location": probe_location,
        }

        probes_collection.insert_one(probe_data)
        logger.info(f"Probe data stored in database: {probe_data}")

    except Exception as e:
        logger.error(f"Error during probe: {e}")




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


