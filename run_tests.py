import unittest
import os

suite = unittest.TestLoader().discover(
    "tests", top_level_dir=os.path.abspath(os.pardir))
unittest.TextTestRunner(verbosity=2).run(suite)
