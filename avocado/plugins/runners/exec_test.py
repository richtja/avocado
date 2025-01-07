import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile

import pkg_resources

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner


class ExecTestRunner(BaseRunner):
    """
    Runner for standalone executables treated as tests

    This is similar in concept to the Avocado "SIMPLE" test type, in which an
    executable returning 0 means that a test passed, and anything else means
    that a test failed.

    Runnable attributes usage:

     * uri: path to a binary to be executed as another process

     * args: arguments to be given on the command line to the
       binary given by path

     * kwargs: key=val to be set as environment variables to the
       process
    """

    name = "exec-test"
    description = "Runner for standalone executables treated as tests"

    CONFIGURATION_USED = [
        "run.keep_tmp",
        "runner.exectest.exitcodes.skip",
        "runner.exectest.clear_env",
    ]

    def _process_final_status(
        self, process, runnable, stdout=None, stderr=None
    ):  # pylint: disable=W0613
        # Since Runners are standalone, and could be executed on a remote
        # machine in an "isolated" way, there is no way to assume a default
        # value, at this moment.
        skip_codes = runnable.config.get("runner.exectest.exitcodes.skip", [])
        final_status = {}
        if skip_codes is None:
            skip_codes = []
        if process.returncode in skip_codes:
            final_status["result"] = "skip"
        elif process.returncode == 0:
            final_status["result"] = "pass"
        else:
            final_status["result"] = "fail"

        final_status["returncode"] = process.returncode
        return self.prepare_status("finished", final_status)

    def _cleanup(self, runnable):
        """Cleanup method for the exec-test tests"""
        # cleanup temporary directories
        workdir = runnable.kwargs.get("AVOCADO_TEST_WORKDIR")
        if (
            workdir is not None
            and runnable.config.get("run.keep_tmp") is not None
            and os.path.exists(workdir)
        ):
            shutil.rmtree(workdir)

    def _create_params(self, runnable):
        """Create params for the test"""
        if runnable.variant is None:
            return {}

        params = dict(
            [(str(key), str(val)) for _, key, val in runnable.variant["variant"][0][1]]
        )
        return params

    @staticmethod
    def _get_avocado_version():
        """Return the Avocado package version, if installed"""
        version = "unknown.unknown"
        try:
            version = pkg_resources.get_distribution("avocado-framework").version
        except pkg_resources.DistributionNotFound:
            pass
        return version

    def _get_env_variables(self, runnable):
        """Get the default AVOCADO_* environment variables

        These variables are available to the test environment during the test
        execution.
        """
        # create the temporary work dir
        workdir = tempfile.mkdtemp(prefix=".avocado-workdir-")
        # create the avocado environment variable dictionary
        avocado_test_env_variables = {
            "AVOCADO_VERSION": self._get_avocado_version(),
            "AVOCADO_TEST_WORKDIR": workdir,
            "AVOCADO_TEST_BASEDIR": os.path.dirname(os.path.abspath(runnable.uri)),
        }
        if runnable.output_dir:
            avocado_test_env_variables["AVOCADO_TEST_LOGDIR"] = runnable.output_dir
            avocado_test_env_variables["AVOCADO_TEST_OUTPUTDIR"] = runnable.output_dir
            avocado_test_env_variables["AVOCADO_TEST_LOGFILE"] = os.path.join(
                runnable.output_dir, "debug.log"
            )
        return avocado_test_env_variables

    @staticmethod
    def _is_uri_a_file_on_cwd(uri):
        if (
            uri is not None
            and os.path.basename(uri) == uri
            and os.access(uri, os.R_OK | os.X_OK)
        ):
            return True
        return False

    def _get_env(self, runnable):
        clear_env = runnable.config.get("runner.exectest.clear_env", None)
        if clear_env not in ["all", "system", None]:
            raise ValueError(
                f"The `runner.exectest.clear_env` value {clear_env} is not supported."
            )
        if clear_env in ["all", "system"]:
            env = {}
        else:
            env = dict(os.environ)
        if runnable.kwargs:
            env.update(runnable.kwargs)
            for key, value in runnable.kwargs.items():
                if value is None:
                    del env[key]

        # set default Avocado environment variables if running on a valid Task
        if runnable.uri is not None and clear_env != "all":
            avocado_test_env_variables = self._get_env_variables(runnable)
            # save environment variables for further cleanup
            runnable.kwargs.update(avocado_test_env_variables)
            if env is None:
                env = avocado_test_env_variables
            else:
                env.update(avocado_test_env_variables)

        params = self._create_params(runnable)
        if params:
            env.update(params)

        if env and "PATH" not in env:
            env["PATH"] = os.environ.get("PATH")

        # Support for running executable tests in the current working directory
        if self._is_uri_a_file_on_cwd(runnable.uri):
            env["PATH"] += f":{os.getcwd()}"

        return env

    def _run(self, runnable):
        if runnable.output_dir is not None:
            stdout_pipe = open(os.path.join(runnable.output_dir, "stdout"), "xb")
            stderr_pipe = open(os.path.join(runnable.output_dir, "stderr"), "xb")
        else:
            stdout_pipe = subprocess.PIPE
            stderr_pipe = subprocess.PIPE

        try:
            process = subprocess.Popen(
                [runnable.uri] + list(runnable.args),
                stdin=subprocess.DEVNULL,
                stdout=stdout_pipe,
                stderr=stderr_pipe,
                env=self._get_env(runnable),
            )
        except Exception as e:
            self._cleanup(runnable)
            raise e

        process.wait()
        if process.stdout is not None:
            stdout = process.stdout.read()
            yield self.prepare_status("running", {"type": "stdout", "log": stdout})
        else:
            stdout_path = os.path.join(runnable.output_dir, "stdout")
            with open(stdout_path, "rb") as stdout_file:
                stdout = stdout_file.read()
            yield self.prepare_status(
                "running", {"type": "stdout", "log": stdout, "log_only": True}
            )

        if process.stderr is not None:
            stderr = process.stderr.read()
            yield self.prepare_status("running", {"type": "stderr", "log": stderr})
        else:
            stderr_path = os.path.join(runnable.output_dir, "stderr")
            with open(stderr_path, "rb") as stderr_file:
                stderr = stderr_file.read()
            yield self.prepare_status(
                "running", {"type": "stderr", "log": stderr, "log_only": True}
            )

        yield self._process_final_status(process, runnable, stdout, stderr)
        self._cleanup(runnable)


class RunnerApp(BaseRunnerApp):
    PROG_NAME = "avocado-runner-exec-test"
    PROG_DESCRIPTION = "nrunner application for exec-test tests"
    RUNNABLE_KINDS_CAPABLE = ["exec-test"]


def main():
    if sys.platform == "darwin":
        multiprocessing.set_start_method("fork")
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
