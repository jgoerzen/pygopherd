#!/usr/bin/env python3
import setuptools

setuptools.setup(
    name="pygopherd",
    version="3.0.0.b2",
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
