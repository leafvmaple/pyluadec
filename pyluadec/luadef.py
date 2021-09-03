def Kst(index, key):
    key = key[index]
    return key if type(key) != float else key

def RK(index, key):
    if (index & 256) == 0:
        return R(index)
    return Kst(index - 256, key)

def R(index):
    return 'a%d' % index

def U(index):
    return 'u%d' % index

def F(index, flag):
    field = 'local ' if index not in flag else ''
    flag[index] = True
    return field

def T(table, key):
    if type(key) == float or type(key) == int:
        return '%s[%s]' % (table, key)
    return '%s' % key if table == '_G' else '%s.%s' % (table, key)

class OP_CODE:
    MOVE      = 0
    LOADK     = 1
    LOADBOOL  = 2
    LOADNIL   = 3
    GETUPVAL  = 4
    GETGLOBAL = 5
    GETTABLE  = 6

    CLOSURE   = 36

OP_ASM = {
    0:  lambda it: 'MOVE %d %d'         % (it.A, it.B),
    1:  lambda it: 'LOADK %d %d'        % (it.A, it.Bx),
    2:  lambda it: 'LOADBOOL %d %d %d'  % (it.A, it.B, it.C),
    3:  lambda it: 'LOADNIL %d %d'      % (it.A, it.B),
    4:  lambda it: 'GETUPVAL %d %d'     % (it.A, it.B),
    
    5:  lambda it: 'GETGLOBAL %d %d'    % (it.A, it.Bx),
    6:  lambda it: 'GETTABLE %d %d %d'  % (it.A, it.B, it.C),
    
    7:  lambda it: 'SETGLOBAL %d %d'    % (it.A, it.Bx),
    8:  lambda it: 'SETUPVAL %d %d'     % (it.A, it.B),
    9:  lambda it: 'SETTABLE %d %d %d'  % (it.A, it.B, it.C),

    10: lambda it: 'NEWTABLE %d %d %d'  % (it.A, it.B, it.C),
    11: lambda it: 'SELF %d %d %d'      % (it.A, it.B, it.C), 

    12: lambda it: 'ADD %d %d %d' % (it.A, it.B, it.C),
    13: lambda it: 'SUB %d %d %d' % (it.A, it.B, it.C),
    14: lambda it: 'MUL %d %d %d' % (it.A, it.B, it.C),
    15: lambda it: 'DIV %d %d %d' % (it.A, it.B, it.C),
    16: lambda it: 'MOD %d %d %d' % (it.A, it.B, it.C),
    17: lambda it: 'POW %d %d %d' % (it.A, it.B, it.C),
    18: lambda it: 'UNM %d %d' % (it.A, it.B),
    19: lambda it: 'NOT %d %d' % (it.A, it.B),
    20: lambda it: 'LEN %d %d' % (it.A, it.B),
    
    21: lambda it: 'CONCAT %d %d %d' % (it.A, it.B, it.C),
    22: lambda it: 'JUMP %d' % it.Bx,

    23: lambda it: 'EQ %d %d %d' % (it.A, it.B, it.C),
    24: lambda it: 'LT %d %d %d' % (it.A, it.B, it.C),
    25: lambda it: 'LE %d %d %d' % (it.A, it.B, it.C),
    26: lambda it: 'TEST %d %d' % (it.A, it.C),
    27: lambda it: 'TESTSET %d %d %d' % (it.A, it.B, it.C),

    28: lambda it: 'CALL %d %d %d' % (it.A, it.B, it.C),
    29: lambda it: 'TAILCALL %d %d %d' % (it.A, it.B, it.C),
    30: lambda it: 'RETURN %d %d' % (it.A, it.B),

    31: lambda it: 'FORLOOP %d %d' % (it.A, it.Bx),
    32: lambda it: 'FORPREP %d %d' % (it.A, it.Bx),
    33: lambda it: 'TFORLOOP %d %d' % (it.A, it.C),

    34: lambda it: 'SETLIST %d %d %d' % (it.A, it.B, it.C),

    35: lambda it: 'CLOSE',
    36: lambda it: 'CLOSURE %d %d' % (it.A, it.Bx),

    37: lambda it: 'VARARG %d %d' % (it.A, it.B),
}

