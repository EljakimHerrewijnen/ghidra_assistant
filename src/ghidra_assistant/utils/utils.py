import struct, string, logging, typing
from .definitions import *

class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    blue = "\x1b[36;20m"
    green = "\x1b[32;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(name)s | %(levelname)s | %(message)s" # (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logger(name):
    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())
    if name in logging.Logger.manager.loggerDict:
        return logging.getLogger(name)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger


def _configure_root_logger() -> None:
    """Wire CustomFormatter onto the root logger exactly once.

    Child loggers (e.g. ``logging.getLogger(__name__)``) propagate to root
    by default, so they will all inherit coloured output without any extra
    setup.
    """
    root = logging.root
    if not any(isinstance(h, logging.StreamHandler) and isinstance(getattr(h, 'formatter', None), CustomFormatter)
               for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(CustomFormatter())
        root.addHandler(handler)
    if root.level == logging.WARNING:   # default – open up to DEBUG
        root.setLevel(logging.DEBUG)


_configure_root_logger()

# Package-level logger – use this for all module code that imports from utils
_log = logging.getLogger("ghidra_assistant")

info    = _log.info
debug   = _log.debug
ok      = _log.info      # success / confirmation messages → INFO
warn    = _log.warning
warning = _log.warning
error   = _log.error
critic  = _log.critical

KB = 1024
MB = KB * 1024
GB = MB * 1024
TB = GB * 1024
PB = TB * 1024

COLOR_PURPLE    = '\033[95m'
COLOR_BLUE      = '\033[94m'
COLOR_LBLUE     = '\033[96m'
COLOR_GREEN     = '\033[92m'
COLOR_YELLOW    = '\033[93m'
COLOR_RED       = '\033[91m'
COLOR_END           = '\033[0m'
COLOR_BOLD          = '\033[1m'
COLOR_UNDERLINE     = '\033[4m'

def p_info(msg):
    info(msg)

def p_ok(msg):
    ok(msg)

def p_warn(msg):
    warn(msg)

def p_error(msg):
    error(msg)

def p64(val):
    return struct.pack("<Q", val)

def bytes_len_hex(inbytes, str_len):
    return (inbytes[str_len:], inbytes[:str_len].encode("hex"))

def bytes_len(inbytes, str_len):
    return (inbytes[str_len:], inbytes[:str_len])

def utf16_str(inbytes, str_len):
    data = inbytes[:str_len]
    stri = ""
    for i in range(0, len(data), 2):
        if data[i] == "\x00":
            break
        stri += data[i]
    return (inbytes[str_len:], stri)

def str_len(inbytes, str_len):
    return (inbytes[str_len:], inbytes[:str_len].split("\x00")[0])

def u64(inbytes):
    return struct.unpack("<Q", inbytes[:8])[0]
    # return (inbytes[8:], struct.unpack("<Q", inbytes[:8])[0])

def u32(s):
    """u32(s) -> int
    Unpack 32 bits integer from a little endian str representation
    """
    return struct.unpack('<I', s)[0]


def u16(inbytes):
    return struct.unpack("<H", inbytes[:2])[0]


def u8(inbytes):
    return ord(inbytes[:1])

def p8(i):
    """p8(i) -> str
    Pack 8 bits integer
    """
    return struct.pack('B', i)

def p32(i):
    """p32(i) -> str
    Pack 32 bits integer (little endian)
    """
    return struct.pack('<I', i)

def round_down(address, align):
    """round_down(address, align) -> int
    Round down ``address`` to the nearest increment of ``align``.
    """
    return address & ~(align-1)

def page_align(address):
    """page_align(address) -> int
    Round down ``address`` to the nearest page boundary.
    """
    return round_down(address, 0x1000)

def align_top(address, align):
    """page_align_up(address) -> int
    Round up ``address`` to the nearest page boundary.
    """
    return round_down(address + align, align)

def page_align_top(address):
    """page_align_up(address) -> int
    Round up ``address`` to the nearest page boundary.
    """
    return round_down(address + 0x1000, 0x1000)

def util_get_mmu_entry(base, address):
    # May not work on other SDM
    # work only for level 1
    return base + 8 * (0x200 + ((page_align(address) >> 12) & 0x1FF))

def simple_hexdump(src, length=16, sep='.', start = 0):
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
    lines = []
    for c in range(0, len(src), length):
        chars = src[c:c+length]

        hexstr = ' '.join(["%02x" % ord(x) for x in chars]) if type(chars) is str else ' '.join(['{:02x}'.format(x) for x in chars])
        if len(hexstr) > 24:
            hexstr = "%s %s" % (hexstr[:24], hexstr[24:])
        printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars]) if type(chars) is str else ''.join(['{}'.format((x <= 127 and FILTER[x]) or sep) for x in chars])
        lines.append("%08x:  %-*s  |%s|" % (c + start, length*3, hexstr, printable))
    return lines

