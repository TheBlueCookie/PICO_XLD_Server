from temperature_sweep import TemperatureSweep

import numpy as np

powers = np.arange(0, 10, 5)

tsweep = TemperatureSweep(thermalization_time=5, power_array=powers, client_timeout=5)

tsweep.exec()
