import codecs
import sys
import typing

log: typing.Callable[[str], None]
syslogfunc: typing.Callable[[int, str], None]
priority: int
facility: int

# Roundabout way to enable writing surrogate escapes to stdout
logfile = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="surrogateescape")


def log_file(message: str) -> None:
    logfile.write(message + "\n")


def setlogfile(file):
    global logfile
    logfile = file


def log_syslog(message: str) -> None:
    # TODO: Test w/ surrogate bytes
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
