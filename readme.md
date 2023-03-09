# c3
A native Python library for communicating with the ZKAccess C3 Access Control Panels.

This library intends to implement the same functionality as provided by the ZKAccess C3 PullSDK API.
It is a port of my (C3 Lua library)[../zkaccess-c3-lua]

## Usage
```
TODO
```

## Protocol
The C3 access panels communicate using RS485 or TCP/IP. The connection is optionally secured by a password.
The wire protocol for the access panels is binary, with the following datagram both for requests (from client to equipment) and responses:

Byte        | 0      | 1       | 2       | 3          | 4          | 5,6,7,8, ...  | n-2, n-1 | n
------------|--------|---------|---------|------------|------------|---------------|----------|-----
**Meaning** | Start  | Version | Command | Length Lsb | Length Msb | Data          | Checksum | End
**Value**   | `0xAA` | `0x01`  |         |            |            |               |          | `0x55`

The start bytes 0, 1 and last byte have a fixed value.
The *Command* is one of the following (only listing commands supported by this library)

Code   | Command
-------|--------
`0x76` | Connect (session initiation)
`0x02` | Disconnection (session end)
`0x05` | Device control command
`0x0B` | Retrieve realtime log
`0xC8` | Response (confirm successful execution of command)

The *Length* field (2 bytes, in Little Endian encoding) contains the number of bytes of the *Data* field.
The *Data* field (as of byte 5) typically has at least 4 bytes:
- Session Id (2 bytes, in Little Endian encoding): The session identifier assigned by the equipment in response to a session initiation command
- Message Number (2 bytes, in Little Endian encoding): A message sequence number that starts from 0 (the session initiation command) and is increased with every command send

Byte        | 5             | 6             | 7              | 8              | ...
------------|---------------|---------------|----------------|----------------|--------
**Meaning** | SessionId Lsb | SessionId Msb | Message Nr Lsb | Message Nr Msb | Payload

The *Checksum* is a CRC-16 checksum calculated over the full message excluding the *Start* and *End* byte.

## API
```
    TODO
```

### connect
```
connect(host, port)
```

The method is used to connect a C3 device using TCP. RS485 is not supported. Neither is using a password to secure the connection. This method must be called before any other method and initializes a C3 session.
Returns true in case of a successful connection.

### disconnect
```
disconnect()
```

Disconnects from the C3 access panel and ends the session.

### getRTLog
```
getRTLog()
```

This method acquires the realtime event log generated by the access panel. It contains the door and/or alarm status of the equipment.
It returns an array of RTDAStatusRecord and/or RTEventRecord objects.

### getDeviceParameters
```
getDeviceParameters(params_arr)
```

This method reads device parameters, both configuration and static parameters.
The argument is a list of (maximum 30) strings with the parameter names for which the values need to be returned. Valid values are (reduced list):
   ~SerialNumber, AntiPassback, AuxInCount, AuxOutCount, BackupTime, ComPwd, DateTime, DaylightSavingTime, DaylightSavingTimeOn, DLSTMode, Door{N}CancelKeepOpenDay, Door{N}CloseAndLock, Door{N}Detectortime, Door{N}Drivertime, Door{N}FirstCardOpenDoor, Door{N}ForcePassWord, Door{N}Intertime, Door{N}KeepOpenTimeZone, Door{N}MultiCardOpenDoor, Door{N}SensorType, Door{N}SupperPassWord, Door{N}ValidTZ, Door{N}VerifyType, GATEIPAddress, InBIOTowWay , InterLock, IPAddress, LockCount, NetMask, ReaderCount, Reboot, RS232BaudRate, StandardTime, WatchDog, WeekOfMonth{N},
For the full list and the meaning of the returned value, refer to the PullSDK specification.
The return value is a table of key/value pairs with the parameter name and value.

### controlDevice
```
controlDevice(control_command_object)
```

Sends a control command to the access panel to perform an action on the requipment. The control_command is an instance of one of the following objects:
- `C3.ControlDeviceOutput(door_number, address, duration)`: Open or close a door or auxilary device
  - *door_number*: The number of the door or auxilary to control (1-4)
  - *address*: Determines whether *door_number* is a door (*address* = 1) or an auxilary (*address* = 2)
  - *duration*: The duration for which the door will be open; 0 will close the door immediately, 1-254 will leave the door open for that number of seconds: 255 will leave the door open for an undetermined period
- `C3.ControlDeviceCancelAlarm()`: Cancel any triggered alarm
- `C3.ControlDeviceRestartDevice()`: Reboot the access panel
- `C3.ControlDeviceNOState(door_number, enable_disable)`: Change the normal open/close state for the door controller
  - *door_number*: The number of the door to control (1-4)
  - *enable_disable*: Enable normally open mode (*enable_disable* = 1) or disable normally open mode for the door (*enable_disable* = 0, default)

### setDebug
```
set_debug(debug_on_off)
```

Sets or unsets debug mode. In debug mode, the library prints a lot of detailed internal information, specifically regarding protocol binary data.
