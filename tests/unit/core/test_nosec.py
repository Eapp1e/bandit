#
# Copyright 2026 The Bandit Authors
#
# SPDX-License-Identifier: Apache-2.0
import os

import fixtures
import testtools

from bandit.core import config
from bandit.core import manager

WARNING = "nosec encountered"


class NosecReportingTests(testtools.TestCase):
    """Tests the reporting of ``#nosec`` comments that skip nothing."""

    def setUp(self):
        super().setUp()
        self.config = config.BanditConfig()
        self.logger = self.useFixture(fixtures.FakeLogger(level="DEBUG"))
        self.temp_dir = self.useFixture(fixtures.TempDir())

    def _run_bandit(self, source):
        path = os.path.join(self.temp_dir.path, "example.py")
        with open(path, "w") as fd:
            fd.write(source)

        mgr = manager.BanditManager(
            config=self.config, agg_type="file", debug=False, verbose=False
        )
        mgr.discover_files([path])
        mgr.run_tests()
        return mgr

    def test_nosec_in_multiline_statement_is_not_reported(self):
        # the string on line 2 raises B104 and is skipped by the comment,
        # the string on line 3 raises nothing but belongs to the same
        # statement, so the comment must not be reported as unused
        mgr = self._run_bandit(
            "values = [\n"
            '    "0.0.0.0",  # nosec: B104\n'
            '    "-h",\n'
            "]\n"
        )

        self.assertEqual([], mgr.results)
        self.assertNotIn(WARNING, self.logger.output)

    def test_nosec_without_matching_issue_is_reported(self):
        # B104 runs on the string but there is nothing to report for it
        mgr = self._run_bandit('bind_host = "127.0.0.1"  # nosec: B104\n')

        self.assertEqual([], mgr.results)
        self.assertIn(f"{WARNING} (B104)", self.logger.output)
        self.assertIn("example.py:1", self.logger.output)

    def test_nosec_reported_once_per_line(self):
        mgr = self._run_bandit(
            'first = "127.0.0.1"  # nosec: B104\n'
            'second = ("127.0.0.1")  # nosec: B104\n'
        )

        self.assertEqual([], mgr.results)
        self.assertEqual(2, self.logger.output.count(WARNING))

    def test_blanket_nosec_is_not_reported(self):
        mgr = self._run_bandit('bind_host = "0.0.0.0"  # nosec\n')

        self.assertEqual([], mgr.results)
        self.assertNotIn(WARNING, self.logger.output)
