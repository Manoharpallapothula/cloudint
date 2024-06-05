import paho.mqtt.client as mqtt
import ssl
import time
import asyncio
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
from pymongo import MongoClient
import board
import Adafruit_DHT
from datetime import datetime
from google.cloud import pubsub_v1

# Constants
MONGO_URI = "mongodb_connection_string"
MONGO_DB_NAME = "database_name"
MONGO_COLLECTION_NAME = "collection_name"
AWS_ENDPOINT = "aws_endpoint"
AWS_ROOT_CA_PATH = "path_for_aws_root-ca-file"
AWS_PRIVATE_KEY_PATH = "path_for_aws_privatekey-file"
AWS_CERTIFICATE_PATH = "path_for_aws_certificate-file"
AWS_TOPIC_PUBLISH = "aws_topic_name"
AZURE_CONN_STR = "Azure_connection_string"
GOOGLE_PROJECT_ID = "google_project_id"
GOOGLE_TOPIC_NAME = "google_topic_name"
keyfile_path = "path_for_google-key-file"

# Functions
def read_sensor_data():
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 17)
    if humidity is not None and temperature is not None:
        return humidity, temperature
    else:
        print("Failed to read sensor data.")
        return None, None

async def publish_to_azure(temperature, humidity, mongo_collection):
    async def send_recurring_telemetry(device_client):
        await device_client.connect()
        while True:
            msg_txt_formatted = '{{"timestamp": "{}", "temperature": {}, "humidity": {}}}'.format(datetime.now().isoformat(), temperature, humidity)
            message = Message(msg_txt_formatted)
            message.content_encoding = "utf-8"
            message.content_type = "application/json"
            print("Sending message to Azure - " + msg_txt_formatted)
            await device_client.send_message(message)
            mongo_collection.insert_one({"timestamp": datetime.now(), "temperature": temperature, "humidity": humidity})
            await asyncio.sleep(3)

    device_client = IoTHubDeviceClient.create_from_connection_string(AZURE_CONN_STR)
    try:
        await send_recurring_telemetry(device_client)
    except KeyboardInterrupt:
        print("User initiated exit")
    finally:
        await device_client.shutdown()

def publish_to_google_cloud(temperature, humidity, mongo_collection):
    publisher = pubsub_v1.PublisherClient.from_service_account_file(keyfile_path)
    topic_path = publisher.topic_path(GOOGLE_PROJECT_ID, GOOGLE_TOPIC_NAME)
    while True:
        try:
            data = '{{"timestamp": "{}", "temperature": {}, "humidity": {}}}'.format(datetime.now().isoformat(), temperature, humidity)
            print("Publishing data to Google Cloud:", data)  # Print the data being published
            publisher.publish(topic_path, data.encode())
            mongo_collection.insert_one({"timestamp": datetime.now(), "temperature": temperature, "humidity": humidity})
            time.sleep(3)
        except KeyboardInterrupt:
            print("User initiated exit")
            break
        except Exception as e:
            print("Error:", e)

def main():
    mongo_client = MongoClient(MONGO_URI)
    mongo_db = mongo_client[MONGO_DB_NAME]
    mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
    print("Select cloud platform:")
    print("1. AWS")
    print("2. Azure")
    print("3. Google Cloud")
    choice = input("Enter your choice: ")

    if choice == "1": # AWS
        aws_client = mqtt.Client()
        aws_client.tls_set(
            AWS_ROOT_CA_PATH,
            certfile=AWS_CERTIFICATE_PATH,
            keyfile=AWS_PRIVATE_KEY_PATH,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        aws_client.connect(AWS_ENDPOINT, 8883, keepalive=60)
        aws_client.loop_start()
        try:
            while True:
                temperature, humidity = read_sensor_data()
                if temperature is not None and humidity is not None:
                    payload = '{{"timestamp": "{}", "temperature": {}, "humidity": {}}}'.format(datetime.now().isoformat(), temperature, humidity)
                    print("Publishing data to AWS:", payload)
                    aws_client.publish(AWS_TOPIC_PUBLISH, payload, qos=1)
                    mongo_collection.insert_one({"timestamp": datetime.now(), "temperature": temperature, "humidity": humidity})
                    time.sleep(3)
        except KeyboardInterrupt:
            print("Keyboard interruption detected. Stopping AWS data publishing.")
            aws_client.disconnect()
            aws_client.loop_stop()
    elif choice == "2": # Azure
        temperature, humidity = read_sensor_data()
        if temperature is not None and humidity is not None:
            asyncio.run(publish_to_azure(temperature, humidity, mongo_collection))
        else:
            print("Failed to read sensor data.")
    elif choice == "3": # Google Cloud
        temperature, humidity = read_sensor_data()
        if temperature is not None and humidity is not None:
            publish_to_google_cloud(temperature, humidity, mongo_collection)
        else:
            print("Failed to read sensor data.")
    else:
        print("Invalid choice. Please enter either '1', '2', or '3'.")

if __name__ == "__main__":
    main()
