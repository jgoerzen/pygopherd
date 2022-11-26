THIS REPOSITORY IS OBSOLETE.

Pygopherd development continues with the Python 3 version at:

<https://github.com/michael-lazar/pygopherd>

OLD readme follows:

README for Pygopherd
===========================================================================

QUICKSTART (Debian)
-------------------

Use the .deb:

dpkg -i pygopherd.deb

or

apt-get install pygopherd

QUICKSTART (non-Debian)
-----------------------

1. Download and install Python 2.2 or above from www.python.org, if not already
   present on your system.

You can run pygopherd either in-place (as a regular user account) or
as a system-wide daemon.  For running in-place, do this:

1. Modify conf/pygopherd.conf:
   * Set usechroot = no
   * Comment out (add a # sign to the start of the line) the 
     pidfile, setuid, and setgid lines
   * Set mimetypes = ./conf/mime.types
   * Set root = to something appropriate.
   * Set port to a number greater than 1024.

2. Modify the first line of executables/pygopherd to reflect
   the location of your Python installation.

3. Invoke pygopherd by running:
   ./executables/pygopherd

For installing:

1. Run python2.2 setup.py install

2. Make sure that the /etc/pygopherd/pygopherd.conf names valid users
   (setuid, setgid) and valid document root (root).

