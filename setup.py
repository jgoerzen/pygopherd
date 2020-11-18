#!/usr/bin/env python3

# Python-based gopher server
# Module: installer
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


from distutils.core import setup
import pygopherd.version

setup(
    name="pygopherd",
    version=pygopherd.version.versionstr,
    description=pygopherd.version.description,
    author=pygopherd.version.author,
    author_email=pygopherd.version.author_email,
    url=pygopherd.version.homepage,
    packages=["pygopherd", "pygopherd.handlers", "pygopherd.protocols"],
    scripts=["bin/pygopherd"],
    data_files=[("/etc/pygopherd", ["conf/pygopherd.conf", "conf/mime.types"])],
    license=pygopherd.version.license,
)
