# Venstar Thermostat Local API
#
# Author: getSurreal
#
"""
<plugin key="Venstar" name="Venstar Thermostat Local API" author="getSurreal and Wagner Oliveira" version="1.0" wikilink="http://www.domoticz.com/wiki/plugins/venstar.html" externallink="http://venstar.com/">
    <params>
        <param field="Address"  label="Address"  width="200px" required="true"  default="192.168.1.x"/>
        <param field="Port"     label="Port"     width="200px" required="true" default="80"/>
        <param field="Mode1"    label="Polling Period (seconds)" width="200px" required="true" default="60"/>
        <param field="Mode6"    label="Debug"    width="75px">
            <options>
                <option label="True"  value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
   </params>
</plugin>
"""
#        <param field="Username" label="Username" width="200px" required="false" default=""/>
#        <param field="Password" label="Password" width="200px" required="false" default=""/>


import Domoticz
import urllib.parse
import json
import base64
from datetime import datetime
import time
   
class BasePlugin:
    isConnected = False


    def __init__(self):
        return

    def onStart(self):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)
            Domoticz.Debug("onStart called")
            DumpConfig()            
            DumpSettings()

        self.VenstarConn = Domoticz.Connection(Name="Venstar", Transport="TCP/IP", Protocol="HTTP", Address=Parameters["Address"], Port=Parameters["Port"])
        self.VenstarConn.Connect()
        Domoticz.Heartbeat(int(Parameters["Mode1"]))

    def onStop(self):
        Domoticz.Debug("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Debug("onConnect called")
        if (Status == 0):
            self.isConnected = True
            if (1 not in Devices):
                Options = { "LevelActions": "||||", "LevelNames": "Off|Heat|Cool|Auto", "LevelOffHidden": "false", "SelectorStyle": "0" }
                Domoticz.Device(Name="Mode",  Unit=1, TypeName="Selector Switch", Switchtype=18, Image=16, Options=Options).Create()
            if (2 not in Devices):
                Options = { "LevelActions": "||||", "LevelNames": "Auto|On", "LevelOffHidden": "false", "SelectorStyle": "0" }
                Domoticz.Device(Name="Fan Mode",  Unit=2, TypeName="Selector Switch", Switchtype=18, Image=7, Options=Options).Create()
            if (3 not in Devices): Domoticz.Device(Name="Heat Setpoint", Unit=3, Type=242, Subtype=1).Create()
            if (4 not in Devices): Domoticz.Device(Name="Cool Setpoint", Unit=4, Type=242, Subtype=1).Create()
#            if (5 not in Devices): Domoticz.Device(Name="Dehum Setpoint", Unit=5, Type=244, Subtype=73, Switchtype=7).Create()
            if (6 not in Devices): Domoticz.Device(Name="Temperature", Unit=6, Type=80, Subtype=5).Create()
            if (7 not in Devices): Domoticz.Device(Name="Temp + Humidity", Unit=7, Type=82, Subtype=5).Create()
            if (8 not in Devices): Domoticz.Device(Name="Humidity", Unit=8, Type=81, Subtype=1).Create()
            if (9 not in Devices): Domoticz.Device(Name="Schedule", Unit=9, Type=244, Subtype=73).Create()
            if (10 not in Devices): Domoticz.Device(Name="Away Mode", Unit=10, Type=244, Subtype=73).Create()
        else:
            self.isConnected = False
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"])
            Domoticz.Debug("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+" with error: "+Description)

    def onMessage(self, Connection, Data):
        Domoticz.Debug("onMessage called")
        jsonStr = Data["Data"].decode("utf-8", "ignore")

        if "success" in jsonStr:
            return
        if "error" in jsonStr:
            Domoticz.Log(jsonStr)
            return

        data = json.loads(jsonStr) # parse json string to dictionary
        UpdateDevice(1,0,str(data['mode']*10))
        UpdateDevice(2,0,str(data['fan']*10))
        if (data['tempunits'] == 0): # If thermostat is in fahrenheit convert to celcius for domoticz
            UpdateDevice(3,0,str((data['heattemp'] -32)*5/9))
            UpdateDevice(4,0,str((data['cooltemp'] -32)*5/9))
            UpdateDevice(6,0,str((data['spacetemp']-32)*5/9))
            UpdateDevice(7,0,str((data['spacetemp']-32)*5/9)+";"+str(data['hum_setpoint'])+";1")
        else:
            UpdateDevice(3,0,str(data['heattemp']))
            UpdateDevice(4,0,str(data['cooltemp']))
            UpdateDevice(6,0,str(data['spacetemp']))
            UpdateDevice(7,0,str(data['spacetemp'])+";"+str(data['hum'])+";1")
#            UpdateDevice(5,0,str(data['dehum_setpoint']))
        UpdateDevice(8,data['hum'],"0")
        UpdateDevice(9,data['schedule'],"0")
        UpdateDevice(10,data['away'],"0")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(int(Level)))
        Domoticz.Debug("mode:"+str(int(Devices[1].sValue))+", fan:"+str(Devices[2].nValue)+", heattemp:"+str(float(Devices[3].sValue))+", cooltemp:"+str(float(Devices[4].sValue)) )

        if (Unit == 1): # mode
            mode_val = int(Level/10)
            UpdateDevice(Unit,0,Level)
        else:
            mode_val = int(int(Devices[1].sValue)/10)

        if (Unit == 2): # fan mode
            fan_val = int(Level/10)
            UpdateDevice(Unit,0,Level)
        else:
            fan_val = int(int(Devices[2].sValue)/10)

        if (Unit == 3): # heat temp
            heat_val = float(Level)
        else:
            heat_val = float(Devices[3].sValue)

        if (Unit == 4): # cool temp
            cool_val = float(Level)
        else:
            cool_val = float(Devices[4].sValue)

        if (Unit <= 4):
            params = "mode="+str(mode_val)+"&fan="+str(fan_val)+"&heattemp="+str(heat_val)+"&cooltemp="+str(cool_val)
            headers = { 'Content-Type': 'application/x-www-form-urlencoded', \
                        'Content-Length' : "%d"%(len(params)) }
            sendData = { 'Verb' : 'POST',
                         'URL'  : '/control',
                         'Headers' : headers,
                         'Data': params }
            self.VenstarConn.Send(sendData)

        if (Unit == 9): # schedule
            if (Command == "On"):
                params = "schedule=1"
                UpdateDevice(Unit,1,"0")

            elif (Command == "Off"):
                params = "schedule=0"
                UpdateDevice(Unit,0,"0")

            headers = { 'Content-Type': 'application/x-www-form-urlencoded', \
                        'Content-Length' : "%d"%(len(params)) }
            sendData = { 'Verb' : 'POST',
                         'URL'  : '/settings',
                         'Headers' : headers,
                         'Data': params }
            self.VenstarConn.Send(sendData)

        if (Unit == 10): # away
            if (Command == "On"):
                params = "away=1"
                UpdateDevice(Unit,1,"0")

            elif (Command == "Off"):
                params = "away=0"
                UpdateDevice(Unit,0,"0")

            headers = { 'Content-Type': 'application/x-www-form-urlencoded', \
                        'Content-Length' : "%d"%(len(params)) }
            sendData = { 'Verb' : 'POST',
                         'URL'  : '/settings',
                         'Headers' : headers,
                         'Data': params }
            self.VenstarConn.Send(sendData)

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Debug("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called")
        self.isConnected = False

    def onHeartbeat(self):
        Domoticz.Debug("onHeartbeat called")
        if (self.VenstarConn.Connected() == True):
            url = '/query/info'
            sendData = { 'Verb' : 'GET',
                         'URL'  : url,
                         'Headers' : { 'Content-Type': 'text/xml; charset=utf-8', \
                                       'Connection': 'keep-alive', \
                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                       'Host': Parameters["Address"]+":"+Parameters["Port"], \
                                       'User-Agent':'Domoticz/1.0'
                                    },
                        }
            self.VenstarConn.Send(sendData)
        else:
            Domoticz.Connect()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

# Generic helper functions
def DumpConfig():
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

def DumpSettings():
    for x in Settings:
        Domoticz.Debug( "'" + x + "':'" + str(Settings[x]) + "'")
    return

def stringToBase64(s):
    return base64.b64encode(s.encode('utf-8')).decode("utf-8")

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    if (Unit in Devices):
        # Update the device before it times out even if the values are the same
        SensorTimeout = Settings['SensorTimeout']

        # try/catch due to http://bugs.python.org/issue27400
        try:
            timeDiff = datetime.now() - datetime.strptime(Devices[Unit].LastUpdate,'%Y-%m-%d %H:%M:%S')
        except TypeError:
            timeDiff = datetime.now() - datetime(*(time.strptime(Devices[Unit].LastUpdate,'%Y-%m-%d %H:%M:%S')[0:6]))

        timeDiffMinutes = (timeDiff.seconds/60)%60
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue or timeDiffMinutes+5 > int(SensorTimeout)):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[Unit].Name+")")
    return


