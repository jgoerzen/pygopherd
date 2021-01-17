import os
import signal
import sys

from pygopherd import logger

pid = None


def huphandler(signum, frame):
    logger.log("SIGHUP (%d) received; terminating process" % signum)
    os._exit(5)  # So we don't raise SystemExit


def termhandler(signum, frame):
    if os.getpid() == pid:  # Master killed; kill children.
        logger.log("SIGTERM (%d) received in master; doing orderly shutdown" % signum)
        logger.log("Terminating all of process group with SIGHUP")
        # Ignore this signal so that our own process won't get it again.
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        os.kill(0, signal.SIGHUP)
        logger.log("Master application process now exiting.  Goodbye.")
        sys.exit(6)
    else:  # Shouldn't need this -- just in case.
        logger.log("SIGTERM (%d) received in child; terminating this process" % signum)
        os._exit(7)  # So we don't raise SystemExit


def setsighuphandler():
    if "SIGHUP" in signal.__dict__:
        signal.signal(signal.SIGHUP, huphandler)


def setsigtermhandler():
    global pid
    pid = os.getpid()
    signal.signal(signal.SIGTERM, termhandler)
