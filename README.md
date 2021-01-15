[![Build](https://github.com/michael-lazar/pygopherd/workflows/Test/badge.svg)](https://github.com/michael-lazar/pygopherd/actions)
[![license GPLv2](https://img.shields.io/github/license/michael-lazar/pygopherd)](https://www.gnu.org/licenses/gpl-2.0.en.html)

# PyGopherd

PyGopherd is a multiprotocol (gopher, gopher+, http, wap) information server.

[PyGopherd Online User Manual](https://michael-lazar.github.io/pygopherd/doc/pygopherd.html)

## History

This repo is a fork of [jgoerzen/pygopherd](https://github.com/jgoerzen/pygopherd)
that adds support for Python 3.

If you're upgrading from an old version of PyGopherd, see the [upgrade notes](UPGRADING.md).

## Quickstart

### Debian

Use the .deb:

```
dpkg -i pygopherd.deb
```

or

```
apt-get install pygopherd
```

### Non-Debian

First, download and install Python 3.7 or higher.

You can run pygopherd either in-place (as a regular user account) or
as a system-wide daemon. For running in-place, do this:

```
PYTHONPATH=. bin/pygopherd conf/local.conf
```

For installing,

```
python3 setup.py install
```

Make sure that the ``/etc/pygopherd/pygopherd.conf`` names valid users
   (setuid, setgid) and valid document root (root).