OP_DECODE = {
    0:  lambda it, key, func, flag: '%s%s = %s'         % (F(it.A, flag), R(it.A), R(it.B)),
    1:  lambda it, key, func, flag: '%s%s = %s'         % (F(it.A, flag), R(it.A), Kst(it.Bx, key)),
    2:  lambda it, key, func, flag: '%s%s = %s%s'       % (F(it.A, flag), it.A, 'true' if it.B > 0 else 'false', '; pc++' if it.C > 0 else ''),
    3:  lambda it, key, func, flag: '%s%s = nil'        % (F(it.A, flag), ' = '.join([R(i) for i in range(it.A, it.B + 1)])),
    4:  lambda it, key, func, flag: '%s%s = %s'         % (F(it.A, flag), R(it.A), U(it.B)),

    5:  lambda it, key, func, flag: '%s%s = %s'         % (F(it.A, flag), R(it.A), T('_G', Kst(it.Bx, key))),
    6:  lambda it, key, func, flag: '%s = %s'           % (R(it.A), T(R(it.B), RK(it.C, key))),

    7:  lambda it, key, func, flag: "%s = %s"           % (T('_G', Kst(it.Bx, key)), R(it.A)),
    8:  lambda it, key, func, flag: '%s = %s'           % (U(it.B), R(it.A)),
    9:  lambda it, key, func, flag: '%s = %s'           % (T(R(it.A), RK(it.B, key)), RK(it.C, key)),

    10: lambda it, key, func, flag: '%s%s = {}'         % (F(it.A, flag), R(it.A)),
    11: lambda it, key, func, flag: '%s = %s; %s = %s[%s]'   % (R(it.A + 1), R(it.B), R(it.A), R(it.B), RK(it.C, key)),

    12: lambda it, key, func, flag: '%s = %s + %s'      % (R(it.A), RK(it.B, key), RK(it.C, key)),
    13: lambda it, key, func, flag: '%s = %s - %s'      % (R(it.A), RK(it.B, key), RK(it.C, key)),
    14: lambda it, key, func, flag: '%s = %s * %s'      % (R(it.A), RK(it.B, key), RK(it.C, key)),
    15: lambda it, key, func, flag: '%s = %s / %s'      % (R(it.A), RK(it.B, key), RK(it.C, key)),
    16: lambda it, key, func, flag: '%s = %s %% %s'     % (R(it.A), RK(it.B, key), RK(it.C, key)),
    17: lambda it, key, func, flag: '%s = %s ^ %s'      % (R(it.A), RK(it.B, key), RK(it.C, key)),
    18: lambda it, key, func, flag: '%s = -%s'          % (R(it.A), R(it.B)),
    19: lambda it, key, func, flag: '%s = not %s'       % (R(it.A), R(it.B)),
    20: lambda it, key, func, flag: '%s = #(%s)'        % (R(it.A), R(it.B)),

    21: lambda it, key, func, flag: '%s = %s'           % (R(it.A), ' .. '.join([R(i) for i in range(it.B, it.C + 1)])),
    22: lambda it, key, func, flag: 'pc += %s'          % (it.Bx),

    23: lambda it, key, func, flag: 'if (%s == %s) ~= %s then pc++' % (RK(it.B, key), RK(it.C, key), it.A),
    24: lambda it, key, func, flag: 'if (%s == %s) <  %s then pc++' % (RK(it.B, key), RK(it.C, key), it.A),
    25: lambda it, key, func, flag: 'if (%s == %s) <= %s then pc++' % (RK(it.B, key), RK(it.C, key), it.A),

    26: lambda it, key, func, flag: 'if not (%s != %s) then pc++'        % (R(it.A), it.C),
    27: lambda it, key, func, flag: 'if %s != %s then %s = %s else pc++' % (R(it.B), it.C, R(it.A), R(it.B)),

    28: lambda it, key, func, flag: '%s = %s(%s)'       % (', '.join([R(i) for i in range(it.A, it.A + it.C - 1)]), R(it.A), ', '.join([R(i) for i in range(it.A + 1, it.A + it.B)])),
    29: lambda it, key, func, flag: 'return %s(%s)'     % (R(it.A), ', '.join([R(i) for i in range(it.A + 1, it.A + it.B)])),
    30: lambda it, key, func, flag: 'return %s'         % (', '.join([R(i) for i in range(it.A, it.A + it.B - 1)])),

    31: lambda it, key, func, flag: '%s + %s; if %s <= %s then { pc += %s; %s = %s }' % (R(it.A), R(it.A + 2), R(it.A), R(it.A + 1), it.Bx, R(it.A + 3), R(it.A)),
    32: lambda it, key, func, flag: '%s - %s; pc += %s' % (R(it.A), R(it.A + 2), it.Bx),

    33: lambda it, key, func, flag: '%s = %s(%s, %s); if %s ~= nil then %s = %s else pc++' 
                                        % (', '.join([R(i) for i in range(it.A + 3, it.A + it.C + 3)]), R(it.A), R(it.A + 1), R(it.A + 2), R(it.A + 3), R(it.A + 2), R(it.A + 3)),
    34: lambda it, key, func, flag: '%s[%s * FPF + i] = R(%s + i), i <= i <= %s' % (R(it.A), it.C + 1, it.A, it.B),

    35: lambda it, key, func, flag: 'close %s'  % (R(it.A)),
    36: lambda it, key, func, flag: '%s%s = function() end' % (F(it.A, flag), R(it.A)),
    37: lambda it, key, func, flag: '%s = vararg'       % (', '.join([R(i) for i in range(it.A, it.A + it.B)])),
}