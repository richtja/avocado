import json
import os
import shutil
import time
import sys
import tempfile
import xml.dom.minidom
import glob

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import exit_codes
from avocado.utils import process
from avocado.utils import script


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

PASS_SHELL_CONTENTS = "exit 0"

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""

FAIL_SHELL_CONTENTS = "exit 1"

VOID_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.core.plugins.plugin import Plugin
class VoidPlugin(Plugin):
    pass
"""

SYNTAX_ERROR_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.core.plugins.plugin import Plugin
class VoidPlugin(Plugin)
"""

HELLO_PLUGIN_CONTENTS = """#!/usr/bin/env python
from avocado.core.plugins.plugin import Plugin
class HelloWorld(Plugin):
    name = 'hello'
    enabled = True
    def configure(self, parser):
        self.parser = parser.subcommands.add_parser('hello')
        super(HelloWorld, self).configure(self.parser)
    def run(self, args):
        print('Hello World!')
"""


class RunnerOperationTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_all_ok(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s passtest passtest' % self.tmpdir
        process.run(cmd_line)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_datadir_alias(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s datadir' % self.tmpdir
        process.run(cmd_line)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_datadir_noalias(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s examples/tests/datadir.py '
                    'examples/tests/datadir.py' % self.tmpdir)
        process.run(cmd_line)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_noalias(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s examples/tests/passtest.py "
                    "examples/tests/passtest.py" % self.tmpdir)
        process.run(cmd_line)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_tests_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s passtest failtest passtest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_nonexistent_test(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s bogustest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_doublefail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s --xunit - doublefail' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("TestError: Failing during tearDown. Yay!", output,
                      "Cleanup exception not printed to log output")
        self.assertIn("TestFail: This test is supposed to fail",
                      output,
                      "Test did not fail with action exception:\n%s" % output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_uncaught_exception(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - uncaught_exception" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "ERROR"', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_fail_on_exception(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - fail_on_exception" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "FAIL"', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_timeout(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s --xunit - timeouttest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn("TestTimeoutError: Timeout reached waiting for", output,
                      "Test did not fail with timeout exception:\n%s" % output)
        # Ensure no test aborted error messages show up
        self.assertNotIn("TestAbortedError: Test aborted unexpectedly", output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_abort(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s --xunit - abort' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        excerpt = 'Test process aborted'
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        unexpected_rc = exit_codes.AVOCADO_FAIL
        self.assertNotEqual(result.exit_status, unexpected_rc,
                            "Avocado crashed (rc %d):\n%s" % (unexpected_rc, result))
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))
        self.assertIn(excerpt, output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_silent_output(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s passtest --silent' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        expected_output = ''
        self.assertEqual(result.exit_status, expected_rc)
        self.assertEqual(result.stderr, expected_output)

    def test_empty_args_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        expected_output = 'error: too few arguments'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn(expected_output, result.stderr)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_empty_test_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        expected_output = 'No tests found for given urls'
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn(expected_output, result.stderr)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_not_found(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.assertEqual(result.exit_status, expected_rc)
        self.assertIn('Unable to discover url', result.stderr)
        self.assertNotIn('Unable to discover url', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_invalid_unique_id(self):
        cmd_line = './scripts/avocado run --sysinfo=off --force-job-id foobar passtest'
        result = process.run(cmd_line, ignore_status=True)
        self.assertNotEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertIn('needs to be a 40 digit hex', result.stderr)
        self.assertNotIn('needs to be a 40 digit hex', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_valid_unique_id(self):
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    '--force-job-id 975de258ac05ce5e490648dec4753657b7ccc7d1 passtest' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertNotIn('needs to be a 40 digit hex', result.stderr)
        self.assertIn('PASS', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_automatic_unique_id(self):
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off passtest --json -' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        r = json.loads(result.stdout)
        int(r['job_id'], 16)  # it's an hex number
        self.assertEqual(len(r['job_id']), 40)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_skip_outside_setup(self):
        os.chdir(basedir)
        cmd_line = ("./scripts/avocado run --sysinfo=off --job-results-dir %s "
                    "--json - skip_outside_setup" % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc,
                                                                result))
        self.assertIn('"status": "ERROR"', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_early_latest_result(self):
        """
        Tests that the `latest` link to the latest job results is created early
        """
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --sysinfo=off --job-results-dir %s '
                    'examples/tests/passtest.py' % self.tmpdir)
        avocado_process = process.SubProcess(cmd_line)
        avocado_process.start()
        link = os.path.join(self.tmpdir, 'latest')
        for trial in xrange(0, 50):
            time.sleep(0.1)
            if os.path.exists(link) and os.path.islink(link):
                avocado_process.wait()
                break
        self.assertTrue(os.path.exists(link))
        self.assertTrue(os.path.islink(link))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_dry_run(self):
        os.chdir(basedir)
        cmd = ("./scripts/avocado run --sysinfo=off passtest failtest "
               "errortest --json - --mux-inject foo:1 bar:2 baz:3 foo:foo:a "
               "foo:bar:b foo:baz:c bar:bar:bar --dry-run")
        result = json.loads(process.run(cmd).stdout)
        debuglog = result['debuglog']
        log = open(debuglog, 'r').read()
        # Remove the result dir
        shutil.rmtree(os.path.dirname(os.path.dirname(debuglog)))
        self.assertIn('/tmp', debuglog)   # Use tmp dir, not default location
        self.assertEqual(result['job_id'], u'0' * 40)
        # Check if all tests were skipped
        self.assertEqual(result['skip'], 3)
        for i in xrange(3):
            test = result['tests'][i]
            self.assertEqual(test['fail_reason'],
                             u'Test skipped due to --dry-run')
        # Check if all params are listed
        # The "/:bar ==> 2 is in the tree, but not in any leave so inaccessible
        # from test.
        for line in ("/:foo ==> 1", "/:baz ==> 3", "/foo:foo ==> a",
                     "/foo:bar ==> b", "/foo:baz ==> c", "/bar:bar ==> bar"):
            self.assertEqual(log.count(line), 3)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class RunnerHumanOutputTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_output_pass(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s passtest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('passtest.py:PassTest.test:  PASS', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_output_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s failtest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('failtest.py:FailTest.test:  FAIL', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_output_error(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s errortest' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('errortest.py:ErrorTest.test:  ERROR', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_output_skip(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --sysinfo=off --job-results-dir %s skiponsetup' % self.tmpdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('skiponsetup.py:SkipOnSetupTest.test_wont_be_executed:'
                      '  SKIP', result.stdout)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_ugly_echo_cmd(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("Program /bin/echo does not exist")
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run "/bin/echo -ne '
                    'foo\\\\\\n\\\'\\\\\\"\\\\\\nbar/baz" --job-results-dir %s'
                    ' --sysinfo=off  --show-job-log' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %s:\n%s" %
                         (expected_rc, result))
        self.assertIn('[stdout] foo', result.stdout, result)
        self.assertIn('[stdout] \'"', result.stdout, result)
        self.assertIn('[stdout] bar/baz', result.stdout, result)
        self.assertIn('PASS /bin/echo -ne foo\\\\n\\\'\\"\\\\nbar/baz',
                      result.stdout, result)
        # logdir name should escape special chars (/)
        test_dirs = glob.glob(os.path.join(self.tmpdir, 'latest',
                                           'test-results', '*'))
        self.assertEqual(len(test_dirs), 1, "There are multiple directories in"
                         " test-results dir, but only one test was executed: "
                         "%s" % (test_dirs))
        self.assertEqual(os.path.basename(test_dirs[0]),
                         '_bin_echo -ne foo\\\\n\\\'\\"\\\\nbar_baz')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class RunnerSimpleTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.pass_script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_simpletest_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript('avocado_fail.sh',
                                                  FAIL_SCRIPT_CONTENTS,
                                                  'avocado_simpletest_'
                                                  'functional')
        self.fail_script.save()

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_simpletest_pass(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, self.pass_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_simpletest_fail(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, self.fail_script.path))
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_onehundred_fail_timing(self):
        """
        We can be pretty sure that a failtest should return immediattely. Let's
        run 100 of them and assure they not take more than 30 seconds to run.

        Notice: on a current machine this takes about 0.12s, so 30 seconds is
        considered to be pretty safe here.
        """
        os.chdir(basedir)
        one_hundred = 'failtest ' * 100
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' %s' % (self.tmpdir, one_hundred))
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 30.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_runner_sleep_fail_sleep_timing(self):
        """
        Sleeptest is supposed to take 1 second, let's make a sandwich of
        100 failtests and check the test runner timing.
        """
        os.chdir(basedir)
        sleep_fail_sleep = 'sleeptest ' + 'failtest ' * 100 + 'sleeptest'
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off %s' % (
            self.tmpdir, sleep_fail_sleep)
        initial_time = time.time()
        result = process.run(cmd_line, ignore_status=True)
        actual_time = time.time() - initial_time
        self.assertLess(actual_time, 33.0)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" % (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_simplewarning(self):
        """
        simplewarning.sh uses the avocado-bash-utils
        """
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off '
                    'examples/tests/simplewarning.sh --show-job-log' % self.tmpdir)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %s:\n%s" %
                         (expected_rc, result))
        self.assertIn('DEBUG| Debug message', result.stdout, result)
        self.assertIn('INFO | Info message', result.stdout, result)
        self.assertIn('WARN | Warning message (should cause this test to '
                      'finish with warning)', result.stdout, result)
        self.assertIn('ERROR| Error message (ordinary message not changing '
                      'the results)', result.stdout, result)

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        shutil.rmtree(self.tmpdir)


class ExternalRunnerTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.pass_script = script.TemporaryScript(
            'pass',
            PASS_SHELL_CONTENTS,
            'avocado_externalrunner_functional')
        self.pass_script.save()
        self.fail_script = script.TemporaryScript(
            'fail',
            FAIL_SHELL_CONTENTS,
            'avocado_externalrunner_functional')
        self.fail_script.save()

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_externalrunner_pass(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh %s'
        cmd_line %= (self.tmpdir, self.pass_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_externalrunner_fail(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh %s'
        cmd_line %= (self.tmpdir, self.fail_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_TESTS_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_externalrunner_chdir_no_testdir(self):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off --external-runner=/bin/sh '
                    '--external-runner-chdir=test %s')
        cmd_line %= (self.tmpdir, self.pass_script.path)
        result = process.run(cmd_line, ignore_status=True)
        expected_output = ('Option "--external-runner-chdir=test" requires '
                           '"--external-runner-testdir" to be set')
        self.assertIn(expected_output, result.stderr)
        expected_rc = exit_codes.AVOCADO_JOB_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        shutil.rmtree(self.tmpdir)


class AbsPluginsTest(object):

    def setUp(self):
        self.base_outputdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def tearDown(self):
        shutil.rmtree(self.base_outputdir)


class PluginsTest(AbsPluginsTest, unittest.TestCase):

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_sysinfo_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado sysinfo %s' % self.base_outputdir
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        sysinfo_files = os.listdir(self.base_outputdir)
        self.assertGreater(len(sysinfo_files), 0, "Empty sysinfo files dir")

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_list_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado list'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('No tests were found on current tests dir', output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_list_error_output(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado list sbrubles'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stderr
        expected_rc = exit_codes.AVOCADO_FAIL
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn("Unable to discover url", output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_plugin_list(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado plugins'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        if sys.version_info[:2] >= (2, 7, 0):
            self.assertNotIn('Disabled', output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_config_plugin(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado config --paginator off'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_config_plugin_datadir(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado config --datadir --paginator off'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stdout
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn('Disabled', output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_Namespace_object_has_no_attribute(self):
        os.chdir(basedir)
        cmd_line = './scripts/avocado plugins'
        result = process.run(cmd_line, ignore_status=True)
        output = result.stderr
        expected_rc = exit_codes.AVOCADO_ALL_OK
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertNotIn("'Namespace' object has no attribute", output)


class ParseXMLError(Exception):
    pass


class PluginsXunitTest(AbsPluginsTest, unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        super(PluginsXunitTest, self).setUp()

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nnotfound, e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off'
                    ' --xunit - %s' % (self.tmpdir, testname))
        result = process.run(cmd_line, ignore_status=True)
        xml_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            xunit_doc = xml.dom.minidom.parseString(xml_output)
        except Exception, detail:
            raise ParseXMLError("Failed to parse content: %s\n%s" %
                                (detail, xml_output))

        testsuite_list = xunit_doc.getElementsByTagName('testsuite')
        self.assertEqual(len(testsuite_list), 1, 'More than one testsuite tag')

        testsuite_tag = testsuite_list[0]
        self.assertEqual(len(testsuite_tag.attributes), 7,
                         'The testsuite tag does not have 7 attributes. '
                         'XML:\n%s' % xml_output)

        n_tests = int(testsuite_tag.attributes['tests'].value)
        self.assertEqual(n_tests, e_ntests,
                         "Unexpected number of executed tests, "
                         "XML:\n%s" % xml_output)

        n_errors = int(testsuite_tag.attributes['errors'].value)
        self.assertEqual(n_errors, e_nerrors,
                         "Unexpected number of test errors, "
                         "XML:\n%s" % xml_output)

        n_failures = int(testsuite_tag.attributes['failures'].value)
        self.assertEqual(n_failures, e_nfailures,
                         "Unexpected number of test failures, "
                         "XML:\n%s" % xml_output)

        n_skip = int(testsuite_tag.attributes['skip'].value)
        self.assertEqual(n_skip, e_nskip,
                         "Unexpected number of test skips, "
                         "XML:\n%s" % xml_output)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_xunit_plugin_passtest(self):
        self.run_and_check('passtest', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0, 0)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_xunit_plugin_failtest(self):
        self.run_and_check('failtest', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 0, 1, 0)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_xunit_plugin_skiponsetuptest(self):
        self.run_and_check('skiponsetup', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0, 1)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_xunit_plugin_errortest(self):
        self.run_and_check('errortest', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super(PluginsXunitTest, self).tearDown()


class ParseJSONError(Exception):
    pass


class PluginsJSONTest(AbsPluginsTest, unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        super(PluginsJSONTest, self).setUp()

    def run_and_check(self, testname, e_rc, e_ntests, e_nerrors,
                      e_nfailures, e_nskip):
        os.chdir(basedir)
        cmd_line = ('./scripts/avocado run --job-results-dir %s --sysinfo=off --json - --archive %s' %
                    (self.tmpdir, testname))
        result = process.run(cmd_line, ignore_status=True)
        json_output = result.stdout
        self.assertEqual(result.exit_status, e_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (e_rc, result))
        try:
            json_data = json.loads(json_output)
        except Exception, detail:
            raise ParseJSONError("Failed to parse content: %s\n%s" %
                                 (detail, json_output))
        self.assertTrue(json_data, "Empty JSON result:\n%s" % json_output)
        self.assertIsInstance(json_data['tests'], list,
                              "JSON result lacks 'tests' list")
        n_tests = len(json_data['tests'])
        self.assertEqual(n_tests, e_ntests,
                         "Different number of expected tests")
        n_errors = json_data['errors']
        self.assertEqual(n_errors, e_nerrors,
                         "Different number of expected tests")
        n_failures = json_data['failures']
        self.assertEqual(n_failures, e_nfailures,
                         "Different number of expected tests")
        n_skip = json_data['skip']
        self.assertEqual(n_skip, e_nskip,
                         "Different number of skipped tests")
        return json_data

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_json_plugin_passtest(self):
        self.run_and_check('passtest', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 0)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_json_plugin_failtest(self):
        self.run_and_check('failtest', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 0, 1, 0)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_json_plugin_skiponsetuptest(self):
        self.run_and_check('skiponsetup', exit_codes.AVOCADO_ALL_OK,
                           1, 0, 0, 1)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_json_plugin_errortest(self):
        self.run_and_check('errortest', exit_codes.AVOCADO_TESTS_FAIL,
                           1, 1, 0, 0)

    @unittest.skip("Temporary plugin infrastructure removal")
    def test_ugly_echo_cmd(self):
        if not os.path.exists("/bin/echo"):
            self.skipTest("Program /bin/echo does not exist")
        data = self.run_and_check('"/bin/echo -ne foo\\\\\\n\\\'\\\\\\"\\\\\\'
                                  'nbar/baz"', exit_codes.AVOCADO_ALL_OK, 1, 0,
                                  0, 0)
        # The executed test should be this
        self.assertEqual(data['tests'][0]['url'],
                         '/bin/echo -ne foo\\\\n\\\'\\"\\\\nbar/baz')
        # logdir name should escape special chars (/)
        self.assertEqual(os.path.basename(data['tests'][0]['logdir']),
                         '_bin_echo -ne foo\\\\n\\\'\\"\\\\nbar_baz')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super(PluginsJSONTest, self).tearDown()

if __name__ == '__main__':
    unittest.main()
