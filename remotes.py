import os
from enum import Enum
from recordtype import recordtype
from collections import Iterable

class ConfigPart(Enum):
    IGNORE = 1
    REMOTE = 2
    CODES = 3

RemoteInfo=recordtype("RemoteInfo", [
    "name",
    "bits",
    "freq",  #kHz
    "header",
    "one",
    "zero",
    "ptrail",
    "gap",
    "codes",
])





def __read_single_config(fname) -> RemoteInfo:
    remote = RemoteInfo(
        name=None, 
        bits=32, 
        freq=38.0,
        header=None, 
        one=None, 
        zero=None, 
        ptrail=None, 
        gap=None, 
        codes={})
    part = ConfigPart.IGNORE
    with open(fname) as f:
        for line in f:
            line = line.split('#', 1)[0]
            line = line.strip()

            if len(line) == 0:
                continue

            if line == "begin remote":
                part = ConfigPart.REMOTE
            elif line == "begin codes":
                part = ConfigPart.CODES
            elif line == "end codes":
                part = ConfigPart.REMOTE
            elif line == "end remote":
                part = ConfigPart.IGNORE
            else:
                if part == ConfigPart.REMOTE:
                    __read_remote(remote, line)
                elif part == ConfigPart.CODES:
                    __read_codes(remote, line)

    return (remote.name, remote)


def __read_remote(remote, line):
    if line.startswith("name"):
        remote.name = line.replace("name", "").strip()
    elif line.startswith("bits"):
        remote.bits = int(line.replace("bits", "").strip())
    elif line.startswith("header"):
        remote.header = [int(x) for x in filter(None, line.replace("header", "").strip().split(" "))]
    elif line.startswith("one"):
        remote.one = [int(x) for x in filter(None, line.replace("one", "").strip().split(" "))]
    elif line.startswith("zero"):
        remote.zero = [int(x) for x in filter(None, line.replace("zero", "").strip().split(" "))]
    elif line.startswith("ptrail"):
        remote.ptrail = [int(x) for x in filter(None, line.replace("ptrail", "").strip().split(" "))]
    elif line.startswith("gap"):
        remote.gap = int(line.replace("gap", "").strip())

def __read_codes(remote, line):
        (key, code) = tuple(filter(None, line.split(" ")))
        bytecode = bytearray.fromhex(code.replace("0x", ""))
        if len(bytecode) * 8 != remote.bits:
            print("Warning, incorrect number of bits for key '{}'".format(key))
        remote.codes[key] = bytecode



def read_config(path):
    remotes = {}
    files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            if '.conf' in file:
                files.append(os.path.join(r, file))

    for f in files:
        name, remote = __read_single_config(f)
        remotes[name] = remote

    return remotes
