import sys
import codecs

log = None
# Roundabout way to enable writing surrogate escapes to stdout
logfile = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="surrogateescape")
priority = None
facility = None
syslogfunc = None


def log_file(message: str) -> None:
    logfile.write(message + "\n")


def setlogfile(file):
    global logfile
    logfile = file


def log_syslog(message: str) -> None:
    # TODO: Test w/ surrogate bytes
    if syslogfunc:
        syslogfunc(priority, message)


def log_none(message):
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
