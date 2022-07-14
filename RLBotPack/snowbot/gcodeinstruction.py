import re

class GcodeInstruction:
    line_re = re.compile(r"^G(1|0)(?=.*x(-?\d*(\.\d*)))(?=.*y(-?\d*(\.\d*))).*", flags=re.IGNORECASE)
    type_re = re.compile(r";TYPE:(.*)", flags=re.IGNORECASE)
    def __init__(self, line, line_number):
        self.line = line
        self.line_number = line_number
        self.type = None
        self.x = None
        self.y = None
        self.is_travel = False
        self.valid = True
        type_mo = self.type_re.match(line)
        if type_mo:
            self.type = type_mo.group(1)
        else:
            line_mo = self.line_re.match(line)
            if not line_mo:
                self.valid = False
                return
            self.x = float(line_mo.group(2))*100
            self.y = float(line_mo.group(4))*100
            self.is_travel = line_mo.group(1) == "0"