# A Python plugin for Domoticz to access AirHumidifier2 (CA4)
#
# Author: tierman
#
# v 0.1

"""
<plugin key="AirHumidifier2" name="AirHumidifier2" author="tierman" version="0.1" wikilink="https://github.com/rytilahti/python-miio" externallink="https://github.com/tierman/domoticz-AirHumidifier2-CA4">
    <params>
		<param field="Address" label="IP Address" width="200px" required="true" default="127.0.0.1"/>
		<param field="Mode1" label="AirHumidifier Token" default="" width="400px" required="true"  />
		<param field="Mode2" label="Model" width="160px">
			<options>
				<option label="zhimi.humidifier.ca4" value="zhimi.humidifier.ca4" default="true"/>
			</options>
		</param>
                <param field="Mode3" label="Check every x minutes" width="40px" default="15" required="true" />
		<param field="Mode6" label="Debug" width="75px">
			<options>
				<option label="True" value="Debug"/>
				<option label="False" value="Normal" default="true" />
			</options>
		</param>
    </params>
</plugin>
"""


import Domoticz
import datetime
from miio.airhumidifier_miot import OperationMode, LedBrightness
import miio.airhumidifier

L10N = {
    'en': { },
    'pl': {
        "Humidity":
            "Wilgotność",
        "Target Humidity":
            "Docelowa wilgotność",
        "Temperature":
            "Temperatura",
        "Fan Speed":
            "Prędkość wiatraka",
        "Favorite Fan Level":
            "Ulubiona prędkość wiatraka",
        "Device Unit=%(Unit)d; Name='%(Name)s' already exists":
            "Urządzenie Unit=%(Unit)d; Name='%(Name)s' już istnieje",
        "Creating device Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d":
            "Tworzę urządzenie Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d",
        "%(Vendor)s - %(Address)s, %(Locality)s<br/>Station founder: %(sensorFounder)s":
            "%(Vendor)s - %(Address)s, %(Locality)s<br/>Sponsor stacji: %(sensorFounder)s",
        "%(Vendor)s - %(Locality)s %(StreetNumber)s<br/>Station founder: %(sensorFounder)s":
            "%(Vendor)s - %(Locality)s %(StreetNumber)s<br/>Sponsor stacji: %(sensorFounder)s",
        "Great humidity":
            "Bardzo dobra wilgotność",
        "Good humidity":
            "Dobra wilgotność",
        "Poor humidity":
            "Przeciętna wilgotność",
        "Bad humidity":
            "Zła wilgotność",
        "Sensor id (%(sensor_id)d) not exists":
            "Sensor (%(sensor_id)d) nie istnieje",
        "Not authorized":
            "Brak autoryzacji",
        "Starting device update":
            "Rozpoczynanie aktualizacji urządzeń",
        "Update unit=%d; nValue=%d; sValue=%s":
            "Aktualizacja unit=%d; nValue=%d; sValue=%s",
        "Awaiting next pool: %s":
            "Oczekiwanie na następne pobranie: %s",
        "Next pool attempt at: %s":
            "Następna próba pobrania: %s",
        "Unrecognized error: %s":
            "Nierozpoznany błąd: %s"
    }
}

def translate(key):
    try:
        return L10N[Settings["Language"]][key]
    except KeyError:
        return key


def humiInstance(addressIp, token):
    return miio.AirHumidifierMiot(addressIp, token, 0, 0, True)


class UnauthorizedException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class SensorNotFoundException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class ConnectionErrorException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message


class HumidifierStatus:
    def __init__(self, addressIp, token):
        token = str(token)
        MyHumidifier = humiInstance(addressIp, token)
        Domoticz.Debug("Calling: ip: " + addressIp + ", token: " + token)

        data = str(MyHumidifier.status().data)
        Domoticz.Debug("Result data: " + data)

        data = data[1:-1]
        Domoticz.Debug("Result data 2: " + data)

        data = data.replace(' ', '').replace('\'', '')
        data = dict(item.split(":") for item in data.split(","))
        Domoticz.Debug("Result data: " + str(data))

        self.power = data["power"]
        self.fault = data["fault"]
        self.humidity = int(data["humidity"])
        self.temperature = data["temperature"]
        self.mode = data["mode"]
        self.target_humidity = int(data["target_humidity"])
        self.water_level=data["water_level"]
        self.dry = data["dry"]
        self.use_time = data["use_time"]
        self.speed_level = data["speed_level"]
        self.fahrenheit = data["fahrenheit"]
        self.buzzer = data["buzzer"]
        self.led_brightness = data["led_brightness"]
        self.child_lock = data["child_lock"]
        self.actual_speed = data["actual_speed"]
        self.power_time = data["power_time"]
        #self.clean_mode = data["clean_mode"]

        for item in data.keys():
            Domoticz.Debug(str(item) + " => " + str(data[item]))


