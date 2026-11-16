import unittest

from model_policy import validate


class ModelPolicyTests(unittest.TestCase):
    def test_allowed_requests(self):
        for surface in ("collaboration", "responses", "codex"):
            for effort in ("high", "xhigh", "max"):
                self.assertTrue(validate("gpt-6.1-sol", effort, surface)["allowed"])

    def test_disallowed_models_and_weak_efforts(self):
        for model in ("glm-53-flash", "gemma-4-26b-a4b-it", "gpt-6-astra", "gpt-6-sol", "deepseek", ""):
            with self.assertRaises(ValueError):
                validate(model, "max")
        for effort in ("none", "low", "medium", "", None):
            with self.assertRaises(ValueError):
                validate("gpt-6.1-sol", effort)

    def test_no_fallback_or_unsupported_ultra_surface(self):
        with self.assertRaises(ValueError):
            validate("gpt-6.1-sol", "high", fallback="glm-53-flash")
        self.assertTrue(validate("gpt-6.1-sol", "ultra", "collaboration")["allowed"])
        for surface in ("responses", "codex"):
            with self.assertRaises(ValueError):
                validate("gpt-6.1-sol", "ultra", surface)


if __name__ == "__main__":
    unittest.main()
