from dataclasses import dataclass
import secrets
from datetime import datetime
from multiprocessing import Lock
import sqlite3 as sq
import logging
import os

from measurements import WAIT, GO, RUNNING, CRASHED
from passkey import data_dir, db_filename

xld_logger = logging.getLogger('waitress')


@dataclass
class ServerDB:
    db_name: str = os.path.join(data_dir, db_filename)
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

    def _exec_db_command(self, cmd: str, params: tuple = ()):
        with sq.connect(self.db_name) as con:
            return con.execute(cmd, params)

    def _info(self, msg):
        xld_logger.info(f"DATABASE OPERATION: {msg}")

    def _warning(self, msg):
        xld_logger.warning(f"DATABASE OPERATION: {msg}")

    def prep_tables(self):
        self._exec_db_command('''CREATE TABLE if not exists clients
        (id CHAR(16) PRIMARY KEY,
        user_name VARCHAR,
        w_group VARCHAR,
        start_time DATETIME,
        progress NUMERIC,
        running BOOLEAN,
        signal VARCHAR,
        crashed BOOLEAN DEFAULT 0)''')
        self._exec_db_command('''CREATE TABLE if not exists temps
        (channel NUMERIC PRIMARY KEY,
        temp NUMERIC,
        tstamp DATETIME)''')
        self._exec_db_command('''CREATE TABLE if not exists heaters
        (h_ind NUMERIC PRIMARY KEY,
        power NUMERIC,
        tstamp DATETIME)''')

        self._info("Created database tables.")

    def _get_all_ids(self):
        cursor = self._exec_db_command("SELECT id FROM clients")
        ids = [row[0] for row in cursor]

        return ids

    def register_measurement(self, user: str, group: str):
        with self.meas_lock:
            ids = self._get_all_ids()
            unique = False
            while not unique:
                token = secrets.token_urlsafe(16)
                if token not in ids:
                    unique = True

            self._exec_db_command("INSERT INTO clients (id, user_name, w_group, start_time, progress, running, signal)"
                                  "VALUES (?, ?, ?, ?, ?, ?, ?)", (token, user, group, datetime.now(), -1, False, WAIT))

            self._info(f"Measurement registered by {user} ({group}) with ID {token}.")
        return token

    def deregister_measurement(self, meas_id: str):
        with self.meas_lock:
            if meas_id in self._get_all_ids():
                self._exec_db_command("DELETE FROM clients WHERE id = ?;", (meas_id,))

            self._info(f"Measurement with ID {meas_id} deregistered.")

    def get_html_meas_dict(self):
        meas = []
        with self.meas_lock:
            cursor = self._exec_db_command("SELECT * FROM clients")
            for row in cursor:
                meas.append({'id': row[0], 'user': row[1], 'group': row[2], 'timestamp': row[3], 'progress': row[4],
                             'running': row[5], 'signal': row[6], 'crashed': row[7]})

            return meas

    def get_single_meas_dict(self, meas_id):
        with self.meas_lock:
            cursor = self._exec_db_command("SELECT * FROM clients where id = ?", (meas_id, ))
            for row in cursor:
                return {'id': row[0], 'user': row[1], 'group': row[2], 'timestamp': row[3], 'progress': row[4],
                        'running': row[5], 'signal': row[6], 'crashed': row[7]}

    def set_meas_status(self, meas_id: str, status: bool):
        with self.meas_lock:
            if meas_id in self._get_all_ids():
                self._exec_db_command("UPDATE clients SET running = ? WHERE id = ?", (status, meas_id))
                self._info(f"Set measurement {meas_id} to running = {status}.")

                if status:
                    self._exec_db_command("UPDATE clients SET signal = ? WHERE id = ?", (RUNNING, meas_id))
                    self._info(f"Set measurement {meas_id} to signal = {RUNNING}.")

                else:
                    self._exec_db_command("UPDATE clients SET signal = ? WHERE id = ?", (WAIT, meas_id))
                    self._info(f"Set measurement {meas_id} to signal = {WAIT}.")

                return status

    def set_meas_as_crashed(self, meas_id):
        with self.meas_lock:
            if meas_id in self._get_all_ids():
                self._exec_db_command("UPDATE clients SET crashed = ? WHERE id = ?", (True, meas_id))
                self._warning(f"Marked measurement {meas_id} as crashed.")

    def write_temp(self, channel: int, val: float, timestamp: datetime = datetime.now()):
        with self.temp_lock:
            self._exec_db_command("INSERT INTO temps (channel, temp, tstamp)"
                                  "VALUES (?, ?, ?)"
                                  "ON CONFLICT(channel)"
                                  "DO UPDATE SET temp = ?, tstamp = ?",
                                  (channel, val, timestamp, val, timestamp))

            self._info(f'Written temp = {val} to channel {channel}.')

    def read_temp(self, channel: int):
        with self.temp_lock:
            cursor = self._exec_db_command(
                "SELECT temp from temps WHERE channel = ?", (channel,))
            ts = [row[0] for row in cursor]
            if ts:
                return ts[0]

            else:
                return 0

    def write_heater(self, index: int, val: float, timestamp: datetime = datetime.now()):
        with self.heater_lock:
            self._exec_db_command("INSERT INTO heaters (h_ind, power, tstamp)"
                                  "VALUES (?, ?, ?)"
                                  "ON CONFLICT(h_ind)"
                                  "DO UPDATE SET power = ?, tstamp = ?",
                                  (index, val, timestamp, val, timestamp))

            self._info(f'Written power = {val} to heater {index}.')

    def read_heater(self, index: int):
        with self.heater_lock:
            cursor = self._exec_db_command(
                "SELECT power from heaters WHERE h_ind = ?", (index,))
            ts = [row[0] for row in cursor]
            if ts:
                return ts[0]

            else:
                return 0

    def get_meas_signal(self, meas_id):
        with self.meas_lock:
            if meas_id in self._get_all_ids():
                cursor = self._exec_db_command("SELECT signal from clients WHERE id = ?", (meas_id,))
                return [row[0] for row in cursor][0]

    def get_all_meas_signals(self):
        with self.meas_lock:
            cursor = self._exec_db_command("SELECT signal, crashed from clients WHERE 1")
            return [(row[0], row[1]) for row in cursor]

    def set_all_meas_to_go(self):
        with self.meas_lock:
            self._exec_db_command("UPDATE clients SET signal = ? WHERE 1", (GO,))
            self._info("Set all measurements to signal = GO.")