class BasePlugin:
    enabled = False

    def __init__(self):
        # Consts
        self.version = "0.2"

        self.EXCEPTIONS = {
            "SENSOR_NOT_FOUND":     1,
            "UNAUTHORIZED":         2,
        }

        self.debug = False
        self.inProgress = False

        # Do not change below UNIT constants!
        self.UNIT_AIR_QUALITY_INDEX     = 1
        self.UNIT_AIR_POLLUTION_LEVEL   = 2
        self.UNIT_TEMPERATURE           = 3
        self.UNIT_HUMIDITY              = 4
        self.UNIT_ACTUAL_MOTOR_SPEED    = 5
        self.UNIT_AVARAGE_AQI           = 6

        self.UNIT_POWER_CONTROL         = 10
        self.UNIT_MODE_CONTROL          = 11
        self.UNIT_MOTOR_SPEED_FAVORITE  = 12

        self.UNIT_TARGET_HUMIDITY       = 13
        self.UNIT_CHILD_LOCK            = 14
        self.UNIT_DRY_MODE              = 15
        #self.UNIT_CLEAN_MODE            = 16
        self.UNIT_BUZZER                = 17
        self.UNIT_LED_BRIGHTNESS        = 18

        self.UNIT_WATER_LEVEL           = 20


        self.nextpoll = datetime.datetime.now()
        return


    def onStart(self):
        Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == 'Debug':
            self.debug = True
            Domoticz.Debugging(1)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)

        Domoticz.Heartbeat(20)
        self.pollinterval = int(Parameters["Mode3"]) * 60


        self.variables = {
            self.UNIT_TEMPERATURE:          {"Name": translate("Temperature"),      "TypeName": "Temperature",  "Used": 0, "nValue": 0, "sValue": None},
            #self.UNIT_ACTUAL_MOTOR_SPEED:   {"Name": translate("Temperature"),      "TypeName": "Temperature",       "Used": 0, "nValue": 0, "sValue": None},
            self.UNIT_HUMIDITY:             {"Name": translate("Humidity"),         "TypeName": "Humidity",     "Used": 0, "nValue": 0, "sValue": None},
            self.UNIT_WATER_LEVEL:          {"Name": translate("Water level"),      "TypeName": "Percentage",   "Used": 0, "nValue": 0, "sValue": None},
            self.UNIT_TARGET_HUMIDITY:      {"Name": translate("Target Humidity"),  "TypeName": "Humidity",     "Used": 0, "nValue": 0, "sValue": None}
        }

        #create switches
        if (len(Devices) == 0):
            Domoticz.Device(Name=translate("Power"), Unit=self.UNIT_POWER_CONTROL, TypeName="Switch", Image=7).Create()
            Options = {"LevelActions": "||||",
                       "LevelNames": "Auto|Silent|Medium|High",
                       "LevelOffHidden": "false",
                       "SelectorStyle": "0"
                      }
            Domoticz.Device(Name=translate("Source"), Unit=self.UNIT_MODE_CONTROL, TypeName="Selector Switch", Switchtype=18,
                            Image=7,
                            Options=Options).Create()
            HumidityTarget = {"LevelActions": "|||",
                            "LevelNames": "50%|60%|70%",
                            "LevelOffHidden": "false",
                            "SelectorStyle": "0"}
            Domoticz.Device(Name=translate("Target Humidity"), Unit=self.UNIT_TARGET_HUMIDITY, TypeName="Selector Switch", Switchtype=18,
                            Image=7,
                            Options=HumidityTarget).Create()
            Domoticz.Log("Devices created.")
        else:
            Domoticz.Debug("len(Devices): " + str(len(Devices)))
            Domoticz.Debug("Devices: " + str(Devices))

            self.createChildLockSwitch()
            self.createDryModeSwitch()
            self.createBuzzerSwitch()
            self.createLedBrightnessSwitch()

            if (self.UNIT_POWER_CONTROL in Devices):
                Domoticz.Log("Device UNIT_POWER_CONTROL with id " + str(self.UNIT_POWER_CONTROL) + " exist")
            else:
                Domoticz.Device(Name="Power", Unit=self.UNIT_POWER_CONTROL, TypeName="Switch", Image=7).Create()

            if (self.UNIT_MODE_CONTROL in Devices):
                Domoticz.Log("Device UNIT_MODE_CONTROL with id " + str(self.UNIT_MODE_CONTROL) + " exist")
            else:
                Options = {"LevelActions": "||||",
                           "LevelNames": "Auto|Silent|Medium|High",
                           "LevelOffHidden": "false",
                           "SelectorStyle": "0"
                           }
                Domoticz.Device(Name="Mode", Unit=self.UNIT_MODE_CONTROL, TypeName="Selector Switch", Switchtype=18, Image=7, Options=Options).Create()

            if (self.UNIT_TARGET_HUMIDITY in Devices):
                Domoticz.Log("Device UNIT_TARGET_HUMIDITY with id " + str(self.UNIT_TARGET_HUMIDITY) + " exist")
            else:
                HumidityTarget = {"LevelActions": "|||",
                                "LevelNames": "50%|60%|70%",
                                "LevelOffHidden": "false",
                                "SelectorStyle": "0"}
                Domoticz.Device(Name="Target Humidity", Unit=self.UNIT_TARGET_HUMIDITY, TypeName="Selector Switch", Switchtype=18, Image=7, Options=HumidityTarget).Create()

        self.onHeartbeat(fetch=False)

    def createChildLockSwitch(self):
        if (self.UNIT_CHILD_LOCK in Devices):
            Domoticz.Log("Device UNIT_CHILD_LOCK with id " + str(self.UNIT_CHILD_LOCK) + " exist")
        else:
            Domoticz.Device(Name="Child lock", Unit=self.UNIT_CHILD_LOCK, TypeName="Switch", Image=7).Create()

    def createDryModeSwitch(self):
        if (self.UNIT_DRY_MODE in Devices):
            Domoticz.Log("Device UNIT_DRY_MODE with id " + str(self.UNIT_DRY_MODE) + " exist")
        else:
            Domoticz.Device(Name="Dry mode", Unit=self.UNIT_DRY_MODE, TypeName="Switch", Image=7).Create()

    def createBuzzerSwitch(self):
        if (self.UNIT_BUZZER in Devices):
            Domoticz.Log("Device UNIT_BUZZER with id " + str(self.UNIT_BUZZER) + " exist")
        else:
            Domoticz.Device(Name="Buzzer", Unit=self.UNIT_BUZZER, TypeName="Switch", Image=7).Create()

    def createLedBrightnessSwitch(self):
        if (self.UNIT_LED_BRIGHTNESS in Devices):
            Domoticz.Log("Device UNIT_LED_BRIGHTNESS with id " + str(self.UNIT_LED_BRIGHTNESS) + " exist")
        else:
            ledBrightness = {"LevelActions": "|||",
                              "LevelNames": "Off|Dim|Bright",
                              "LevelOffHidden": "false",
                              "SelectorStyle": "0"}
            Domoticz.Device(Name="Led brightness", Unit=self.UNIT_LED_BRIGHTNESS, TypeName="Selector Switch", Switchtype=18, Image=7, Options=ledBrightness).Create()

    def onStop(self):
        Domoticz.Log("onStop called")
        Domoticz.Debugging(0)

    def onConnect(self, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        humidifier = humiInstance(Parameters["Address"], Parameters["Mode1"])

        if Unit == self.UNIT_POWER_CONTROL and str(Command).upper() == "ON":
            humidifier.info()
            humidifier.on()
        elif Unit == self.UNIT_POWER_CONTROL and str(Command).upper() == "OFF":
            humidifier.off()
        elif Unit == self.UNIT_MODE_CONTROL and int(Level) == 10:
            humidifier.set_mode(OperationMode.Low)
        elif Unit == self.UNIT_MODE_CONTROL and int(Level) == 0:
            humidifier.set_mode(OperationMode.Auto)
        elif Unit == self.UNIT_MODE_CONTROL and int(Level) == 20:
            humidifier.set_mode(OperationMode.Mid)
        elif Unit == self.UNIT_MODE_CONTROL and int(Level) == 30:
            humidifier.set_mode(OperationMode.High)
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 0:
            humidifier.set_led_brightness(LedBrightness.Off)
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 10:
            humidifier.set_led_brightness(LedBrightness.Dim)
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 20:
            humidifier.set_led_brightness(LedBrightness.Bright)
        elif Unit == self.UNIT_TARGET_HUMIDITY and int(Level) == 0:
            humidifier.set_target_humidity(50)
        elif Unit == self.UNIT_TARGET_HUMIDITY and int(Level) == 10:
            humidifier.set_target_humidity(60)
        elif Unit == self.UNIT_TARGET_HUMIDITY and int(Level) == 20:
            humidifier.set_target_humidity(70)
        elif Unit == self.UNIT_CHILD_LOCK and str(Command).upper() == "ON":
            humidifier.set_child_lock(True)
        elif Unit == self.UNIT_CHILD_LOCK and str(Command).upper() == "OFF":
            humidifier.set_child_lock(False)
        elif Unit == self.UNIT_DRY_MODE and str(Command).upper() == "ON":
            humidifier.set_dry(True)
        elif Unit == self.UNIT_DRY_MODE and str(Command).upper() == "OFF":
            humidifier.set_dry(False)
#        elif Unit == self.UNIT_CLEAN_MODE and str(Command).upper() == "ON":
#            humidifier.set_clean_mode(True)
#        elif Unit == self.UNIT_CLEAN_MODE and str(Command).upper() == "OFF":
#            humidifier.set_clean_mode(False)
        elif Unit == self.UNIT_BUZZER and str(Command).upper() == "ON":
            humidifier.set_buzzer(True)
        elif Unit == self.UNIT_BUZZER and str(Command).upper() == "OFF":
            humidifier.set_buzzer(False)
        else:
            Domoticz.Log("onCommand called not found")

        if Parameters["Mode6"] == 'Debug':
            data = str(humidifier.status().data)
            Domoticz.Debug(data)

        self.onHeartbeat(fetch=True)

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self):
        Domoticz.Log("onDisconnect called")

    def postponeNextPool(self, seconds=3600):
        self.nextpoll = (datetime.datetime.now() + datetime.timedelta(seconds=seconds))
        return self.nextpoll

    def createDevice(self, key=None):
        """create Domoticz virtual device"""

        def createSingleDevice(key):
            """inner helper function to handle device creation"""

            item = self.variables[key]
            _unit = key
            _name = item['Name']

            # skip if already exists
            if _unit in Devices:
                Domoticz.Debug(translate("Device Unit=%(Unit)d; Name='%(Name)s' already exists") % {'Unit': _unit, 'Name': _name})
                return

            try:
                _options = item['Options']
            except KeyError:
                _options = {}

            _typename = item['TypeName']

            try:
                _used = item['Used']
            except KeyError:
                _used = 0

            try:
                _image = item['Image']
            except KeyError:
                _image = 0

            Domoticz.Debug(translate("Creating device Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d") % {'Name': _name, 'Unit': _unit, 'TypeName': _typename, 'Used': _used})
            Domoticz.Device(Name=_name, Unit=_unit, TypeName=_typename, Image=_image, Options=_options, Used=_used).Create()

        if key:
            createSingleDevice(key)
        else:
            for k in self.variables.keys():
                createSingleDevice(k)


    def onHeartbeat(self, fetch=False):
        Domoticz.Debug("onHeartbeat called")
        now = datetime.datetime.now()

        if fetch == False:
            if self.inProgress or (now < self.nextpoll):
                Domoticz.Debug(translate("Awaiting next pool: %s") % str(self.nextpoll))
                return

        # Set next pool time
        self.postponeNextPool(seconds=self.pollinterval)

        try:
            # check if another thread is not running
            # and time between last fetch has elapsed
            self.inProgress = True

            res = self.sensor_measurement(Parameters["Address"], Parameters["Mode1"])

            self.updateHumudity(res)
            self.updateHumidityStatus(res)
            self.updateUnitTemperature(res)
            self.updateWaterLevel(res)
            self.updatePowerStatus(res)
            self.updateChildLock(res)
            self.updateDryMode(res)
            self.updateMode(res)
            self.updateLedBrightness(res)
            self.updateBuzzer(res)
           # self.updateUnitActualMotorSpeed(res)
