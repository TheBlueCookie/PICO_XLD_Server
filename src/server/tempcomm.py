from blueftc.BlueFTController import BlueFTController
from database import ServerDB

from time import sleep


class XLDTempHandler:
    def __init__(self, database: ServerDB, ip: str, update_interval: int):
        self.db = database
        self.controller = BlueFTController(ip)
        self.update_interval = update_interval
        self.temp_channels = list(self.controller.channels.keys())
        self.heater_indices = list(self.controller.heaters.keys())

    def _update_temps(self):
        for ch in self.temp_channels:
            temp = self.controller.get_latest_channel_temp(ch)
            self.db.write_temp(channel=ch, val=temp)

    def _update_heaters(self):
        for i in self.heater_indices:
            actual_pow = self.controller.get_heater_power(i)
            self.db.write_heater(channel=i, val=actual_pow)

    def exec(self):
        while True:
            self._update_temps()
            self._update_heaters()
            sleep(self.update_interval)


