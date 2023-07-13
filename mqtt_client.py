import paho.mqtt.client as mqtt
import json
import datetime
import pytz
import hmac
import hashlib
import time
import threading

jsonpath = './data.json'
host = "f292611f33.st1.iotda-device.cn-north-4.myhuaweicloud.com"
deviceId = "64ae66e9b84c1334befacf21_1c697a231dd9"
secret = "iotascfg"

# define topic type
MSG_UP = 0
REQUEST = 1

# event = threading.Event()


# topic generate
def topic(type):
    if type == MSG_UP:
        print("topic report")
        return "$oc/devices/"+deviceId+"/sys/messages/up"
    elif type == REQUEST:
        print("topic request")
        return "$oc/devices/"+deviceId+"/sys/commands/#"


# connect fallback
def on_connect(client, userdata, flags, rc):
    print('Connected with result code '+str(rc))
    if rc == 0:
        print("connect success")
        client.subscribe(topic(REQUEST))

# recv message fallback
def on_message(client, userdata, msg):
    print("receive: "+msg.topic+" "+str(msg.payload))
    # # enable the next publish behavior
    # event.set()

# password generate
def time_stamp():
    time = datetime.datetime.now(pytz.utc).strftime("%Y%m%d%H")
    return time

def sha256_mac(message, time):
    passWord = None
    try:
        sha256_HMAC = hmac.new(time.encode(), message.encode(), hashlib.sha256)
        bytes = sha256_HMAC.digest()
        passWord = byteArrayToHexString(bytes)
    except Exception as e:
        print(e)
    return passWord

def byteArrayToHexString(byteArray):
    return ''.join(['%02x' % b for b in byteArray])

def password():
    return sha256_mac(secret, time_stamp())

# clientid generate
def client_id():
    return deviceId + "_0_0_" + time_stamp()


class Client:
    def __init__(self, on_msg_cb) -> None:
        # create mqtt client
        self.client = mqtt.Client(client_id())

        # bind service
        self.client.on_connect = on_connect
        self.client.on_message = on_msg_cb
        # connect
        self.client.username_pw_set(deviceId, password())
        self.client.connect(host, 1883, 120)

        self.start_subscribe_thread()

        
    def publish(self, payload):
        self.client.publish(topic(MSG_UP), payload=payload, qos=1)

    def start_subscribe_thread(self):
        def loop():
            print("Start to subscribe...")
            self.client.loop_forever()
        t = threading.Thread(target=loop)
        t.start()


def create_client() -> mqtt.Client:

    return client




if __name__ == "__main__":
    client = create_client()

    with open(jsonpath, 'r') as data_file:
        data = json.load(data_file)
        data_str = json.dumps(data)

    while True:
        # publish message
        client.publish(topic(MSG_UP),payload=data_str,qos=1)
        time.sleep(6)