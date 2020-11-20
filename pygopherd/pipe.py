# pygopherd -- Gopher-based protocol server in Python
# module: Execute children in a pipe.
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
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

import os
import sys

# Later we will check sys.platform


def pipedata_unix(
    file,
    args,
    environ=os.environ,
    childstdin=None,
    childstdout=None,
    childstderr=None,
    pathsearch=0,
):
    pid = os.fork()
    if pid:
        # Parent.
        return os.waitpid(pid, 0)[1]
    else:
        # Child.
        if childstdin:
            os.dup2(childstdin.fileno(), 0)
        if childstdout:
            os.dup2(childstdout.fileno(), 1)
        if childstderr:
            os.dup2(childstderr.fileno(), 2)
        if pathsearch:
            os.execvpe(file, args, environ)
        else:
            os.execve(file, args, environ)
        sys.exit(255)


pipedata = pipedata_unix
