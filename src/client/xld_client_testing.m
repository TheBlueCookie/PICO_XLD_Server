xld_client = XLDMeasClient('127.0.0.1', "Elias", "PICO", 5000, 5);
[n_sweep, timeout] = xld_client.openSession();
xld_client.getMXCTemp();

for i = 1:n_sweep
    xld_client.listen()
    pause(15)
    xld_client.stopped()
end

xld_client.closeSession();
