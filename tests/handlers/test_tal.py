from __future__ import annotations

import html
import io
import unittest

from pygopherd import initialization, testutil
from pygopherd.handlers.base import VFS_Real
from pygopherd.handlers.tal import TALFileHandler, talavailable

TEST_TEMPLATE = """
<html>
<head>
<title>TAL Test</title>
</head>
<body>
My selector is: <b>{selector}</b><br>
My MIME type is: <b>text/html</b><br>
Another way of getting that is: <b>text/html</b><br>
Gopher type is: <b>h</b><br>
My handler is: <b>{handler}</b><br>
My protocol is: <b>{protocol}</b><br>
Python path enabling status: <b>1</b><br>
My vfs is: <b>{vfs}</b><br>
Math: <b>4</b>
</body>
</html>
"""


class TestTALHandler(unittest.TestCase):
    def setUp(self):
        self.config = testutil.get_config()
        self.vfs = VFS_Real(self.config)
        self.selector = "/talsample.html.tal"
        self.protocol = testutil.get_testing_protocol(self.selector, config=self.config)
        self.stat_result = self.vfs.stat(self.selector)

        # Initialize the custom mimetypes encoding map
        initialization.init_logger(self.config, "")
        initialization.init_mimetypes(self.config)

    def test_tal_available(self):
        self.assertTrue(talavailable)

    def test_tal_handler(self):
        handler = TALFileHandler(
            self.selector, "", self.protocol, self.config, self.stat_result, self.vfs
        )

        self.assertTrue(handler.canhandlerequest())

        entry = handler.getentry()
        self.assertEqual(entry.mimetype, "text/html")
        self.assertEqual(entry.type, "h")

        wfile = io.BytesIO()
        handler.write(wfile)
        rendered_data = wfile.getvalue().decode()

        expected_data = TEST_TEMPLATE.format(
            selector=handler.selector,
            handler=html.escape(str(handler)),
            protocol=html.escape(str(self.protocol)),
            vfs=html.escape(str(self.vfs)),
        )

        self.assertEqual(rendered_data.strip(), expected_data.strip())
