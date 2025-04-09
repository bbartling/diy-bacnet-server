import requests
import random
import time
import csv

# Load point names from your CSV
with open(
    "./nr-modbus-to-py-bacnet/chiller_csv_file/fanshaweCec_multistack_modbusRtu_9600_8N1.csv.csv",
    newline="",
) as csvfile:
    reader = csv.DictReader(csvfile)
    point_names = [row["Name"] for row in reader if row.get("Name")]

# FastAPI endpoint
url = "http://localhost:8080/update"

# Run loop forever
while True:
    # Pick a random point and value
    point = random.choice(point_names)
    value = round(random.uniform(0, 100), 2)

    # Build the payload
    payload = {point: value}

    try:
        response = requests.post(url, json=payload)
        print(
            f"Sent: {payload} => Status: {response.status_code}, Response: {response.json()}"
        )
    except Exception as e:
        print(f"Error sending data: {e}")

    time.sleep(1)