#             self.updateCleanMode(res)

            Domoticz.Log("Calling: self.doUpdate()")
            self.doUpdate()
        except Exception as e:
            Domoticz.Error(translate("Unrecognized error: %s") % str(e))
        finally:
            self.inProgress = False
        if Parameters["Mode6"] == 'Debug':
            Domoticz.Debug("onHeartbeat finished")
        return True

    def updateHimidity(self, res):
        try:
            self.variables[self.UNIT_HUMIDITY]['sValue'] = str(res.humidity)
        except KeyError:
            pass  # No humidity value

    def updateHumidityStatus(self, res):
        try:
            humidity = int(round(res.humidity))
            if humidity >= 60 and humidity <= 70:
                pollutionText = translate("Great humidity")
                humidity_status = 1 # great
            elif (humidity >= 45 and humidity < 60) or (humidity > 70 and humidity <= 80):
                pollutionText = translate("Good humidity")
                humidity_status = 0 # normal
            elif (humidity >= 30 and humidity < 45) or (humidity > 80):
                pollutionText = translate("Poor humidity")
                humidity_status = 3 # wet/poor
            elif humidity < 30:
                pollutionText = translate("Bad humidity")
                humidity_status = 2 # dry

            self.variables[self.UNIT_HUMIDITY]['nValue'] = humidity
            self.variables[self.UNIT_HUMIDITY]['sValue'] = str(humidity_status)
        except KeyError:
            pass  # No humidity value

    def updateUnitTemperature(self, res):
        try:
            Domoticz.Debug("updateUnitTemperature: " + str(res.temperature))
            #self.variables[self.UNIT_TEMPERATURE]['nValue'] = res.temperature
            self.variables[self.UNIT_TEMPERATURE]['sValue'] = str(res.temperature)
        except KeyError:
            pass  # No temperature value

