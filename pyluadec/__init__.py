#!/usr/bin/python

from utility import Struct, read, fread

MAGIC = b'\033Lua'

class TTYPE:
    TNIL = 0
    TBOOLEAN = 1
    TNUMBER = 3
    TSTRING = 4

def Kst(index, key):
    key = key[index]
    return "'%s'" % key if type(key) != float else key

def RK(index, key):
    if (index & 256) == 0:
        return 'R%d' % index
    return Kst(index - 256, key)

def R(index):
    return 'R%d' % index

def U(index):
    return 'U%d' % index

OP_ASM = {
    0: lambda a, b, c, bx: 'MOVE %d %d'        % (a, b),
    1: lambda a, b, c, bx: 'LOADK %d %d'       % (a, bx),
    2: lambda a, b, c, bx: 'LOADBOOL %d %d %d' % (a, b, c),
    3: lambda a, b, c, bx: 'LOADNIL %d %d'     % (a, b),
    4: lambda a, b, c, bx: 'GETUPVAL %d %d'    % (a, b),
    
    5: lambda a, b, c, bx: 'GETGLOBAL %d %d'   % (a, bx),
    6: lambda a, b, c, bx: 'GETTABLE %d %d %d' % (a, b, c),
    
    7: lambda a, b, c, bx: 'SETGLOBAL %d %d' % (a, bx),
    8: lambda a, b, c, bx: 'SETUPVAL %d %d'  % (a, b),
    9: lambda a, b, c, bx: 'SETTABLE %d %d %d'  % (a, b, c),

    10: lambda a, b, c, bx: 'NEWTABLE %d %d %d'  % (a, b, c),
    11: lambda a, b, c, bx: 'SELF %d %d %d'      % (a, b, c), 

    12: lambda a, b, c, bx: 'ADD %d %d %d' % (a, b, c),
    13: lambda a, b, c, bx: 'SUB %d %d %d' % (a, b, c),
    14: lambda a, b, c, bx: 'MUL %d %d %d' % (a, b, c),
    15: lambda a, b, c, bx: 'DIV %d %d %d' % (a, b, c),
    16: lambda a, b, c, bx: 'MOD %d %d %d' % (a, b, c),
    17: lambda a, b, c, bx: 'POW %d %d %d' % (a, b, c),
    18: lambda a, b, c, bx: 'UNM %d %d' % (a, b),
    19: lambda a, b, c, bx: 'NOT %d %d' % (a, b),
    20: lambda a, b, c, bx: 'LEN %d %d' % (a, b),
    
    21: lambda a, b, c, bx: 'CONCAT %d %d %d' % (a, b, c),
    22: lambda a, b, c, bx: 'JUMP %d' % bx,

    23: lambda a, b, c, bx: 'EQ %d %d %d' % (a, b, c),
    24: lambda a, b, c, bx: 'LT %d %d %d' % (a, b, c),
    25: lambda a, b, c, bx: 'LE %d %d %d' % (a, b, c),
    26: lambda a, b, c, bx: 'TEST %d %d' % (a, c),
    27: lambda a, b, c, bx: 'TESTSET %d %d %d' % (a, b, c),

    28: lambda a, b, c, bx: 'CALL %d %d %d' % (a, b, c),
    29: lambda a, b, c, bx: 'TAILCALL %d %d %d' % (a, b, c),
    30: lambda a, b, c, bx: 'RETURN %d %d' % (a, b),

    31: lambda a, b, c, bx: 'FORLOOP %d %d' % (a, bx),
    32: lambda a, b, c, bx: 'FORPREP %d %d' % (a, bx),
    33: lambda a, b, c, bx: 'TFORLOOP %d %d' % (a, c),

    34: lambda a, b, c, bx: 'SETLIST %d %d %d' % (a, b, c),

    35: lambda a, b, c, bx: 'CLOSE',
    36: lambda a, b, c, bx: 'CLOSURE %d %d' % (a, bx),

    37: lambda a, b, c, bx: 'VARARG %d %d' % (a, b),
}

