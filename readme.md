# C3
A native Python library for communicating with the ZKTeco ZKAccess C3 Access Control Panels.

This library intends to implement the same functionality as provided by the ZKAccess C3 PullSDK API, but using native Python only.
The full documentation of the official SDK is available from [ZKTeco](https://www.zkteco.com.pk/SoftwareDevelopmentKit/pullsdk).
A snapshot can be found at [licjapodaca/Pull-SDK-Demo](https://github.com/licjapodaca/Pull-SDK-Demo) or [hmojicag/ZKTecoStandAlonePullSDK](https://github.com/hmojicag/ZKTecoStandAlonePullSDK).

[![GPLv3 License](https://img.shields.io/badge/License-GPL%20v3-yellow.svg)](https://opensource.org/licenses/)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/vwout/zkaccess-c3-py?style=flat-square)
[![PyPi Version](https://img.shields.io/pypi/v/zkaccess-c3.svg)](https://pypi.python.org/pypi/zkaccess-c3/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Usage
To use the library, import the main class:
```
from c3 import C3
```
A panel connection can be created from the main class `C3`:
```
    panel = C3(ip)
    if panel.connect():
      panel.get_device_param(["~SerialNumber", "LockCount")
```
To use the real-time log (RTLog), or control outputs, also include the helper classes from `controldevice` and `rtlog`.

## Compatible devices
The following devices are tested and known compatible:
- C3-200 (firmware AC Ver 4.1.9 4609-03 Apr 7 2016)
- C3-400 (firmware AC Ver 4.3.4 Apr 27 2017)
- C3-400 (firmware AC Ver 5.4.3.2001 Sep 25 2019)
- inBio 460 (firmware AC Ver 5.0.9 4609-06 - Sep 15 2017) (probably 260 and 160 also work)

## Protocol
The C3 access panels communicate using RS485 or TCP/IP.
This library only support TCP/IP connections using IPv4.
The connection is optionally secured by a password.

The wire protocol for the access panels is binary, with the following datagram both for requests (from client to equipment) and responses:

| Byte        | 0      | 1       | 2       | 3          | 4          | 5,6,7,8, ...  | n-2, n-1 | n       |
|-------------|--------|---------|---------|------------|------------|---------------|----------|---------|
| **Meaning** | Start  | Version | Command | Length LSB | Length MSB | Data          | Checksum | End     |
|  **Value**  | `0xAA` | `0x01`  |         |            |            |               |          | `0x55`  |

- The start bytes 0, 1 and last byte have a fixed value.
- The *Command* is one of the following (only listing commands supported by this library)

  | Code   | Command                                            |
  |--------|----------------------------------------------------|
  | `0x01` | Connect (without session initiation)               |
  | `0x02` | Disconnect                                         |
  | `0x03` | Set datetime                                       |
  | `0x04` | Get parameters                                     |
  | `0x05` | Device control command                             |
  | `0x06` | Get datatable configuration                        |
  | `0x08` | Retrieve data from datatable                       |
  | `0x0B` | Retrieve realtime log                              |
  | `0x14` | Device discovery                                   |
  | `0x76` | Connect (session initiation)                       |
  | `0x79` | Realtime log key-values                            |
  | `0xC8` | Response (confirm successful execution of command) |

- The *Length* field (2 bytes, in Little Endian encoding) contains the number of bytes of the *Data* field.
- The *Data* field (as of byte 5) may use 4 reserved bytes in front of actual payload:
  - Session Id (2 bytes, in Little Endian encoding): The session identifier assigned by the equipment in response to a session initiation command
  - Message Number (2 bytes, in Little Endian encoding): A message sequence number that starts from -258 (the session initiation command) and is increased with every command send

  | Byte         | 5             | 6             | 7              | 8              | ...      |
  |--------------|---------------|---------------|----------------|----------------|----------|
  |  **Meaning** | SessionId Lsb | SessionId Msb | Message Nr Lsb | Message Nr Msb | Payload  |

  Whether the Session Id and Message Number is used, depends on how the connection is made (using either command 0x01 or 0x76).
  The support for these commands varies per panel / firmware combination.

- The *Checksum* is a CRC-16 checksum calculated over the full message excluding the *Start* and *End* byte.

## API

### Connect
```
connect(password)
```
The method is used to connect a C3 device using TCP. 
RS485 is not supported,  neither is using a password to secure the connection.
This method must be called before any other method and initializes a C3 session.
The parameter `password` is optional, when omitted, a connection attempt is made without password.
Returns true in case of a successful connection.

### Disconnect
```
disconnect()
```

Disconnects from the C3 access panel and ends the session.

### SetDeviceDatetime
```
set_device_datetime(self, time)
```
Sets the device date/time as ISO timestamp.


### SetDeviceParam
Not implemented yet.

### Get Device Parameters
```
get_device_param(params_arr)
```

This method reads device parameters, both configuration and static parameters.
The argument is a list of (maximum 30) strings with the parameter names for which the values need to be returned. 
Valid values are (reduced list):
- ~CardFormatFunOn, ~DeviceName, ~Ext485ReaderFunOn, ~IsOnlyRFMachine, ~MaxAttLogCount, ~MaxUserCount, ~MaxUserFingerCount, ~SerialNumber, ~ZKFPVersion, 
  AntiPassback, AuxInCount, AuxOutCount, BackupTime, DateTime, DaylightSavingTime, DaylightSavingTimeOn, DeviceID, DLSTMode, 
  Door{N}CancelKeepOpenDay, Door{N}CloseAndLock, Door{N}Detectortime, Door{N}Drivertime, Door{N}FirstCardOpenDoor, Door{N}ForcePassWord, Door{N}Intertime, Door{N}KeepOpenTimeZone, Door{N}MultiCardOpenDoor, Door{N}SensorType, Door{N}SupperPassWord, Door{N}ValidTZ, Door{N}VerifyType, 
  Door4ToDoor2, FirmVer, GATEIPAddress, InBIOTowWay, InterLock, 
  IPAddress, LockCount, MachineType, MasterInbio485, MThreshold, NetMask, PC485AsInbio485, ReaderCount, Reboot, RS232BaudRate, SimpleEventType, StandardTime, WatchDog, WeekOfMonth{N}

For the full list and the meaning of the returned value, refer to the PullSDK specification.
The return value is a table of key/value pairs with the parameter name and value.

### Control Device
```
control_device(control_command_object)
```

Sends a control command to the access panel to perform an action on the requipment. The control_command is an instance of one of the following objects:
- `ControlDeviceOutput(output_number, address, duration)`: Open or close a door or auxiliary device
  - *output_number*: The number of the door or auxiliary to control (1-4)
  - *address*: Determines whether *door_number* is a door (*address* = 1) or an auxiliary (*address* = 2)
  - *duration*: The duration for which the door will be open; 0 will close the door immediately, 1-254 will leave the door open for that number of seconds: 255 will leave the door open for an undetermined period
- `ControlDeviceCancelAlarms()`: Cancel any triggered alarm
- `ControlDeviceRestart()`: Reboot the access panel
- `ControlDeviceNormalOpenStateEnable(door_number, enable_disable)`: Change the normal open/close state for the door controller
  - *door_number*: The number of the door to control (1-4)
  - *enable*: Enable normally open mode (*enable* = True) or disable normally open mode for the door (*enable_disable* = 0, default)


### SetDeviceData
Not implemented yet.

### Get Device Data
```
get_device_data(table_name, field_names)
```

Read the device data (such as the user configuration, user access, timezones and holiday information). 
The method supports the following tables and will return al available records for:
- user
- userauthorize
- holiday
- timezone
- transaction
- firstcard
- multicard or multimcard
- inoutfun
- template
- templatev10

The table support varies between devices and firmwares.
When no table is provided, the method will raise an exception listing all supported tables.
The data is returned as a list of records, with a key/value dictionary per record. 

### GetDeviceDataCount
Not implemented yet.

### DeleteDeviceData
Not implemented yet.

### Get RT Log (real-time log)
```
get_rt_log()
```

This method acquires the realtime event log generated by the access panel. 
It contains the door and/or alarm status of the equipment.
It returns an array of DoorAlarmStatusRecord and/or EventRecord objects.

### SearchDevice
Not implemented yet.

### ModifyIPAddress
Not implemented yet.

### PullLastError
Not implemented yet.

### SetDeviceFileData
Not implemented yet.

### GetDeviceFileData
Not implemented yet.

### ProcessBackupData
Not implemented yet.

### Set log level
```
log_level(level)
```
Sets the logging level, using the Python logging levels.
