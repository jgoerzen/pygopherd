#!/usr/bin/env python3

# Python-based gopher server
# Module: installer
# COPYRIGHT #
# Copyright (C) 2021 Michael Lazar
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
import setuptools

setuptools.setup(
    name="pygopherd",
    version="2.0.18",
    description="Multiprotocol Internet Gopher Information Server",
    author="Michael Lazar",
    author_email="lazar.michael22@gmail.com",
    python_requires=">=3.7",
    url="https://www.github.com/michael-lazar/pygopherd",
    packages=["pygopherd", "pygopherd.handlers", "pygopherd.protocols"],
    scripts=["bin/pygopherd"],
    data_files=[("/etc/pygopherd", ["conf/pygopherd.conf", "conf/mime.types"])],
    test_suite="pygopherd",
    license="GPLv2",
)
