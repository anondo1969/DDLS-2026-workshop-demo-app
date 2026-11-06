"""Static contract checks for container packaging and manual-only publication."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from app.data import CSV_NAME, DATA_PATH
from scripts.preflight import dockerignore_excludes_csv, run

ROOT = Path(__file__).resolve().parents[1]


class DeploymentContractTests(unittest.TestCase):
    def test_docker_context_contains_real_csv_and_expected_copy(self):
        self.assertTrue(DATA_PATH.is_file())
        self.assertEqual(DATA_PATH, ROOT / "data" / CSV_NAME)
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("RUN useradd -m -u 1000", dockerfile)
        self.assertIn("USER appuser", dockerfile)
        self.assertIn("COPY --chown=1000:1000 app/ ./", dockerfile)
        self.assertIn("COPY --chown=1000:1000 data/ $HOME/data/", dockerfile)
        self.assertIn("EXPOSE 8501", dockerfile)
        self.assertIn('"--server.port=8501"', dockerfile)
        self.assertIn('"--server.address=0.0.0.0"', dockerfile)
        self.assertIn("_stcore/health", dockerfile)
        self.assertFalse(
            dockerignore_excludes_csv((ROOT / ".dockerignore").read_text(encoding="utf-8"))
        )
        # app/data.py derives its path relative to itself, not the current directory.
        container_module = PurePosixPath("/home/appuser/app/data.py")
        container_csv = container_module.parent.parent / "data" / CSV_NAME
        self.assertEqual(str(container_csv), "/home/appuser/data/" + CSV_NAME)

    def test_simulated_container_layout_loads_csv(self):
        # Docker itself is unavailable in the local review environment.
        # Re-create the two COPY destinations and run data.py from WORKDIR.
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home" / "appuser"
            code_dir = home / "app"
            data_dir = home / "data"
            code_dir.mkdir(parents=True)
            data_dir.mkdir()
            shutil.copy2(ROOT / "app/data.py", code_dir / "data.py")
            shutil.copy2(DATA_PATH, data_dir / CSV_NAME)
            check = (
                "import data; "
                "frame=data.load_data(); "
                "assert len(frame)==308; "
                "assert float(frame.query(\"area=='Riket' and year==2025\").iloc[0].treated_per_1000)==48.80; "
                "print(str(data.DATA_PATH))"
            )
            proc = subprocess.run(
                [sys.executable, "-c", check],
                cwd=code_dir,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            # self.assertEqual(Path(proc.stdout.strip()), data_dir / CSV_NAME)

    def test_dockerignore_common_exclusions_are_detected(self):
        self.assertTrue(dockerignore_excludes_csv("data/\n"))
        self.assertTrue(dockerignore_excludes_csv("*.csv\n"))
        self.assertTrue(dockerignore_excludes_csv("data/*.csv\n"))
        self.assertFalse(dockerignore_excludes_csv("# data/\n*.log\n"))
        self.assertFalse(dockerignore_excludes_csv("*.csv\n!data/" + CSV_NAME + "\n"))

    def test_manual_image_publication_not_on_push(self):
        workflow = (ROOT / ".github/workflows/docker-image-ghcr.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("docker buildx build --platform linux/amd64", workflow)
        for step in (
            "Log in to GitHub Container Registry",
            "Publish validated image to GHCR",
            "Deployment image reference",
        ):
            self.assertRegex(
                workflow,
                re.escape("- name: " + step) + r"\n\s+if: github\.event_name == 'workflow_dispatch'",
            )
        self.assertEqual(run(strict=True), [])


if __name__ == "__main__":
    unittest.main()
