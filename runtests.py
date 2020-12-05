#!/usr/bin/env python3
# Python-based gopher server
# Module: main test runner
# COPYRIGHT #
# Copyright (C) 2002-2019 John Goerzen
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
import sys
import tracemalloc
import unittest

if __name__ == "__main__":
    tracemalloc.start()

    suite = unittest.defaultTestLoader.discover(start_dir="pygopherd/", pattern="*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    sys.exit(not runner.run(suite).wasSuccessful())
