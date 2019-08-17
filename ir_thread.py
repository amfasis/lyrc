import pigpio
import os
import asyncio
from collections import Iterable

from remotes import read_config
from command import CommandItem


"""
Consumer with an infinite loop. It only stops if there is a poison pill.
"""
async def irsend_thread(queue, loop, config_path, gpio_pin, start_pigpio, verbose):
    print("Starting IR thread")
    remotes = read_config(config_path)
    
    print("Loaded {} remote(s) from {}".format(len(remotes), config_path))

    if start_pigpio:
        os.system("sudo service pigpiod start")
        print("started pigpiod")

    pi = pigpio.pi()
    pi.set_mode(gpio_pin, pigpio.OUTPUT)
    pi.wave_clear()
    pi.wave_add_new()

    waves = {}
    for remote in remotes.keys():
        if verbose:
            print("Creating waves for {}".format(remote))
        waves[remote] = __create_waves(pi, remotes[remote], gpio_pin)

    print("PiGPIO loaded with pin {} and {} remote(s)".format(gpio_pin, len(remotes)))

    repeat_wave = None #the wave form last generated, to be transmitted again (or None if not needed to repeat)
    try:
        while True:
            
            if not repeat_wave or not queue.empty():
                item = await queue.get() # coroutine will be blocked if queue is empty

                if not isinstance(item, CommandItem):
                    print("got {}, closing".format(item))
                    break #clean close
                
                assert(isinstance(item.future, asyncio.Future))

                if item.directive == "LIST":
                    if not item.remote:
                        item.future.set_result(list(remotes.keys()))
                    elif not item.key_code:
                        if item.remote in remotes:
                            item.future.set_result(list(remotes[item.remote].codes.keys()))
                        else:
                            item.future.set_result("unknown remote")
                    else:
                        if item.remote in remotes:
                            if item.key_code in remotes[item.remote].codes:
                                item.future.set_result(["{} 0x{}".format(item.key_code, remotes[item.remote].codes[item.key_code].hex().upper())])
                            else:
                                item.future.set_result("unknown key_code")
                        else:
                            item.future.set_result("unknown remote")
                        
                elif item.directive in "SEND_STOP":
                    if repeat_wave:
                        repeat_wave = None
                        item.future.set_result(True) #cancelled succesfully
                    else:
                        item.future.set_result("No key was scheduled for repeat")

                elif item.directive in ("SEND_ONCE", "SEND_START"):
                    if not item.remote in remotes:
                        item.future.set_result("Unknown remote")
                    else:
                        remote_info = remotes[item.remote]

                    if not item.key_code in remote_info.codes:
                        item.future.set_result("Unknown key_code")
                    else:
                        start = item.directive == "SEND_START"
                        key_code = remotes[item.remote].codes[item.key_code]
                        bytes_as_bits = ''.join(format(byte, '08b') for byte in key_code)

                        chain = [0] + [1 if x == '1' else 2 for x in bytes_as_bits] + [3]
                        if item.directive == "SEND_START":
                            chain.append(4) #append gap

                        if verbose:
                            print("chain {}".format(chain))
    
                        repeat_wave = list(__flatten([waves[item.remote][id] for id in chain]))

                        pi.wave_chain(repeat_wave)
                        while pi.wave_tx_busy():
                            await asyncio.sleep(0.05)

                        item.future.set_result(True)

                        if item.directive != 'SEND_START':
                            repeat_wave = None
                else:
                    item.future.set_result("Directive '{}' not supported".format(item.directive))

                # signal that the current task from the queue is done 
                # and decrease the queue counter by one
                queue.task_done()

            else:
                pi.wave_chain(repeat_wave)
                while pi.wave_tx_busy():
                    await asyncio.sleep(0.05)
    
    except asyncio.CancelledError:
        print("cancelling blasting thread")
    except Exception as e:
        print("exception: {}".format(e))
    finally:
        for rwaves in waves.values():
            for pwaves in rwaves:
                for w in pwaves:
                    pi.wave_delete(w)

        pi.stop()

        if start_pigpio:
            print("stopping pigpiod")
            os.system("sudo service pigpiod stop")
        
        print("Stopped ir blaster thread")
    


def __flatten(items):
    """Yield items from any nested iterable; see Reference."""
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in __flatten(x):
                yield sub_x
        else:
            yield x

def __carrier(gpio, frequency, micros, dutycycle=0.5):
    """
    Generate cycles of carrier on gpio with frequency and dutycycle.
    """
    wf = []
    cycle = 1000.0 / frequency
    cycles = int(round(micros/cycle))
    on = int(round(cycle * dutycycle))
    sofar = 0
    for c in range(cycles):
        target = int(round((c+1)*cycle))
        sofar += on
        off = target - sofar
        sofar += off
        wf.append(pigpio.pulse(1<<gpio, 0, on))
        wf.append(pigpio.pulse(0, 1<<gpio, off))
    return wf

def __create_waves(pi, remote, gpio_pin):
    waves = []
    
    pi.wave_clear()
    print(str(remote))
    for code in [remote.header, remote.one, remote.zero, remote.ptrail]:
        code_waves = []
        for i, length in enumerate(code):

            if i%2 == 0:
                res = pi.wave_add_generic(__carrier(gpio_pin, remote.freq, round(length / 2)))
                res = pi.wave_create()
                code_waves.append(res)
            else:
                res = pi.wave_add_generic([pigpio.pulse(0, 0, round(length / 2))])
                res = pi.wave_create()
                code_waves.append(res)

        waves.append(code_waves)

    pi.wave_add_generic([pigpio.pulse(0, 0, remote.gap)])
    waves.append([pi.wave_create()])
    return waves

        