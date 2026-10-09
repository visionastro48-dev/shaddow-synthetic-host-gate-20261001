import unittest
from health import get_health_status


class TestHealth(unittest.TestCase):
    def test_get_health_status(self):
        expected = {"status": "ok", "source": "jules-integration-smoke"}
        self.assertEqual(get_health_status(), expected)


if __name__ == "__main__":
    unittest.main()
