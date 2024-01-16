from main import XLDMeasClient
from time import sleep

from passkey import xld_ip

client = XLDMeasClient(user='Elias', group='PICO', server_ip=xld_ip, update_interval=2)
n_sweep, _ = client.open_session()

print(n_sweep)

for i in range(n_sweep):
    if client.listen():
        print("Starting measurement")
    sleep(30)
    print(f"done with step {i+1}")
    client.stopped()

print("client stopped fully")
sleep(10)
client.close_session()
