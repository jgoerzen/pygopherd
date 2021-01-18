import sys
import typing

log: typing.Callable[[str], None]
syslogfunc: typing.Callable[[int, str], None]
priority: int
facility: int


def log_file(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode(errors="surrogateescape"))
    sys.stdout.buffer.flush()


def log_syslog(message: str) -> None:
    # Python's syslog forces UTF-8 and doesn't allow surrogate escapes.
    # Even though RFC 5424 clearly states the syslog encoding is optional.
    #
    # > The character set used in MSG SHOULD be UNICODE, encoded using UTF-8
    # > as specified in [RFC3629].  If the syslog application cannot encode
    # > the MSG in Unicode, it MAY use any other encoding.
    #
    # Come on python
    message_bytes = message.encode(errors="surrogateescape")
    message = message_bytes.decode("utf-8", errors="backslashreplace")
    syslogfunc(priority, message)


def log_none(message: str):
    pass


def init(config):
    global log, priority, facility, syslogfunc
    logmethod = config.get("logger", "logmethod")
    if logmethod == "syslog":
        import syslog

        priority = eval("syslog." + config.get("logger", "priority"))
        facility = eval("syslog." + config.get("logger", "facility"))
        syslog.openlog("pygopherd", syslog.LOG_PID, facility)
        syslogfunc = syslog.syslog
        log = log_syslog
    elif logmethod == "file":
        log = log_file
    else:
        log = log_none
