#!/usr/bin/python
import mimetypes
import socketserver
import unittest

from pygopherd import fileext, initialization


class InitializationConfigTestCase(unittest.TestCase):
    def test_init_config(self):
        self.assertRaises(Exception, initialization.init_config, "/foo")
        # Load the standard config file.  It should be OK at least.
        config = initialization.init_config("conf/pygopherd.conf")
        assert not config.has_option(
            "pygopherd", "servername"
        ), "servername should be disabled by default"
        self.assertEqual(config.getint("pygopherd", "port"), 70, "Port should be 70")
        self.assertEqual(
            config.get("pygopherd", "servertype"),
            "ForkingTCPServer",
            "Servertype should be ForkingTCPServer",
        )
        assert config.getboolean(
            "pygopherd", "tracebacks"
        ), "Tracebacks should be enabled."


class InitializationGeneralTestCase(unittest.TestCase):
    def setUp(self):
        self.config = initialization.init_config("conf/pygopherd.conf")

    def test_init_logger(self):
        # FIXME Can't really test this.
        pass

    def test_init_mimetypes_except(self):
        self.config.set("pygopherd", "mimetypes", "/foo:/bar")
        self.assertRaises(Exception, initialization.init_mimetypes, self.config)

    def test_init_mimetypes(self):
        # Logger is required for this test.
        self.config.set("logger", "logmethod", "none")
        initialization.init_logger(self.config, "TESTING")
        initialization.init_mimetypes(self.config)
        self.assertEqual(mimetypes.types_map[".txt"], "text/plain")
        self.assertEqual(mimetypes.encodings_map[".bz2"], "bzip2")
        assert ".txt" in fileext.typemap["text/plain"]

    def test_get_server(self):
        self.config.set("pygopherd", "port", "22270")
        s = initialization.get_server(self.config)
        assert isinstance(s, socketserver.ForkingTCPServer)
        s.server_close()

    def test_init_security(self):
        # FIXME
        pass
