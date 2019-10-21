
import unittest

import time
import server

class TestDefaultSubprocess(unittest.TestCase):

    def setUp(self):
        self.nh = server.default_subprocess()

    def tearDown(self):
        self.nh.terminate()

    def test_startup(self):
        data = self.nh.read()
        self.assertTrue(data, msg="Some output from nethack")

    def test_input(self):
        data = self.nh.read()
        while data:
            data = self.nh.read()
        self.nh.write(b' ')
        data = self.nh.read()
        print(data)
        self.assertTrue(data, msg="Input didn't create more output")

if __name__ == '__main__':
    unittest.main() 
