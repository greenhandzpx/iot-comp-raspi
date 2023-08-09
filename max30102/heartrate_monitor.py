from max30102 import MAX30102
from gps import GPS
import hrcalc
import threading
import time
import numpy as np
import json
from mqtt_client import Client


HR_MONITOR = None

EVENT = threading.Event()


def on_message(client, userdata, msg):
    print("receive: " + msg.topic + " " + str(msg.payload))
    global HR_MONITOR
    if HR_MONITOR != None:
        HR_MONITOR.set_freq(str(msg.payload))
    # enable the next publish behavior
    EVENT.set()


class HeartRateMonitor(object):
    """
    A class that encapsulates the max30102 device into a thread
    """

    LOOP_TIME = 0.01

    def __init__(self, print_raw=False, print_result=False):
        self.bpm = 0
        if print_raw is True:
            print("IR, Red")
        self.print_raw = print_raw
        self.print_result = print_result
        self.client = Client(on_message)
        self.interval = 10
        self.cnt = 0
        self.bo_range = [97, 100]
        self.bpm_range = [70, 115]
        global EVENT
        EVENT.set()

    def set_freq(self, resp: str):
        # print("set freq:", resp)
        data = json.loads(resp[2:-1])["content"]
        self.interval = data["interval"]
        print("recv data", data)
        print("set new freq:")
        print("interval:", self.interval)
        if "data" in data:
            self.bo_range = [data["data"]["bo"]["min"], data["data"]["bo"]["max"]]
            print("bo range:", self.bo_range)
            self.bpm_range = [data["data"]["bpm"]["min"], data["data"]["bpm"]["max"]]
            print("bpm range:", self.bpm_range)

    def process_result(self, bpm, spo2, lat, lon):
        self.cnt += 1
        if (
            bpm < self.bpm_range[0]
            or bpm > self.bpm_range[1]
            or spo2 < self.bo_range[0]
            or spo2 > self.bo_range[1]
        ):
            # detected exception
            self.interval = 1

        if self.cnt >= self.interval:
            bpm = 140
            spo2 = 90
            # bpm = 74
            # spo2 = 99
            self.publish(bpm, spo2, lat, lon)
            self.cnt = 0

    # def publish_thread(self, data):
    #     EVENT.wait()
    #     print("publish_thread: data: ", data)
    #     self.client.publish(data)
    #     EVENT.clear()

    # Note that this method may block until recv the response from the server
    def publish(self, bpm, spo2, lat, lon):
        data = {}
        data["type"] = 2
        data["data"] = {}
        data["data"]["id"] = 180
        data["data"]["bo"] = spo2
        data["data"]["bpm"] = bpm
        data["data"]["lat"] = lat
        data["data"]["lon"] = lon
        data["data"]["lo"] = "home"
        data_str = json.dumps(data)

        # print("publish: data: ", data_str)

        # t = threading.Thread(target=self.publish_thread, args=(self, data_str))
        # EVENT.wait()
        # self.client.publish(data_str)
        # EVENT.clear()

        if EVENT.is_set():
            if self.print_result:
                print(
                    "BPM: {0}, SpO2: {1}, Lat: {2}, Lon: {3}".format(
                        bpm, spo2, lat, lon
                    )
                )
            self.client.publish(data_str)
            EVENT.clear()

        # print("publish finished", data_str)

    def run_sensor(self):
        global HR_MONITOR
        if HR_MONITOR == None:
            HR_MONITOR = self

        sensor = MAX30102()
        gps = GPS()
        ir_data = []
        red_data = []
        bpms = []

        # data for show
        self.spos = []
        self.bpms = []
        self.lat = []
        self.lon = []

        # run until told to stop
        while not self._thread.stopped:
            # read gps
            if gps.GPS_read():
                self.lat = gps.lat + gps.ulat
                self.lon = gps.lon + gps.ulon
            # read max30102
            # check if any data is available
            num_bytes = sensor.get_data_present()
            if num_bytes > 0:
                # grab all the data and stash it into arrays
                while num_bytes > 0:
                    red, ir = sensor.read_fifo()
                    num_bytes -= 1
                    ir_data.append(ir)
                    red_data.append(red)
                    if self.print_raw:
                        print("{0}, {1}".format(ir, red))

                while len(ir_data) > 100:
                    ir_data.pop(0)
                    red_data.pop(0)

                if len(ir_data) == 100:
                    bpm, valid_bpm, spo2, valid_spo2 = hrcalc.calc_hr_and_spo2(
                        ir_data, red_data
                    )
                    if valid_bpm:
                        bpms.append(bpm)
                        while len(bpms) > 4:
                            bpms.pop(0)
                        self.bpm = np.mean(bpms)
                        if np.mean(ir_data) < 50000 and np.mean(red_data) < 50000:
                            self.bpm = 0
                            # if self.print_result:
                            # print("Finger not detected")
                        # else:
                        # sss self.client.publish()

                        if spo2 > 0 and self.bpm > 0:
                            self.bpms.append(self.bpm)
                            self.spos.append(spo2)
                            self.process_result(self.bpm, spo2, self.lat, self.lon)

            time.sleep(self.LOOP_TIME)

        sensor.shutdown()

    def start_sensor(self):
        self._thread = threading.Thread(target=self.run_sensor)
        self._thread.stopped = False
        self._thread.start()

    def stop_sensor(self, timeout=2.0):
        self._thread.stopped = True
        self.bpm = 0
        self._thread.join(timeout)

    def show(self):
        import matplotlib.pyplot as plt
        from scipy.signal import savgol_filter

        x = np.arange(len(self.spos))
        y = np.array(self.spos)

        yhat = savgol_filter(y, 51, 3)

        plt.plot(x, yhat)
        plt.show()
