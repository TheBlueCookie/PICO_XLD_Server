from database_sqlite import ServerDB
from passkey import db_filename

import numpy as np
from time import sleep
from datetime import datetime


class TemperatureSweep:
    def __init__(self, thermalization_time, power_array, client_timeout, test_mode: bool = False):
        self.thermalization_time = thermalization_time
        self.power_array = power_array
        self.db = ServerDB(db_filename)
        self.client_timeout = client_timeout
        self.test_mode = test_mode

    def wait_for_all_clients(self):
        start = datetime.now()
        done = False
        while not done:
            done = True
            for signal, crashed in self.db.get_all_meas_signals():
                if signal == 'running' or signal == 'go' and not crashed:
                    done = False

            if (datetime.now() - start).total_seconds() >= self.client_timeout:
                clients = self.db.get_html_meas_dict()
                for meas in clients:
                    if meas['signal'] == 'running' or meas['signal'] == 'go':
                        self.db.set_meas_as_crashed(meas_id=meas['id'])
                done = True

            sleep(5)

    def start_all_client_meas(self):
        self.db.set_all_meas_to_go()

    def exec(self):
        print(f'{datetime.now()}: Making sure that all clients are ready.')
        self.wait_for_all_clients()
        print(f'{datetime.now()}: Started sweep.')

        for i, power in enumerate(self.power_array):
            if not self.test_mode:
                self.db.write_heater(index=self.db.mxc_ind, val=float(power))
            print(f'{datetime.now()}: Set heater power to {power} uW. '
                  f'Waiting {self.thermalization_time} s for thermalization.')
            if not self.test_mode:
                sleep(self.thermalization_time)
            print(
                f'{datetime.now()}: Thermalization done. Current temperature at mixing chamber: '
                f'{self.db.read_temp(channel=self.db.mxc_ch)} K')
            self.start_all_client_meas()
            print(f'{datetime.now()}: Send GO signal to all measurement clients.')
            if not self.test_mode:
                sleep(30)
            print(
                f'{datetime.now()}: Waiting for all measurements to finish at current '
                f'temperature point ({i + 1}/{len(self.power_array)}).')
            self.wait_for_all_clients()
            print(f'{datetime.now()}: All measurements finished at current temperature point.')


class TemperatureSweepManager:
    def __init__(self):
        self.modes = ['pid', 'direct-power']
        self.interpolations = ['linear', 'quadratic', 'manual']

        self.mode = ''
        self.interpolation = ''
        self.cl_timeout = 0
        self.therm_time = 0
        self.sweep_array = np.zeros(1)
        self.html_dict = {}
        self.return_to_base = False
        self.params = {}

        self.generate_html_dict()

    def generate_sweep_array(self, params: dict):
        assert 'sweep_mode' in params.keys() and 'interpolation' in params.keys()
        assert 'client_timeout' in params.keys()
        assert 'ret_base' in params.keys()

        sweep_mode = params['sweep_mode']
        interpolation = params['interpolation']
        self.cl_timeout = params['client_timeout']
        self.return_to_base = bool(params['ret_base'])

        assert sweep_mode in self.modes, "Wrong sweep mode."
        assert interpolation in self.interpolations, "Wrong interpolation."
        if sweep_mode == 'pid':
            assert interpolation in ['linear', 'manual'], "Wrong interpolation for PID mode."

        if sweep_mode == 'direct-power':
            assert 'therm_time' in params.keys()

        if sweep_mode == 'direct-power' and interpolation in ['linear', 'quadratic']:
            assert 'min_pow' in params.keys()
            assert 'max_pow' in params.keys()
            assert 'n_pow' in params.keys()

        if sweep_mode == 'pid':
            raise NotImplementedError

        self.params = params
        self.mode = sweep_mode
        self.interpolation = interpolation

        if self.mode == 'direct-power':
            assert 'therm_time' in self.params.keys()
            self.therm_time = self.params['therm_time']

            if self.interpolation == 'linear':
                self.sweep_array = np.linspace(float(self.params['min_pow']), float(self.params['max_pow']),
                                               int(self.params['n_pow']))

            elif self.interpolation == 'quadratic':
                self.sweep_array = np.square(
                    np.linspace(float(self.params['min_pow']), np.sqrt(float(self.params['max_pow'])),
                                int(self.params['n_pow'])))

            elif self.interpolation == 'manual':
                lines = self.params['values'].split('\n')
                lines = [float(i) for i in lines]
                self.sweep_array = np.array(lines)

        self.generate_html_dict()

    def generate_html_dict(self):
        ret = 'RETURN' if self.return_to_base else 'NOT RETURN'
        html_dict = {'sweep_mode': self.mode, 'interpolation': self.interpolation,
                     'vals': [f' {v:.0f}' for v in self.sweep_array],
                     'cl_timeout': self.cl_timeout, 'ret_base': ret}

        if self.mode == 'direct-power' or self.mode == '':
            html_dict['therm_time'] = self.therm_time

        self.html_dict = html_dict
