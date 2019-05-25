import ctypes
import math
import collections

def isiterable(obj):
    try:
        iterator = iter(obj)
    except TypeError:
        return False
    else:
        return True

# Calculates Root-mean-square deviation between numeric values in the given structs.
# mask may be nested. eg. {'player': {'position_vector':all} }
def struct_rms_deviation(struct1, struct2, mask=all):
    assert type(struct1) == type(struct2)
    if isinstance(struct1, str):
        return struct1 == struct2

    # Array of some kind
    if isiterable(struct1):
        if mask is all:
            mask = {i:all for i in range(len(struct1))}
        assert all(0 <= i < len(struct1) for i in mask)
        sum_of_square_deviation = 0
        for i, (item1, item2) in enumerate(zip(struct1, struct2)):
            if i not in mask:
                continue
            deviation = struct_rms_deviation(item1, item2, mask[i])
            sum_of_square_deviation += deviation * deviation

        return sum_of_square_deviation



    if mask is all:
        mask = {key: all for key,ctype in struct1._fields_}
    assert all(hasattr(struct1, key) for key in mask)

    sum_of_square_deviation = 0
    for key, ctype in struct1._fields_:
        if key not in mask:
            continue

        attr1 = getattr(struct1, key)
        attr2 = getattr(struct2, key)
        if any(issubclass(ctype, t) for t in [ctypes.c_int, ctypes.c_bool, ctypes.c_long, ctypes.c_float, ctypes.c_ubyte, ctypes.c_double]):
            deviation = attr1 - getattr(struct2, key)
            sum_of_square_deviation += deviation * deviation
        elif issubclass(ctype, ctypes.Structure) or isiterable(attr1):
            deviation = struct_rms_deviation(attr1, attr2, mask[key])
            sum_of_square_deviation += deviation * deviation
        elif issubclass(ctype, ctypes.c_wchar):
            continue
        else:
            print ('unsupported ctype: ', ctype, )
    return math.sqrt(sum_of_square_deviation)

def struct_equal(obj1, obj2):
    for fld in obj1._fields_:
        if getattr(obj1, fld[0]) != getattr(obj2, fld[0]):
            return False
    return True
