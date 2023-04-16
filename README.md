## Introduction

Minescanner is an open-source tool for searching for Minecraft servers in IP ranges.

It parses [masscan](https://github.com/robertdavidgraham/masscan) report file and attempts to connect to each server and extract data (MOTD, player count, etc).

## Installation

Install [masscan](https://github.com/robertdavidgraham/masscan)

Download the latest IP to country database from [here](https://git.io/GeoLite2-Country.mmdb) and place it into `geoip` folder

Create venv:

```
python3 -m venv .venv
```

Activate venv:

```
source .venv/bin/activate
```

Install requirements:

```
pip3 install -r requirements.txt
```

Alternatively you can install them system-wide.

## Usage

First you need to scan IP ranges:

```
 sudo masscan -e <device> -p25565 --rate <rate> -iL in/<ranges list> -oL scanned/<filename>
```

You can find more information about masscan's usage on its [GitHub page](https://github.com/robertdavidgraham/masscan)

After scanning you can start minescanner using this command:

```
python3 minescanner.py scanned/<filename> out/<filename> -n <num of processes>
```

The default number of threads is 4, but I recommend setting 20-40 because it will save a lot of time.

Minescanner will start scanning and will write results in CSV format.
