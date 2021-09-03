#!/usr/bin/python
from bytecode import ByteCode

MAGIC = b'\033Lua'

def undump(file):
    if file.read(len(MAGIC)) != MAGIC:
        return
    return ByteCode(file)

def decompiler(path=None, data=None):
    if path:
        file = open(path, 'rb+')
    return undump(file)

data = decompiler('base.lua').decompile()
print(data)
f = open('out.json', 'w')
f.write(data)