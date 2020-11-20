# Python-based gopher server
# Module: signal handlers
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# END OF COPYRIGHT #

import os
import signal
import sys

from pygopherd import logger

pgrp = None
pid = None


def huphandler(signum, frame):
    logger.log("SIGHUP (%d) received; terminating process" % signum)
    os._exit(5)  # So we don't raise SystemExit


def termhandler(signum, frame):
    if os.getpid() == pid:  # Master killed; kill children.
        logger.log("SIGTERM (%d) received in master; doing orderly shutdown" % signum)
        logger.log("Terminating all of process group %s with SIGHUP" % pgrp)
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


def setsigtermhandler(newpgrp):
    global pgrp, pid
    pgrp = newpgrp
    pid = os.getpid()
    signal.signal(signal.SIGTERM, termhandler)
