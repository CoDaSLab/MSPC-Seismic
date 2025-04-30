# /data structure 

**ssh_guide.md** is a tutorial for creating an SSH key and using it to connect to a server.

**README.md**: This file.

**__init__.py** loads the scripts in /data when a Python script imports the folder as a module.

## /scripts

Contains scripts for downloading or checking data.

**clear.py** is used to delete the seismic data stored.

**data_check.py** contains functions that checks seismic data for availability.

**fdsn_download.py** contains functions for downloading data from FDSN (Federation of Digital Seismograph Networks) clients.

**interruptions.py** checks data for empty gaps and overlaps in the signals.


## /involcan

Seismological data from INVOLCÁN.

**fetch.py** checks the INVOLCÁN servers for new data, and adds metadata to **available_files.csv**.

**pull.py** downloads data from INVOLCÁN to the /mseed folder.

### /involcan/DAS

Data from the DAS.

### /involcan/mseed
Contains data from the involcan seismic sensors. Each of the folders inside corresponds to a specific sensor, year and channel/component of the sensor, with the follwoing syntax:

**/[sensor]\_[year]\_[channel]** -> eg. /PLPI\_2021\_HHZ

Within these folders are the seismic data files, each corresponding to a specific day of measurements, specified by the day of the year. The syntax is as follows:

**C7.[sensor]..[channel].D.[year].[day]** -> eg. C7.PA09..HHZ.D.2021.262

### /involcan/metadata
Contains meta-information of the data. 

**available_files.csv** is a registry of all the data files uploaded to the system.

**Available_times.csv** is a registry of the time periods that cointain information for each of the sensors.

**feature_log.csv** is a registry of the features extracted from the signals and the parameters used to do so.

**interruptions.csv** is a registry of the interruptions present in the signals from seismic sensors.

**scans.csv** is a registry of all the times seismic data were scanned for interruptions.

### /involcan/features
Contains the features extracted from the signals. The files inside are codified with a number id, following the syntax:

**[id].mat** -> eg. 231.mat

The **feature_log.csv** registry in _data/metadata_ contains details about the contents of each of the files.


## Other folders

When data or metadata is downloaded using **fdsn_download.py** from one of the available sources, a new folder inside /data is created for that source. Inside, /mseed and /metadata subfolders can be found.