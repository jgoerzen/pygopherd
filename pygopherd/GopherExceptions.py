# pygopherd -- Gopher-based protocol server in Python
# module: exception declarations
# Copyright (C) 2002 John Goerzen
# <jgoerzen@complete.org>
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

import types

class FileNotFound:
    def __init__(self, arg):
        self.selector = arg
        self.comments = ''

        if type(arg) != types.StringType:
            self.selector = arg[0]
            self.comments = arg[1]
            
    def __str__(self):
        retval = "'%s' does not exist" % self.selector
        if self.comments:
            retval += " (%s)" % self.comments
        return retval
