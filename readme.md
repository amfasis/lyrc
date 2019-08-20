# Lyrc - Python replacement for LIRC

This project is an attempt to replace LIRC with a python variant. This came to be when my Raspberry Pi kernel was updated and lost the `lirc-rpi` dtoverlay and I couldn't get the new `gpio-ir-tx` to work.

I was using LIRC to send IR-pulses to my amplifier, using the Android app [LIRC client](https://play.google.com/store/apps/details?id=com.chham.lirc_client). This is what LYRC can also do. I know LIRC can do more than that, also sending actual key events as user input. Since I don't use that part, I also did not attempt to implement anything for that in Lyrc, and honestly I don't think it is possible with Python.

This project was inspired by `irrp.py` from http://abyz.co.uk/rpi/pigpio/examples.html#Python_irrp_py (unfortunately the link has died)

## Features
- **Send IR-pulses on GPIO using Pigpio**
- **Start and stop Pigpio deamon.** I found running Pigpio daemon all the time eats 10% of my Raspberry Pi's CPU.
- **Listen for clients talking the LIRC protocol**
- **Keep-alive for the Pigpio daemon.** When you use the Android app and switch to another app (for example to start music) the client might drop the connection, but Lyrc can keep the Pigpio daemon alive for a configurable amount of time, to reduce start/stops.

## Requirements

You will need
- an IR transmitter connected to GPIO
- a [PiGPIO Daemon](http://abyz.me.uk/rpi/pigpio/pigpiod.html) setup (optionally running), including the python module
- old style LIRC configuration to mimic your remote (LIRC 0.8.5)

## Installation
You should download this repository to a folder of choice and install the `lyrcd.service`

    cd ~
    git clone https://github.com/amfasis/lyrc.git
    cd lyrc
    sudo cp lyrcd.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable lyrcd.service
    sudo systemctl start lyrcd.service

## Configuration
The configuration of Lyrcd is in `config.ini`. You shuold craft your own version, taking `config.ini.example` as a guidline. The following settings are available:

### [server]
- **listen_address** (default `0.0.0.0`)  
  The address to bind the server to, use `0.0.0.0` to listen of all interfaces
- **listen_port** (default `7059` ) 
  The port to listen on, default of LIRC is 7059

### [remotes]
- **path** (default `/etc/lirc`)  
  The path where the remotes configuration files can be found (the old-style LIRC config files, they can be downloaded from http://lirc-remotes.sourceforge.net/). I uploaded mine in this repo, which is actually for a quite old radio ;-)
 
### [pigpio]
- **gpio_pin** (default `22`) 
  The GPIO pin on which you installed the IR transmitter
- **start_pigpio** (default `False`) 
  Whether to start and stop the `pigpiod.service` when a client connects
- **keep_alive** (default `300`) 
  The time to keep the `Pigpiod.service` alive after a client connects

### [logging]
- **verbose** (default `False`) 
  Add some extra logging to help debugging not working remote configuration

## Troubleshooting
When you experience a remote configuration that doesn't make your IR-controlled device react, you can enable `verbose` in `config.ini`. After changing this setting, you should of course stop the service and run it manually: `python3 -m lyrcd` (from the folder where you `git clone`d) to be able to see the output.

Verbose logging will output the imported configuration and print the chain that will be send.

The imported configuration is a bit garbled, but you should be able to read the bytecodes for each key and other settings. These are converted into bits. When playing back a pulse, the `zero` of this bit-array will be presented as 1 and the `one` of the bit-array will be presented as 2. Before the bit-array there is the `header` pulse, which is presented as 0. On the end of the bit-array the `ptrail` pulse will be appended, presented as 3. If you start a repeated pulse-send (SEND_START, in the Android app you can long-press a button to initiate this), a 4 will be appended, which is the `gap`.

The `header`, `one`, `zero`, `ptrail` settings can contain more than one pulse-length, the first and third (and so on) item will always be a pulse of the specified length on a carrier wave of the `freq` setting (which is in kHz), the other items will be 'spaces', no IR-light is send out.
The `gap` setting is only a single integer, since it should be a gap, not a "filled gap" ;-)

## Tricks
I also use a cronjob to automatically switch off my amplifier at night (when forgotten):

```Bash
echo "SEND_ONCE Pioneer_XXD3067 PowerOff" EOF | nc 127.0.0.1 7059 -q 1
```

## Known issues
When a client connects, the first command can take to some time to get processed (~15s) because Pigpio has to start up.

I had two occasions where the ir-thread exited with an exception, which I think was related to the pigpio deamon not available (while the daemon was requested to start).

I am aware that it is only build for one specific remote config. I'm happy to help where I can in case you need a remote with additional configurations. 

Any updates to the project are also welcome.