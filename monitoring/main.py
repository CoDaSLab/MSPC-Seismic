import os
import sys
sys.path.insert(1, os.getcwd())

from datetime import datetime, timedelta, timezone
from data.pull import download_files
from data import fetch

now = datetime.now(timezone.utc).replace(tzinfo=None)
today = now.replace(hour=0, minute=0, second=0, microsecond=0)

# Si no se ha hecho ningun fetch hoy lo hacemos, para ubicar el nombre del archivo

# obtenemos el nombre de todos los sensores operativos buscando en la tabla de avaialble files por la fecha y
# quedándonos con el nombre de los sensores (y sus canales)

# descargamos los datos de hoy de todos los sensores
lp_sensors=[]
with open('data/stations_lp.dat', "r", newline='') as file:
    for line in file:
        lp_sensors.append(line.split()[0])
file.close()

download_files(today, now, lp_sensors, ['HHZ','HHE','HHN'])

# operamos 


# borramos los datos que ya no nos sirvan.


"""
Si usamos MSPC como en la demo del informe D1.3.1, lo que haríamos sería en todo momento tener datos en local de 6 días
de medida. 5 que usaríamos para train y el día que estamos evaluando en el presente.

Al cambiar de día y empezar el nuevo tendríamos que reentrenar el modelo, empezar a descargar los datos del día de hoy y borrar
los datos del primer día del antiguo train.
"""

