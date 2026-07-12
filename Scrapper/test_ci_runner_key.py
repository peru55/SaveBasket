import os
import tempfile
import unittest
from unittest.mock import patch

import ci_runner


class ResolveApiKeyTests(unittest.TestCase):
    def write_env(self, value):
        env_file = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        )
        self.addCleanup(lambda: os.unlink(env_file.name))
        env_file.write(f"SCRAPER_API_KEY={value}\n")
        env_file.close()
        return env_file.name

    def test_cli_key_takes_precedence(self):
        env_path = self.write_env("file-key")

        result = ci_runner.resolve_api_key(
            "cli-key",
            environ={"SCRAPER_API_KEY": "process-key"},
            env_path=env_path,
        )

        self.assertEqual(result, "cli-key")

    def test_process_environment_precedes_dotenv_file(self):
        env_path = self.write_env("file-key")

        result = ci_runner.resolve_api_key(
            None,
            environ={"SCRAPER_API_KEY": "process-key"},
            env_path=env_path,
        )

        self.assertEqual(result, "process-key")

    def test_uses_dotenv_file_as_local_fallback(self):
        env_path = self.write_env("file-key")

        result = ci_runner.resolve_api_key(None, environ={}, env_path=env_path)

        self.assertEqual(result, "file-key")

    def test_returns_none_when_no_key_source_exists(self):
        result = ci_runner.resolve_api_key(
            None,
            environ={},
            env_path="missing-backend.env",
        )

        self.assertIsNone(result)


class RunnerKeyValidationTests(unittest.TestCase):
    def test_backend_push_without_key_fails_before_scraping(self):
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as jobs_file:
            jobs_file.write("https://example.test/product\n")
        self.addCleanup(lambda: os.unlink(jobs_file.name))

        with (
            patch.object(ci_runner, "DEFAULT_BACKEND_ENV_FILE", "missing.env"),
            patch.dict(os.environ, {}, clear=True),
            patch.object(ci_runner, "build_payload_from_url") as build_payload,
            self.assertRaises(SystemExit) as error,
        ):
            ci_runner.main(
                [
                    "--backend",
                    "http://127.0.0.1:8000",
                    "--jobs-file",
                    jobs_file.name,
                ]
            )

        self.assertEqual(error.exception.code, 2)
        build_payload.assert_not_called()


if __name__ == "__main__":
    unittest.main()
