import unittest

from leap.util import translations


class TrasnlationsTestCase(unittest.TestCase):
    """
    tests for translation functions and classes
    """

    def setUp(self):
        self.trClass = translations.LEAPTranslatable

    def test_trasnlatable(self):
        tr = self.trClass({"en": "house", "es": "casa"})
        eq = self.assertEqual
        eq(tr.tr(to="es"), "casa")
        eq(tr.tr(to="en"), "house")


if __name__ == "__main__":
    unittest.main()