def print_addr64(addr : bytes):
    print(hex(struct.unpack("<Q", addr)[0]))

def hexdump(buf, title="", color=6, start=0, remove_dup=True):
    if type(buf) == bytearray:
        buf = bytes(buf)
    color_start = "\033[3%d;1m" % color
    color_start_no_bold = "\033[0m\033[3%dm" % color
    color_stop = "\033[0m"

    address_format_size = len("0x%08x " % (len(buf) + start))
    space_before = " "*address_format_size

    out=("%s%s┌"+"─"*49+"┬"+"─"*18+"┐%s\n") % (space_before, color_start,color_stop)
    if title != "":
        dashlen = int((46-len(title))/2)
        out=("%s%s┌"+"─"*dashlen+"  "+title+"  "+"─"*(dashlen-(1-(len(title)%2)))+"┬"+"─"*18+"┐%s\n") % (space_before, color_start,color_stop)
    last_is_dup = False
    for i in range(0,len(buf),16):
        if remove_dup:
            if i != 0 and (i+16) < len(buf):
                if buf[i:i+16] == buf[i-16:i] and buf[i:i+16] == buf[i+16:i+32]:
                    if not last_is_dup:
                        out+="%s%s* ┆ %s" % (space_before[:-2], color_start, color_start_no_bold)
                        out+="⇩"*47
                        out+="%s ┆ %s" % (color_start, color_start_no_bold)
                        out+="⇩"*16
                        out+=" %s┆%s\n" % (color_start, color_stop)
                    last_is_dup = True
                    continue
                else:
                    last_is_dup=False
        out+="%s0x%08x │ %s" % (color_start,i+start,color_stop)
        for j in range(16):
            if i+j < len(buf):
                if type(buf) == bytes:
                    out+="%02x " % (buf[i+j])
                else:
                    out+="%02x " % (ord(buf[i+j]))
            else:
                out+="   "
        out+="%s│ %s" % (color_start,color_stop)
        for j in range(16):
            if i+j < len(buf):
                char = buf[i+j]
                if type(char) == int:
                    char = chr(char)
                if char in string.printable and char not in "\t\n\r\x0b\x0c":
                    out+="%s" % (char)
                else:
                    out+="."
            else:
                out+=" "
        out+=" %s│%s\n" % (color_start,color_stop)
    out+=("%s%s└"+"─"*49+"┴"+"─"*18+"┘%s") % (space_before, color_start,color_stop)
    print(out)

if __name__ == "__main__":
    print(f"{COLOR_BLUE}BLUE{COLOR_END}")
    print(f"{COLOR_PURPLE}PURPLE{COLOR_END}")
    print(f"{COLOR_LBLUE}LBLUE{COLOR_END}")
    print(f"{COLOR_GREEN}GREEN{COLOR_END}")
    print(f"{COLOR_YELLOW}YELLOW{COLOR_END}")
    print(f"{COLOR_RED}RED{COLOR_END}")
    print(f"{COLOR_BOLD}BOLD{COLOR_END}")
    print(f"{COLOR_UNDERLINE}UNDERLINE{COLOR_END}")