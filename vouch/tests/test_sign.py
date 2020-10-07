from unittest import TestCase

import vouch

class TestSign(TestCase):
    def test_is_string(self):
        self.assertTrue(isinstance('string', str))
