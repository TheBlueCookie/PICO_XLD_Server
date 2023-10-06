from temperature_sweep import TemperatureSweep

import numpy as np

powers = np.arange(0, 10, 5)

tsweep = TemperatureSweep(thermalization_time=10, power_array=powers, client_timeout=30)

tsweep.exec()
