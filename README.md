# domoticz-AirHumidifier2-CA4
Domoticz plugin for Xiaomi Humidifier 2 (Model CA4)
* based on https://github.com/develop-dvs/domoticz-AirHumidifier2

## Installation
```
pip3 install -U python-miio
```

* Make sure your Domoticz instance supports Domoticz Plugin System - see more https://www.domoticz.com/wiki/Using_Python_plugins

* Get plugin data into DOMOTICZ/plugins directory
```
cd YOUR_DOMOTICZ_PATH/plugins
git clone https://github.com/tierman/domoticz-AirHumidifier2-CA4
```
Restart Domoticz
* Go to Setup > Hardware and create new Hardware with type: AirHumidifier2
* Enter name (it's up to you), user name and password if define. If not leave it blank

## Update
```
cd YOUR_DOMOTICZ_PATH/plugins/domoticz-AirHumidifier2-CA4
git pull
```
* Restart Domoticz

## Troubleshooting

In case of issues, mostly plugin not visible on plugin list, check logs if plugin system is working correctly. See Domoticz wiki for resolution of most typical installation issues http://www.domoticz.com/wiki/Linux#Problems_locating_Python