OP_DESC = {
    0: lambda a, b, c, bx, key, func: '%s = %s'           % (R(a), R(b)),
    1: lambda a, b, c, bx, key, func: '%s = %s'           % (R(a), Kst(bx, key)),
    2: lambda a, b, c, bx, key, func: '%s = %s%s'         % (a, 'true' if b > 0 else 'false', '; pc++' if c > 0 else ''),
    3: lambda a, b, c, bx, key, func: '%s = nil'          % (' = '.join([R(i) for i in range(a, b + 1)])),
    4: lambda a, b, c, bx, key, func: '%s = %s'           % (R(a), U(b)),

    5: lambda a, b, c, bx, key, func: '%s = _G[%s]'       % (R(a), Kst(bx, key)),
    6: lambda a, b, c, bx, key, func: '%s = %s[%s]'       % (R(a), R(b), RK(c, key)),

    7: lambda a, b, c, bx, key, func: '_G[%s] = %s'       % (Kst(bx, key), R(a)),
    8: lambda a, b, c, bx, key, func: '%s = %s'           % (U(b), R(a)),
    9: lambda a, b, c, bx, key, func: '%s[%s] = %s'       % (R(a), RK(b, key), RK(c, key)),

    10: lambda a, b, c, bx, key, func: '%s = {} (size = %d,%d)' % (R(a), b, c),
    11: lambda a, b, c, bx, key, func: '%s = %s; %s = %s[%s]'   % (R(a + 1), R(b), R(a), R(b), RK(c, key)),

    12: lambda a, b, c, bx, key, func: '%s = %s + %s'      % (R(a), RK(b, key), RK(c, key)),
    13: lambda a, b, c, bx, key, func: '%s = %s - %s'      % (R(a), RK(b, key), RK(c, key)),
    14: lambda a, b, c, bx, key, func: '%s = %s * %s'      % (R(a), RK(b, key), RK(c, key)),
    15: lambda a, b, c, bx, key, func: '%s = %s / %s'      % (R(a), RK(b, key), RK(c, key)),
    16: lambda a, b, c, bx, key, func: '%s = %s %% %s'     % (R(a), RK(b, key), RK(c, key)),
    17: lambda a, b, c, bx, key, func: '%s = %s ^ %s'      % (R(a), RK(b, key), RK(c, key)),
    18: lambda a, b, c, bx, key, func: '%s = -%s'          % (R(a), R(b)),
    19: lambda a, b, c, bx, key, func: '%s = not %s'       % (R(a), R(b)),
    20: lambda a, b, c, bx, key, func: '%s = #(%s)'        % (R(a), R(b)),

    21: lambda a, b, c, bx, key, func: '%s = %s'           % (R(a), ' .. '.join([R(i) for i in range(b, c + 1)])),
    22: lambda a, b, c, bx, key, func: 'pc += %s'          % (bx),

    23: lambda a, b, c, bx, key, func: 'if (%s == %s) ~= %s then pc++' % (RK(b, key), RK(c, key), a),
    24: lambda a, b, c, bx, key, func: 'if (%s == %s) <  %s then pc++' % (RK(b, key), RK(c, key), a),
    25: lambda a, b, c, bx, key, func: 'if (%s == %s) <= %s then pc++' % (RK(b, key), RK(c, key), a),

    26: lambda a, b, c, bx, key, func: 'if not (%s != %s) then pc++'         % (R(a), c),
    27: lambda a, b, c, bx, key, func: 'if %s != %s then %s = %s else pc++' % (R(b), c, R(a), R(b)),

    28: lambda a, b, c, bx, key, func: '%s = %s(%s)'       % (', '.join([R(i) for i in range(a, a + c - 1)]), R(a), ', '.join([R(i) for i in range(a + 1, a + b)])),
    29: lambda a, b, c, bx, key, func: 'return %s(%s)'     % (R(a), ', '.join([R(i) for i in range(a + 1, a + b)])),
    30: lambda a, b, c, bx, key, func: 'return %s'         % (', '.join([R(i) for i in range(a, a + b - 1)])),

    31: lambda a, b, c, bx, key, func: '%s + %s; if %s <= %s then { pc += %s; %s = %s }' % (R(a), R(a + 2), R(a), R(a + 1), bx, R(a + 3), R(a)),
    32: lambda a, b, c, bx, key, func: '%s - %s; pc += %s' % (R(a), R(a + 2), bx),

    33: lambda a, b, c, bx, key, func: '%s = %s(%s, %s); if %s ~= nil then %s = %s else pc++' 
                                        % (', '.join([R(i) for i in range(a + 3, a + c + 3)]), R(a), R(a + 1), R(a + 2), R(a + 3), R(a + 2), R(a + 3)),
    34: lambda a, b, c, bx, key, func: '%s[%s * FPF + i] = R(%s + i), i <= i <= %s' % (R(a), c + 1, a, b),

    35: lambda a, b, c, bx, key, func: 'close %s'  % (R(a)),
    36: lambda a, b, c, bx, key, func: '%s = closure(KPROTO[%s] %d)'  % (R(a), bx, func[bx].Upvalues),
    37: lambda a, b, c, bx, key, func: '%s = vararg'       % (', '.join([R(i) for i in range(a, a + b)])),
}

