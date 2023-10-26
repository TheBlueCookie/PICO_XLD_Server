from main import XLDMeasClient
from time import sleep

from passkey import xld_ip

client = XLDMeasClient(user='Elias', group='PICO', server_ip=xld_ip, update_interval=2)
client.open_session()

if client.listen():
    print("Starting measurement")

client.started()
sleep(60)
print("done")
client.stopped()
sleep(10)
client.close_session()
