import unittest

from google.appengine.ext import testbed


class AppengineTestCase(unittest.TestCase):
    def setUp(self):
        super(AppengineTestCase, self).setUp()
        self.tb = testbed.Testbed()
        self.tb.activate()
        self.tb.init_search_stub()

    def tearDown(self):
        self.tb.deactivate()
        super(AppengineTestCase, self).tearDown()
