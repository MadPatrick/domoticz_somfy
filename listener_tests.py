import unittest
import logging
import listener
import datetime

class ListenerTests(unittest.TestCase):
    """test cases for Listener ID handling"""
    def setUp(self):
        logging.debug("setting up a test run")
        self.listener = listener.Listener()
        self.listener2 = listener.Listener(4)
        
    def test_creation(self):
        """check set up of listener object"""
        logging.info("test: test_creation")
        self.assertEqual(self.listener.listenerId, None)
        self.assertEqual(self.listener.valid, False)

    def test_SettingValid(self):
        """not allowed to change the validity"""
        logging.info("test: test_SettingValid")
        with self.assertRaises(AttributeError):
            self.listener.valid = True

    def test_refresh(self):
        """check set up of listener object"""
        logging.info("test: test_refresh")
        self.listener.refresh_listener()
        self.assertEqual(self.listener.valid, True)

def main():
    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(filename)-18s - %(message)s', filename="somfy_unit_test.log",level=logging.DEBUG)
    logging.debug("=== unit tests for listener ===")
    unittest.main()

if __name__ == "__main__":
    main()
