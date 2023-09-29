from dataclasses import dataclass, field
from collections import defaultdict
import secrets
from datetime import datetime
from multiprocessing import Lock

from measurements import Measurement, WAIT, GO, RUNNING


@dataclass
class ServerDB:
    measurements: defaultdict[str] = field(default_factory=lambda: defaultdict(str))
    temps: defaultdict[int] = field(default_factory=lambda: defaultdict(int))
    heaters: defaultdict[int] = field(default_factory=lambda: defaultdict(int))
    meas_lock: Lock = Lock()
    temp_lock: Lock = Lock()
    heater_lock: Lock = Lock()
    mxc_ch: int = 6
    still_ch: int = 5
    fourk_ch: int = 2
    fiftyk_ch: int = 1
    mxc_ind: int = 4
    still_ind: int = 3
    mxc_switch_ind: int = 2
    still_switch_ind: int = 1

    def register_measurement(self, user: str, group: str):
        with self.meas_lock:
            unique = False
            while not unique:
                token = secrets.token_urlsafe(16)
                if token not in list(self.measurements.keys()):
                    unique = True

            meas = Measurement(id=token, user=user, group=group, timestamp=datetime.utcnow())
            self.measurements[token] = meas

        return token

    def unregister_measurement(self, meas_id: str):
        with self.meas_lock:
            try:
                self.measurements.pop(meas_id)
            except KeyError as err:
                print(err)

    def get_html_meas_dict(self):
        meas = []
        with self.meas_lock:
            for m in self.measurements.values():
                meas.append(m)

            return meas

    def set_meas_status(self, meas_id: str, status: bool):
        with self.meas_lock:
            if meas_id in self.measurements.keys():
                print(self.measurements[meas_id])
                self.measurements[meas_id].running = status

                if status:
                    self.measurements[meas_id].signal = RUNNING

                else:
                    self.measurements[meas_id].signal = WAIT

                return status

    def write_temp(self, channel: int, val: float):
        with self.temp_lock:
            self.temps[channel] = val

    def read_temp(self, channel: int):
        with self.temp_lock:
            return self.temps[channel]

    def write_heater(self, channel: int, val: float):
        with self.heater_lock:
            self.heaters[channel] = val
            print(val, self.heaters)

    def read_heater(self, channel: int):
        with self.heater_lock:
            return self.heaters[channel]

    def get_meas_signal(self, meas_id):
        with self.meas_lock:
            if meas_id in self.measurements.keys():
                return self.measurements[meas_id].signal

    def set_all_meas_to_go(self):
        with self.meas_lock:
            for meas_id in self.measurements.keys():
                self.measurements[meas_id].signal = GO
