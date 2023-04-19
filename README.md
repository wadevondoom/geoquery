GeoQuery is a project that collects network metrics and probe locations to determine the geographic location of a target IP address. By gathering data such as round-trip time (RTT) and probe locations, GeoQuery allows you to infer the geographic location of IP addresses.

## Features 
- Collect network metrics (RTT, packet loss, etc.) from multiple probe locations 
- Determine probe locations based on IP addresses 
- Use triangulation and machine learning techniques to estimate IP address locations 
- Store probe data for future analysis and reference 

## Overview 
The project consists of several steps, including data collection, preprocessing, distance estimation, triangulation, machine learning, and location prediction.

### Data collection 
Gather RTT and other network metrics from each probe for the target IP address. Record the probe's geographic location as well.

### Data preprocessing 
Clean and preprocess the data to ensure consistency and remove any outliers or errors.

### Distance estimation 
Use the collected RTT values to estimate the distance between each probe and the target IP address. One approach is to assume a constant speed for data packets (e.g., the speed of light in fiber optic cables) and convert the RTT into a distance. However, this method may not be entirely accurate due to network latency and varying packet transmission speeds.

### Triangulation 
Use the estimated distances and the known locations of the probes to triangulate the position of the target IP address. In the simplest case, you can use trilateration, which involves solving a system of equations based on the distances between the target IP and at least three non-collinear probes. However, this method assumes that distance measurements are accurate, which may not be the case due to network latency and other factors.

### Machine learning 
Instead of relying solely on triangulation, you can use machine learning to improve the location estimation. Train a model using the probe data (RTT, probe locations, etc.) and ground truth locations of known IP addresses. The model should learn to predict the location of an IP address based on the collected metrics. You may need to experiment with different algorithms and feature sets to find the best model for your specific use case.

### Location prediction 
Input the probe data for the target IP address into your trained machine learning model to predict its geographic location.

## Installation 
1. Clone this repository 
2. Install the required Python packages: `pip install -r requirements.txt` 
3. Configure the probe locations and target IP addresses 
4. Run the main script: `python app.py`

## License 
This project is licensed under the MIT License. See the LICENSE file for more information.
