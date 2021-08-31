import sys
import json
import struct

BYTE_ORDER = {
    '*': sys.byteorder,
    '+': 'big',
    '-': 'little',
}

def get_null_string(data, offset):
    idx = data.find(b'\0', offset)
    return bytes.decode(data[offset: idx])

def fread(file, size):
    data = file.read(size)
    if len(data) == 0:
        raise EOFError
    return data

def read_string(file, opt, len):
    if len <= 0:
        res = []
        ch = fread(file, 1)
        while (ch != b'\0'):
            res.append(ch)
            ch = fread(file, 1)
        res = b''.join(res)
    else:
        res = fread(file, int(len))
    res = bytes.decode(res.strip(b'\0 '), encoding='gbk', errors="strict")
    if opt == 'i':
        res = int(res)

    return res

READ_BYTE = {
    'u': lambda f, o, x: int.from_bytes(fread(f, int(x)), BYTE_ORDER[o]),
    'i': lambda f, o, x: int.from_bytes(fread(f, int(x)), BYTE_ORDER[o], signed=True),
    'f': lambda f, o, x: struct.unpack('=%s' % 'f' if x == '4' else 'd', fread(f, int(x)))[0],
    's': lambda f, o, x: read_string(f, o, int(x)),
}

def read(file, form, initvars=None):
    if type(form) == str:
        var = READ_BYTE[form[1]](file, form[0], form[2:])
    elif type(form) == type:
        var = form(file, initvars) if initvars else form(file)
    elif type(form) == list:
        var = []
        for v in form:
            try:
                var.append(read(file, v, initvars))
            except EOFError:
                pass
    return var

def from_bytes(obj, file, export):
    for k, v in export.items():
        var = read(file, v)
        setattr(obj, k, var)

def to_bytes(obj, export):
    res = b''
    for k, v in export.items():
        if hasattr(obj, k):
            value = getattr(obj, k)
            if type(v) == int:
                res = res + value.to_bytes(v, byteorder=sys.byteorder)
            elif type(v) == type:
                res = res + value.to_bytes()
    return res

def format_desc(value, desc):
    if type(desc) == dict:
        dict_desc = desc[value] if value in desc \
            else ' | '.join([desc[v] for v in desc.keys() if value & v])
        res = '{0:X} ({1})'.format(value, dict_desc) if len(dict_desc) > 0 else '{0:X}'.format(value)
    else:
        res = str(desc(value))
    return res

def format_obj(key, value, desc):
    if key in desc:
        res = format_desc(value, desc[key])
    elif value is None:
        return None
    elif type(value) == int:
        res = "{0:X}".format(value)
    elif type(value) == str:
        res = value
    elif type(value) == list:
        res = [format_obj(key, v, desc) for v in value]
    elif type(value) == tuple:
        res = str(value)
    elif type(value) == bytes:
        res = ' '.join(['%02X' % b for b in value])
    elif type(value) == float:
        res = value
    else:
        res = value.format()
    
    return res

def format(obj, keys, desc):
    res = {}
    for k in keys:
        value = getattr(obj, k)
        res[k] = format_obj(k, value, desc)

    return res

def read_bytes(file, offset, len):
    cur_offset = file.tell()
    data = file.read(len)
    file.seek(cur_offset)
    return data


class Struct:
    def __init__(self, desc={}, display=[], filter=[], initvars=None):
        self._form    = {}
        self._export  = {}
        self._desc    = desc
        self._display = display
        self._filter  = filter

        if initvars:
            for k, v in initvars.items():
                setattr(self, k, v)

    def __str__(self):
        return str(self.format())
        
    def format(self):
        keys = [v for v in vars(self).keys() if (not v.startswith('_') or v in self._display) and v not in self._filter]
        return format(self, keys, self._desc)
        # return format(self, list(set(vars(self).keys()).union(set(self._display)).difference(set(self._filter))), self._desc)

    def read(self, key, file, form, initvars=None):
        self._form[key] = form
        setattr(self, key, read(file, form, initvars))

    def tojson(self, indent='\t'):
        return json.dumps(self.format(), indent=indent)

    def to_bytes(self):
        return to_bytes(self, self._export)

class Version:
    def __init__(self, file, export):
        self._export = export

        self.Major = 0
        self.Minor = 0

        from_bytes(self, file, export)

    def __str__(self):
        return str(self.format())

    def format(self):
        return '{0}.{1:0>2d}'.format(self.Major, self.Minor)

    def tojson(self, indent='\t'):
        return json.dumps(self.format(), indent=indent)

    def to_bytes(self):
        return to_bytes(self, self._export)
