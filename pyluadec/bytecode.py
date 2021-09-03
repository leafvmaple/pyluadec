from utility import Struct, read, fread
from luadef import OP_ASM, OP_DECODE, OP_CODE, Kst, RK, R, U, F, T

class TTYPE:
    TNIL = 0
    TBOOLEAN = 1
    TNUMBER = 3
    TSTRING = 4

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

        self._ASM = OP_ASM[self.OP](self)

    def format(self):
        # return '{0}({1:X})'.format(self._Desc, self.Inst)
        return self._ASM

class Code(Struct):
    def __init__(self, file):
        super().__init__()

        self.read('SizeCode',    file,  '*u4')
        self.read('Instructions', file,  [Instruction for i in range(self.SizeCode)])

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
        self.Key = [CONST_KEY[read(file, '*u1')](file) for i in range(0, self.SizeKey)]

        self.read('SizeFunction',      file,  '*u4')
        self.read('Functions',      file,  [Function for i in range(self.SizeFunction)])


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

    def decompile(self):
        keys  = self.Constant.Key
        funcs = self.Constant.Functions
        codes = []
        vals = {}
        flag = {}
        skip = 0
        for i, cur in enumerate(self.Code.Instructions):
            if skip > 0:
                skip -= 1
                continue

            if cur.OP == OP_CODE.GETGLOBAL:
                vals[cur.A] = keys[cur.Bx]
            
            if cur.OP == OP_CODE.CLOSURE:
                func = funcs[cur.Bx]
                vals[cur.A] = 'function()'
                skip = func.Upvalues

            if cur.OP == OP_CODE.GETTABLE:
                if cur.B in vals:
                    codes.append('%s%s = %s' % (F(cur.A, flag), R(cur.A), T(vals[cur.B], RK(cur.C, keys))))
                    continue

            codes.append(OP_DECODE[cur.OP](cur, keys, funcs, flag))
        return '\n'.join(codes)

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

class ByteCode(Struct):
    def __init__(self, file):
        super().__init__()

        self._file = file
        self._offset  = file.tell()

        self.read('Header',   file, Header)
        self.read('Function', file, Function)

    def decompile(self):
        return self.Function.decompile()