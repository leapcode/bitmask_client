import unittest

def test_suite():
    import tests.test_send

    suite = unittest.TestSuite()

    suite.addTest(tests.test_send.test_suite())

    return suite

