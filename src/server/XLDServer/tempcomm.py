from blueftc.BlueFTController import BlueFTController
from database_sqlite import ServerDB

from time import sleep
from numpy import isclose
import logging

xld_logger = logging.getLogger('waitress')


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
        if self.first_exec:
            [self.db.write_heater(i, self.controller.get_heater_power(i)) for i in self.heater_indices]
            self.first_exec = False

        for i in self.heater_indices:
            actual_pow = self.controller.get_heater_power(i)
            db_pow = self.db.read_heater(index=i)

            if not isclose(actual_pow, db_pow):
                self.controller.set_heater_power(heater_nr=i, setpower=db_pow)

    def exec(self):
        while True:
            self._update_temps()
            self._update_heaters()
            xld_logger.info("Temperatures and heater power updated.")
            sleep(self.update_interval)


