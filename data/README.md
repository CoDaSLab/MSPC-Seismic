# /data structure

**ivc.dat** is a handmade registry of the known seismic events in a given time period. It contains information about the date, time magnitude and location of the seismic events.

**stations_lp.dat** is a record of the different seismic sensors available to INVOLCÁN in La Palma.

**ssh_guide.md** is a tutorial for creating an SSH key and using it to connect to a server.

## /DAS
Contains data from the DAS

## /seismic
Contains data from the seismic sensors. Each of the folders inside corresponds to a specific sensor, year and channel/component of the sensor, with the follwoing syntax:

**/[sensor]\_[year]\_[channel]** -> eg. /PLPI\_2021\_HHZ

Within these folders are the seismic data files, each corresponding to a specific day of measurements, specified by the day of the year. The syntax is as follows:

**C7.[sensor]..[channel].D.[year].[day]** -> eg. C7.PA09..HHZ.D.2021.262

## /metadata
Contains meta-information of the data. 

**Available_files.csv** is a registry of all the data files uploaded to the system.

**Available_times.csv** is a registry of the time periods that cointain information for each of the sensors.

**feature_log.csv** is a registry of the features extracted from the signals and the parameters used to do so.

**interruptions.csv** is a registry of the interruptions present in the signals from seismic sensors.

**scans.csv** is a registry of all the times seismic data were scanned for interruptions.

## /features
Contains the features extracted from the signals. The files inside are codified with a number id, following the syntax:

**[id].mat** -> eg. 231.mat

The **feature_log.csv** registry in _data/metadata_ contains details about the contents of each of the files.