#    def updateUnitActualMotorSpeed(self, res):
#        try:
#            self.variables[self.UNIT_ACTUAL_MOTOR_SPEED]['sValue'] = res.actual_speed
#        except KeyError:
#            pass  # No temperature value

    def updateWaterLevel(self, res):
        try:
            # https://github.com/aholstenson/miio/issues/131#issuecomment-376881949
            # Max depth is 120. That's why value -> value / 1.2.
            water_level = int(res.water_level)/1.2
            self.variables[self.UNIT_WATER_LEVEL]['nValue'] = int(water_level)
            self.variables[self.UNIT_WATER_LEVEL]['sValue'] = water_level
        except KeyError:
            pass  # No water level value

    def updatePowerStatus(self, res):
        try:
            Domoticz.Debug("updatePowerStatus -> res.power: " + res.power)
            if "True" == str(res.power):
                Domoticz.Debug("res.power: True")
                UpdateDevice(self.UNIT_POWER_CONTROL, True, "AirHumidifier ON")
            elif "False" == str(res.power):
                Domoticz.Debug("res.power: False")
                UpdateDevice(self.UNIT_POWER_CONTROL, False, "AirHumidifier OFF")
        except KeyError:
            pass  # No power value

    def updateChildLock(self, res):
        try:
            if "True" == str(res.child_lock):
                UpdateDevice(self.UNIT_CHILD_LOCK, True, "Child lock ON")
            elif "False" == str(res.child_lock):
                UpdateDevice(self.UNIT_CHILD_LOCK, False, "Child lock OFF")
        except KeyError:
            pass  # No power value

    def updateDryMode(self, res):
        try:
            if "True" == str(res.dry):
                UpdateDevice(self.UNIT_DRY_MODE, True, "Dry mode ON")
            elif "False" == str(res.dry):
                UpdateDevice(self.UNIT_DRY_MODE, False, "Dry mode OFF")
        except KeyError:
            pass  # No power value

    def updateCleanMode(self, res):
        try:
            if "True" == str(res.clean):
                UpdateDevice(self.UNIT_CLEAN_MODE, True, "Clean mode ON")
            elif "False" == str(res.clean):
                UpdateDevice(self.UNIT_CLEAN_MODE, False, "Clean mode OFF")
        except KeyError:
            pass  # No power value

    def updateBuzzer(self, res):
        try:
            if "True" == str(res.buzzer):
                UpdateDevice(self.UNIT_BUZZER, True, "Buzzer ON")
            elif "False" == str(res.buzzer):
                UpdateDevice(self.UNIT_BUZZER, False, "Buzzer OFF")
        except KeyError:
            pass  # No power value

    def updateLedBrightness(self, res):
        try:
            Domoticz.Debug("updateLedBrightness: res.led_brightness: " + res.led_brightness)
            ledBrightness = int(res.led_brightness)

            if ledBrightness == 0:
                UpdateDevice(self.UNIT_LED_BRIGHTNESS, 0, '0')
            elif ledBrightness == 1:
                UpdateDevice(self.UNIT_LED_BRIGHTNESS, 10, '10')
            elif ledBrightness == 2:
                UpdateDevice(self.UNIT_LED_BRIGHTNESS, 20, '20')
            else:
                Domoticz.Debug("LED: res.mode - something wrong...")
        except KeyError:
            pass  # No mode value

    def updateMode(self, res):
        try:
            Domoticz.Debug("res.mode: " + res.mode)
            if int(res.mode) == 0: #"OperationMode.Auto":
                Domoticz.Debug("res.mode : 0")
                UpdateDevice(self.UNIT_MODE_CONTROL, 0, '0')
            elif int(res.mode) == 1: #"OperationMode.Silent":
                Domoticz.Debug("res.mode : 1")
                UpdateDevice(self.UNIT_MODE_CONTROL, 10, '10')
            elif int(res.mode) == 2: #"OperationMode.Medium":
                Domoticz.Debug("res.mode : 2")
                UpdateDevice(self.UNIT_MODE_CONTROL, 20, '20')
            elif int(res.mode) == 3: #"OperationMode.High":
                Domoticz.Debug("res.mode : 3")
                UpdateDevice(self.UNIT_MODE_CONTROL, 30, '30')
            else:
                Domoticz.Debug("res.mode - something wrong...")
        except KeyError:
            pass  # No mode value

    def updateHumudity(self, res):
        try:
            Domoticz.Debug("res.target_humidity: " + str(res.target_humidity))
            humidity = int(res.target_humidity)
            if humidity == 50:
                UpdateDevice(self.UNIT_TARGET_HUMIDITY, 0, '0')
            elif humidity == 60:
                UpdateDevice(self.UNIT_TARGET_HUMIDITY, 10, '10')
            elif humidity == 70:
                UpdateDevice(self.UNIT_TARGET_HUMIDITY, 20, '20')
        except KeyError:
            pass  # No mode value

    def doUpdate(self):
        Domoticz.Log(translate("Starting device update: " + str(self.variables)))
        for unit in self.variables:
            nV = self.variables[unit]['nValue']
            sV = self.variables[unit]['sValue']

            # cast float to str
            if isinstance(sV, float):
                sV = str(float("{0:.0f}".format(sV))).replace('.', ',')

            # Create device if required
            if sV:
                self.createDevice(key=unit)
                if unit in Devices:
                    Domoticz.Log(translate("Update unit=%d; nValue=%d; sValue=%s") % (unit, nV, sV))
                    Devices[unit].Update(nValue=nV, sValue=sV)

    def sensor_measurement(self, addressIP, token):
        """current sensor measurements"""
        return HumidifierStatus(addressIP, token)

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Status, Description):
    global _plugin
    _plugin.onConnect(Status, Description)

def onMessage(Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect():
    global _plugin
    _plugin.onDisconnect()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def UpdateDevice(Unit, nValue, sValue):
    Domoticz.Log("try to update: Unit: " + str(Unit) + ", nValue: " + str(nValue) + ", sValue: " + str(sValue))
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update " + str(nValue) + ":'" + str(sValue) + "' (" + Devices[Unit].Name + ")")
    return
