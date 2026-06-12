import unittest

from reopt_pysam_vn.reopt.sanitize import redact_sensitive_fields


class TestApiResultSanitization(unittest.TestCase):
    def test_redact_sensitive_fields_removes_api_keys_recursively(self):
        payload = {
            "api_key": "top-secret",
            "inputs": {
                "nested": {
                    "api_key": "nested-secret",
                    "keep": 123,
                }
            },
            "items": [
                {"api_key": "array-secret", "name": "row1"},
                "safe",
            ],
        }

        sanitized = redact_sensitive_fields(payload)

        self.assertNotIn("api_key", sanitized)
        self.assertNotIn("api_key", sanitized["inputs"]["nested"])
        self.assertNotIn("api_key", sanitized["items"][0])
        self.assertEqual(sanitized["inputs"]["nested"]["keep"], 123)
        self.assertEqual(sanitized["items"][1], "safe")


if __name__ == "__main__":
    unittest.main()
