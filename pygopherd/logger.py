log = None
priority = None
facility = None
syslogfunc = None

def log_stdout(message):
    print message

def log_syslog(message):
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
        syslog.openlog('pygopherd', syslog.LOG_PID, facility)
        syslogfunc = syslog.syslog
        log = log_syslog
    elif logmethod == 'stdout':
        log = log_stdout
    else:
        log = log_none

