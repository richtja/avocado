import abc
import multiprocessing
import os
import signal
import time
import traceback

from avocado.core.exceptions import TestInterrupt
from avocado.core.nrunner.runnable import RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
from avocado.core.plugin_interfaces import RunnableRunner
from avocado.core.utils import messages
from avocado.utils import process

#: The amount of time (in seconds) between each internal status check
RUNNER_RUN_CHECK_INTERVAL = 0.01

#: The amount of time (in seconds) between a status report from a
#: runner that performs its work asynchronously
RUNNER_RUN_STATUS_INTERVAL = 0.5


def check_runnables_runner_requirements(runnables, runners_registry=None):
    """
    Checks if runnables have runner requirements fulfilled

    :param runnables: the tasks whose runner requirements will be checked
    :type runnables: list of :class:`Runnable`
    :param runners_registry: a registry with previously found (and not found)
                             runners keyed by a task's runnable kind. Defaults
                             to :attr:`RUNNERS_REGISTRY_STANDALONE_EXECUTABLE`
    :type runners_registry: dict
    :return: two list of tasks in a tuple, with the first being the tasks
             that pass the requirements check and the second the tasks that
             fail the requirements check
    :rtype: tuple of (list, list)
    """
    if runners_registry is None:
        runners_registry = RUNNERS_REGISTRY_STANDALONE_EXECUTABLE
    ok = []
    missing = []

    for runnable in runnables:
        runner = runnable.pick_runner_command(runnable.kind, runners_registry)
        if runner:
            ok.append(runnable)
        else:
            missing.append(runnable)
    return (ok, missing)


class BaseRunner(RunnableRunner):

    #: The "main Avocado" configuration keys (AKA namespaces) that
    #: this runners makes use of.
    CONFIGURATION_USED = []

    @staticmethod
    def prepare_status(status_type, additional_info=None):
        """Prepare a status dict with some basic information.

        This will add the keyword 'status' and 'time' to all status.

        :param: status_type: The type of event ('started', 'running',
                             'finished')
        :param: addional_info: Any additional information that you
                               would like to add to the dict. This must be a
                               dict.

        :rtype: dict
        """
        status = {}
        if isinstance(additional_info, dict):
            status = additional_info
        status.update({"status": status_type, "time": time.monotonic()})
        return status

    def running_loop(self, condition):
        """Produces timely running messages until end condition is found.

        :param condition: a callable that will be evaluated as a
                          condition for continuing the loop
        """
        most_current_execution_state_time = None
        while not condition():
            now = time.monotonic()
            if most_current_execution_state_time is not None:
                next_execution_state_mark = (
                    most_current_execution_state_time + RUNNER_RUN_STATUS_INTERVAL
                )
            if (
                most_current_execution_state_time is None
                or now > next_execution_state_mark
            ):
                most_current_execution_state_time = now
                yield self.prepare_status("running")
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)


class PythonBaseRunner(BaseRunner, abc.ABC):
    """
    Base class for Python runners
    """

    def __init__(self):
        super().__init__()
        self.proc = None
        self.process_stopped = False
        self.stop_signal = False

    def signal_handler(self, signum, frame):  # pylint: disable=W0613
        if signum == signal.SIGTERM.value:
            raise TestInterrupt("Test interrupted: Timeout reached")
        elif signum == signal.SIGTSTP.value:
            self.stop_signal = True

    def pause_process(self):
        if self.process_stopped:
            self.process_stopped = False
            sign = signal.SIGCONT
        else:
            self.process_stopped = True
            sign = signal.SIGSTOP
        processes = process.get_children_pids(self.proc.pid, recursive=True)
        processes.append(self.proc.pid)
        for pid in processes:
            os.kill(pid, sign)

    def _monitor(self, queue):
        most_recent_status_time = None
        while True:
            time.sleep(RUNNER_RUN_CHECK_INTERVAL)
            if self.stop_signal:
                self.stop_signal = False
                self.pause_process()
            if queue.empty():
                now = time.monotonic()
                if (
                    most_recent_status_time is None
                    or now >= most_recent_status_time + RUNNER_RUN_STATUS_INTERVAL
                ):
                    most_recent_status_time = now
                    yield messages.RunningMessage.get()
                continue
            else:
                message = queue.get()
                if message.get("type") != "early_state":
                    yield message
                if message.get("status") == "finished":
                    break

    def run(self, runnable):
        if hasattr(signal, "SIGTSTP"):
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)
            signal.signal(signal.SIGTSTP, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # pylint: disable=W0201
        self.runnable = runnable
        yield messages.StartedMessage.get()
        try:
            queue = multiprocessing.SimpleQueue()
            self.proc = multiprocessing.Process(
                target=self._run, args=(self.runnable, queue)
            )
            self.proc.start()
            for message in self._monitor(queue):
                yield message

        except TestInterrupt:
            self.proc.terminate()
            for message in self._monitor(queue):
                yield message
        except Exception as e:
            yield messages.StderrMessage.get(traceback.format_exc())
            yield messages.FinishedMessage.get(
                "error",
                fail_reason=str(e),
                fail_class=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )

    @abc.abstractmethod
    def _run(self, runnable, queue):
        """
        Run the test

        :param runnable: the runnable object
        :type runnable: :class:`Runnable`
        :param queue: the queue to put messages
        :type queue: :class:`multiprocessing.SimpleQueue`
        """
