from blueftc.BlueFTController import BlueFTController
from database_sqlite import ServerDB

from time import sleep
from numpy import isclose


class XLDTempHandler:
    def __init__(self, database: ServerDB, ip: str, update_interval: int):
        self.db = database
        self.controller = BlueFTController(ip)
        self.update_interval = update_interval
        self.temp_channels = list(self.controller.channels.keys())
        self.heater_indices = list(self.controller.heaters.keys())
        self.first_exec = True

    def _update_temps(self):
        for ch in self.temp_channels:
            temp = self.controller.get_latest_channel_temp(ch)
            self.db.write_temp(channel=ch, val=temp[0], timestamp=temp[1])

    def _update_heaters(self):
        for i in self.heater_indices:
            actual_pow = self.controller.get_heater_power(i)
            db_pow = self.db.read_heater(index=i)

            if not self.first_exec:
                if not isclose(actual_pow, db_pow):
                    self.controller.set_heater_power(heater_index=i, setpower=db_pow)

            else:
                self.db.write_heater(index=i, val=actual_pow)
                self.first_exec = False

    def exec(self):
        while True:
            self._update_temps()
            self._update_heaters()
            print("Temperatures and heater power updated.")
            sleep(self.update_interval)


