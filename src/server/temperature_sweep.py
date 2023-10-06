from database_sqlite import ServerDB
from passkey import db_filename

import numpy as np
from time import sleep
from datetime import datetime


class TemperatureSweep:
    def __init__(self, thermalization_time, power_array, client_timeout):
        self.thermalization_time = thermalization_time
        self.power_array = power_array
        self.db = ServerDB(db_filename)
        self.client_timeout = client_timeout

    def wait_for_all_clients(self):
        start = datetime.now()
        done = False
        while not done:
            done = True
            for signal in self.db.get_all_meas_signals():
                if signal == 'running' or signal == 'go':
                    done = False

            if (datetime.now() - start).total_seconds() >= self.client_timeout:
                done = True

            sleep(5)

    def start_all_client_meas(self):
        self.db.set_all_meas_to_go()

    def exec(self):
        print(f'{datetime.now()}: Making sure that all clients are ready.')
        self.wait_for_all_clients()
        print(f'{datetime.now()}: Started sweep.')

        for i, power in enumerate(self.power_array):
            self.db.write_heater(index=self.db.mxc_ind, val=float(power))
            print(f'{datetime.now()}: Set heater power to {power} uW. '
                  f'Waiting {self.thermalization_time} s for thermalization.')
            sleep(self.thermalization_time)
            print(
                f'{datetime.now()}: Thermalization done. Current temperature '
                f'{self.db.read_temp(channel=self.db.mxc_ch)}')
            self.start_all_client_meas()
            print(f'{datetime.now()}: Send GO signal to all measurement clients.')
            sleep(30)
            print(
                f'{datetime.now()}: Waiting for all measurements to finish at current '
                f'temperature point ({i + 1}/{len(self.power_array)}).')
            self.wait_for_all_clients()
            print(f'{datetime.now()}: All measurements finished at current temperature point.')
