#!/usr/bin/python2.2 -i

# Python-based gopher server
# COPYRIGHT #
# Copyright (C) 2002 John Goerzen
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
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

#

from ConfigParser import ConfigParser
import socket, os, sys, signal

config = ConfigParser()
config.read("pygopherd.conf")


# Initialize server.

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', config.getint('serving', 'port')))
s.listen(25)

def closeupshop(signum, frame):
    s.close()
    print "Closeupshop."
    sys.exit(0)

signal.signal(signal.SIGINT, closeupshop)
signal.signal(signal.SIGQUIT, closeupshop)


while 1:
    conn, addr = s.accept()
    if os.fork():
        print "Parent.  Closing conn."
        conn.close()
    else:
        print "Child.  Closing s."
        s.close()
        print conn
        print addr
        conn.send("foo\n")
        conn.shutdown(2)
        conn.close()
        sys.exit(0)
