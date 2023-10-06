import json
import requests
from time import sleep


class XLDMeasClient:
    def __init__(self, server_ip: str, user: str, group: str, server_port: int = 5000, update_interval: int = 30):
        self.user = user
        self.group = group
        self.id = None
        self.server_ip = server_ip
        self.server_port = server_port
        self.http_ip_port = f'http://{server_ip}:{self.server_port}'
        self.listen_delay = 10
        self.running = False
        self.update_interval = update_interval

    @staticmethod
    def _generic_request(path: str, payload: dict = None):
        try:
            if payload is None:
                response = requests.get(path)
            else:
                headers = {'Content-Type': 'application/json'}
                response = requests.post(path, data=json.dumps(payload), headers=headers)
            response.raise_for_status()

            return response.json()

        except Exception as ex:
            print(ex)
            return

    def _make_endpoint(self, *args):
        return self.http_ip_port + '/' + '/'.join(args)

    def _register(self):
        payload = {'user': self.user, 'group': self.group}
        response = self._generic_request(path=self._make_endpoint('meas', 'register'), payload=payload)
        self.id = response['id']

    def _deregister(self):
        payload = {'id': self.id}
        response = self._generic_request(path=self._make_endpoint('meas', 'deregister'), payload=payload)
        return response['deregistered']

    def listen(self):
        while True:
            sleep(self.update_interval)
            payload = {'id': self.id}
            response = self._generic_request(path=self._make_endpoint('meas', 'signal'), payload=payload)
            print(f'Pinged server. Response: {response}')
            if response['signal'] == 'go':
                return True

    def _running_update(self, running):
        payload = {'id': self.id, 'running': running}
        response = self._generic_request(path=self._make_endpoint('meas', 'status', 'set'), payload=payload)
        self.running = bool(response['running'])

    def started(self):
        self._running_update(running=True)

    def stopped(self):
        self._running_update(running=False)

    def open_session(self):
        self._register()
        print(f"Registered at {self.server_ip}. API ID: {self.id}")

    def close_session(self):
        if self._deregister():
            print("Deregistered successfully.")

    def get_mxc_temp(self):
        response = self._generic_request(path= self._make_endpoint('temps', 'base'))

        return response['mxc_temp']
