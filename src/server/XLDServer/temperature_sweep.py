import sys

from src.server.XLDServer.database_sqlite import ServerDB
from passkey import db_filename

import numpy as np
from time import sleep
from datetime import datetime
from multiprocessing import Event
import logging

xld_logger = logging.getLogger('waitress')


class TemperatureSweep:
    def __init__(self, thermalization_time, power_array, client_timeout, return_to_base: bool = False,
                 abort_flag: Event = Event(), is_running: Event = Event(), test_mode: bool = False,
                 skip_first: bool = False):
        self.thermalization_time = float(thermalization_time)
        self.power_array = np.array(power_array)
        self.db = ServerDB(db_filename)
        self.client_timeout = float(client_timeout)
        self.test_mode = float(test_mode)
        self.abort_flag = abort_flag
        self.is_running = is_running
        self.return_to_base = return_to_base
        self.skip_first = skip_first

    def wait_for_all_clients(self):
        start = datetime.now()
        done = False
        while not done:
            self._try_abort()
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
        self.is_running.set()
        xld_logger.info(f'TEMPERATURE CONTROL: Making sure that all clients are ready.')
        self.wait_for_all_clients()
        xld_logger.info(f'TEMPERATURE CONTROL: Started sweep.')

        for i, power in enumerate(self.power_array):
            self._try_abort()
            if not self.test_mode:
                self.db.write_heater(index=self.db.mxc_ind, val=float(power))
            xld_logger.info(f'TEMPERATURE CONTROL: Set heater power to {power} uW.')
            if i == 0:
                if not self.skip_first:
                    xld_logger.info(f'TEMPERATURE CONTROL: Waiting {self.thermalization_time} s for thermalization.')
                    if not self.test_mode:
                        sleep(self.thermalization_time)
                else:
                    xld_logger.info(f'TEMPERATURE CONTROL: Skipping first thermalization.')
            else:
                xld_logger.info(f'TEMPERATURE CONTROL: Waiting {self.thermalization_time} s for thermalization.')
                if not self.test_mode:
                    sleep(self.thermalization_time)
            self._try_abort()
            xld_logger.info(
                f'TEMPERATURE CONTROL: Thermalization done. Current temperature at mixing chamber: '
                f'{self.db.read_temp(channel=self.db.mxc_ch)} K')
            self.start_all_client_meas()
            xld_logger.info(f'TEMPERATURE CONTROL: Send GO signal to all measurement clients.')
            if not self.test_mode:
                sleep(30)
            self._try_abort()
            xld_logger.info(
                f'TEMPERATURE CONTROL: Waiting for all measurements to finish at current '
                f'temperature point ({i + 1}/{len(self.power_array)}).')
            self.wait_for_all_clients()
            xld_logger.info(f'TEMPERATURE CONTROL: All measurements finished at current temperature point.')
            self._try_abort()

        if self.return_to_base:
            xld_logger.info(f'TEMPERATURE CONTROL: Returning to base temperature.')
            if not self.test_mode:
                self.db.write_heater(index=self.db.mxc_ind, val=0.0)

        else:
            xld_logger.info(f'TEMPERATURE CONTROL: Not returning to base temperature.')

        self.is_running.clear()
        if not self.test_mode:
            pass
            # self.db.write_heater(index=self.db.mxc_ind, val=0)


    def _try_abort(self):
        if self.abort_flag.is_set():
            self.abort_flag.clear()
            self.is_running.clear()
            xld_logger.info(f'TEMPERATURE CONTROL: SWEEP ABORTED!')
            sys.exit()

        else:
            return False


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
        self.skip_first = False
        self.params = {}
        self.confirmed = False
        self.started = False
        self.client_dict = {}

        self.generate_html_dict()

    def generate_sweep_array(self, params: dict):
        self.confirmed = False
        assert 'sweep_mode' in params.keys() and 'interpolation' in params.keys()
        assert 'client_timeout' in params.keys()
        assert 'ret_base' in params.keys()
        assert 'skip_first' in params.keys()

        sweep_mode = params['sweep_mode']
        interpolation = params['interpolation']
        self.cl_timeout = params['client_timeout']
        self.return_to_base = bool(params['ret_base'])
        self.skip_first = bool(params['skip_first'])

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
        assert not self.confirmed
        ret = 'RETURN' if self.return_to_base else 'NOT RETURN'
        skip = 'SKIP' if self.skip_first else 'NOT SKIP'
        html_dict = {'sweep_mode': self.mode, 'interpolation': self.interpolation,
                     'vals': [f' {v:.0f}' for v in self.sweep_array],
                     'cl_timeout': self.cl_timeout, 'ret_base': ret, 'skip_first': skip}

        if self.mode == 'direct-power' or self.mode == '':
            html_dict['therm_time'] = self.therm_time

        self.html_dict = html_dict

    def confirm(self):
        assert not self.confirmed
        self.confirmed = True
        self.client_dict = {'abort_in_progress': False, 'confirmed': True, 'sweep_points': len(self.sweep_array),
                            'client_timeout': self.cl_timeout}
        xld_logger.info("TEMPERATURE CONTROL: Parameters set to broadcasted.")

    def start_sweep(self):
        assert not self.started and self.confirmed
        self.started = True
        self.client_dict = {'abort_in_progress': False, 'sweep_started': True, 'confirmed': True,
                            'sweep_points': len(self.sweep_array),
                            'client_timeout': self.cl_timeout}
        xld_logger.info("TEMPERATURE CONTROL: Sweep set to started.")

    def clear(self):
        self.mode = ''
        self.interpolation = ''
        self.cl_timeout = 0
        self.therm_time = 0
        self.sweep_array = np.zeros(1)
        self.html_dict = {}
        self.return_to_base = False
        self.params = {}
        self.confirmed = False
        self.started = False
        self.client_dict = {}

        self.generate_html_dict()
