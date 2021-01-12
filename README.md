[![Build](https://github.com/michael-lazar/pygopherd/workflows/Test/badge.svg)](https://github.com/michael-lazar/pygopherd/actions)

# PyGopherd

PyGopherd is a multiprotocol (gopher/gopher+/http/wap) gopher information server.

This repo is a fork of original PyGopherd project to add support for Python 3.

## Project Timeline

From 2002 to 2020, PyGopherd was created and maintained by John Gorzgen.

In 2020, with Python 2 being deprecated upstream and dropped by Debian
and other package managers, John expressed a lack of interest in updating
to code to support Python 3 himself.

In late 2020, Michael Lazar offered to help port the project to Python 3
and modernize the codebase. 

## Documentation

[PyGopherd User Manual](https://michael-lazar.github.io/pygopherd/doc/pygopherd.html)

## Quickstart (debian)

Use the .deb:

```
dpkg -i pygopherd.deb
```

or

```
apt-get install pygopherd
```

## Quickstart (non-debian)

First, download and install Python 3.7 or higher.

You can run pygopherd either in-place (as a regular user account) or
as a system-wide daemon. For running in-place, do this:

TODO