CONST_KEY = {
    TTYPE.TNIL:     lambda f: None,
    TTYPE.TBOOLEAN: lambda f: read(f, '*u1'),
    TTYPE.TNUMBER:  lambda f: read(f, '*f8'),
    TTYPE.TSTRING:  lambda f: read(f, String),
}

class Data:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.max_len = len(data)

    def read(self, len):
        pos = self.pos
        self.pos = self.pos + len
        return data[pos, self.pos]

class String(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('Size', file, '*u4')
        if self.Size > 0:
            self.read('Value', file, '*s%d' % self.Size)

    def format(self):
        return self.Value if self.Size > 0 else ''

class Instruction(Struct):
    def __init__(self, file):
        super().__init__()

        self.Inst = read(file, '*u4')

        self.OP = (self.Inst)       & 0b111111
        self.A  = (self.Inst >> 6)  & 0b11111111
        self.C  = (self.Inst >> 14) & 0b111111111
        self.B  = (self.Inst >> 23) & 0b111111111
        self.Bx = (self.Inst >> 14)

        self._ASM = OP_ASM[self.OP](self.A, self.B, self.C, self.Bx) if self.OP in OP_ASM else ''
    
    def update(self, key, func):
        self._Desc = OP_DESC[self.OP](self.A, self.B, self.C, self.Bx, key, func) if self.OP in OP_DESC else ''

    def format(self):
        # return '{0}({1:X})'.format(self._Desc, self.Inst)
        return self._ASM

class Code(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('SizeCode',    file,  '*u4')
        self.read('Code',        file,  [Instruction for i in range(self.SizeCode)])

    def update(self, key, func):
        for inst in self.Code:
            inst.update(key, func)

class LocVar(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('VarName',      file,  String)
        self.read('StartPC',      file,  '*u4')
        self.read('EndPC',        file,  '*u4')

class Debug(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('LineInfoSize',  file,  '*u4')
        if self.LineInfoSize > 0:
            self.read('LineInfos', file,  ['*u4' for i in range(self.LineInfoSize)])

        self.read('LocalVarsSize', file,  '*u4')
        if self.LocalVarsSize > 0:
            self.read('LineInfos', file,  [LocVar for i in range(self.LocalVarsSize)])
        
        self.read('UpvalueSize',   file,  '*u4')
        if self.UpvalueSize > 0:
            self.read('LineInfos', file,  [String for i in range(self.UpvalueSize)])

    def format(self):
        return {} if self.LineInfoSize == 0 and self.LocalVarsSize == 0 and self.UpvalueSize == 0 else super().format(self)

class Constant(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('SizeKey',      file,  '*u4')
        if self.SizeKey > 0:
            self.Key = [CONST_KEY[read(file, '*u1')](file) for i in range(0, self.SizeKey)]

        self.read('SizeFunction',      file,  '*u4')
        if self.SizeFunction > 0:
            self.read('Funtions',      file,  [Function for i in range(self.SizeFunction)])


class Function(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('Source',               file,  String)
        self.read('LineDefined',          file,  '*u4')
        self.read('LastLineDefined',      file,  '*u4')
        self.read('Upvalues',             file,  '*u1')
        self.read('Params',               file,  '*u1')
        self.read('IsVarArg',             file,  '*u1')
        self.read('MaxStackSize',         file,  '*u1')
        self.read('Code',                 file,  Code)
        self.read('Constant',             file,  Constant)
        self.read('Debug',                file,  Debug)

        self.Code.update(self.Constant.Key if self.Constant.SizeKey > 0 else [], self.Constant.Funtions if self.Constant.SizeFunction > 0 else [])

class Header(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('Version',              file, '*u1')
        self.read('Format',               file, '*u1')
        self.read('Endian',               file, '*u1')
        self.read('IntLength',            file, '*u1')
        self.read('SizetLength',          file, '*u1')
        self.read('InstructionLength',    file, '*u1') # VM Instruction Length
        self.read('NumberLength',         file, '*u1')
        self.read('IntergralNumber',      file, '*u1')

class Lua(Struct):
    def __init__(self, file):
        super().__init__()

        self._file = file
        self._offset  = file.tell()

        self.read('Header',   file, Header)
        self.read('Function', file, Function)

def undump(file):
    if file.read(len(MAGIC)) != MAGIC:
        return
    return Lua(file)

def decompiler(path=None, data=None):
    if path:
        file = open(path, 'rb+')
    return undump(file)

data = decompiler('base.lua').tojson()
print(data)
f = open('out.json', 'w')
f.write(data)