Introduction
============

Avocado Hello World
-------------------

You should first experience Avocado by using the test runner, that is, the
command line tool that will conveniently run your tests and collect their
results.

To do so, please run ``avocado`` with the ``run`` sub-command followed by a
test reference, which could be either a path to the file, or a recognizable
name

.. literalinclude:: ../../../scripts/hello_world.txt


You probably noticed that we used ``/bin/true`` as a test, and in accordance
with our expectations, it passed! These are known as `simple tests`, but there
is also another type of test, which we call `instrumented tests`. See more at
`test-types` or just keep reading.


Running a job with multiple tests
---------------------------------

You can run any number of test in an arbitrary order, as well as mix and match
instrumented and simple tests

.. literalinclude:: ../../../scripts/multiple_tests.txt

.. note:: Although in most cases running ``avocado run $test1 $test3 ...`` is
          fine, it can lead to argument vs. test name clashes. The safest
          way to execute tests is ``avocado run --$argument1 --$argument2
          -- $test1 $test2``. Everything after `--` will be considered
          positional arguments, therefore test names (in case of
          ``avocado run``)


Using a different runner
------------------------

Currently Avocado has two test runners: ``nrunner`` (the new runner) and
``runner`` (legacy).  You can find a list of current runners installed with the
``avocado plugins`` command::

  $ avocado plugins
  Plugins that run test suites on a job (runners):
  nrunner nrunner based implementation of job compliant runner
  runner  The conventional test runner

During the test execution, you can select the runner using the option
``--test-runner``, where the default is the legacy one::

  $ avocado run --test-runner='nrunner' /bin/true


Interrupting tests
------------------

.. _signal_hanlders:

Sending Signals
~~~~~~~~~~~~~~~

To interrupt a job execution a user can press ``ctrl+c`` which after a single
press sends SIGTERM to the main test's process and waits for it to finish.  If
this does not help user can press ``ctrl+c`` again (after 2s grace period)
which destroys the test's process ungracefully and safely finishes the job
execution always providing the test results.

To pause the test execution a user can use ``ctrl+z`` which sends ``SIGSTOP``
to all processes inherited from the test's PID. We do our best to stop all
processes, but the operation is not atomic and some new processes might not be
stopped. Another ``ctrl+z`` sends ``SIGCONT`` to all processes inherited by the
test's PID resuming the execution. Note the test execution time (concerning the
test timeout) are still running while the test's process is stopped.

Interrupting the job on first fail (failfast)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Avocado ``run`` command has the option ``--failfast`` to exit the job on
first failed test

.. literalinclude:: ../../../scripts/failfast.txt

The default behavior, that is, when ``--failfast`` is **not** set, is
to try to execute all tests in a job, regardless individual of test failures.

.. note:: Avocado versions 80.0 and earlier allowed replayed jobs to override
          the failfast configuration by setting ``--failfast=off`` in a
          ``avocado replay ..`` command line.  This is no longer possible.

.. _the_hint_files:

The hint files
--------------

Avocado team has added support to the "hint files". This feature is present
since Avocado #78 and is a configuration file that you can add to your project
root folder to help Avocado on the "test resolution" phase.

The idea is that, you know more about your tests than anybody else. And you can
specify where your tests are, and what type (kind) they are. You just have to
add a `.avocado.hint` in your root folder with the section`[kinds]` and one
section for each kind that you are using.

On the specific test type section, you can specify 3 options: `uri`, `args` and
`kwargs`.

.. note:: Some test types will convert kwargs into variable environments.
 Please check the documentation of the test type that you are using.

You can also use the keyworkd `$testpath` in any of the options inside the test
type section. Avocado will replace `$testpath` with your test path, after the
expansion.

For instance, bellow you will find a hint file example where we have only one
test type: `tap`:

.. literalinclude:: ../../../../../examples/hint-files/.avocado.hint.example

Let's suppose that you have 2 tests that matches `./tests/unit/*.sh`:

* ./tests/unit/foo.sh
* ./tests/unit/bar.sh

Avocado will run each one as a `TAP` test, as you desired.

Ignoring missing test references
--------------------------------

When you provide a list of test references, Avocado will try to resolve all of
them to tests. If one or more test references can not be resolved to tests, the
Job will not be created. Example::

    $ avocado run passtest.py badtest.py
    Unable to resolve reference(s) 'badtest.py' with plugins(s) 'file', 'robot', 'external', try running 'avocado -V list badtest.py' to see the details.

But if you want to execute the Job anyway, with the tests that could be
resolved, you can use ``--ignore-missing-references``, a boolean command-line
option. The same message will appear in the UI, but the Job will be executed

.. literalinclude:: ../../../scripts/ignore_missing_references.txt

.. _running-external-runner:

Running tests with an external runner
-------------------------------------

It's quite common to have organically grown test suites in most
software projects. These usually include a custom built, very specific
test runner that knows how to find and run their own tests.

Still, running those tests inside Avocado may be a good idea for
various reasons, including being able to have results in different
human and machine readable formats, collecting system information
alongside those tests (the Avocado's `sysinfo` functionality), and
more.

Avocado makes that possible by means of its "external runner" feature. The
most basic way of using it is::

    $ avocado run --external-runner=/path/to/external_runner foo bar baz

In this example, Avocado will report individual test results for tests
`foo`, `bar` and `baz`. The actual results will be based on the return
code of individual executions of `/path/to/external_runner foo`,
`/path/to/external_runner bar` and finally `/path/to/external_runner baz`.

As another way to explain an show how this feature works, think of the
"external runner" as some kind of interpreter and the individual tests as
anything that this interpreter recognizes and is able to execute. A
UNIX shell, say `/bin/sh` could be considered an external runner, and
files with shell code could be considered tests

.. literalinclude:: ../../../scripts/external_runner.txt

This example is pretty obvious, and could be achieved by giving
`/tmp/pass` and `/tmp/fail` shell "shebangs" (`#!/bin/sh`), making
them executable (`chmod +x /tmp/pass /tmp/fail)`, and running them as
"SIMPLE" tests.

But now consider the following example

.. literalinclude:: ../../../scripts/external_runner_google.txt

This effectively makes `/bin/curl` an "external test runner", responsible for
trying to fetch those URLs, and reporting PASS or FAIL for each of them.

.. warning:: The external runner is incompatible with loaders from
   :ref:`test-loaders`. If you use external runner and loader together
   the job will use the external runner and ignore the loader.

Runner outputs
--------------

A test runner must provide an assortment of ways to clearly communicate results
to interested parties, be them humans or machines.

.. note:: There are several optional result plugins, you can find them in
   :ref:`result-plugins`.

Results for human beings
~~~~~~~~~~~~~~~~~~~~~~~~

Avocado has two different result formats that are intended for human beings:

* Its default UI, which shows the live test execution results on a command
  line, text based, UI.
* The HTML report, which is generated after the test job finishes running.

.. note:: The HTML report needs the ``html`` plugin enabled that is an optional
  plugin.

A regular run of Avocado will present the test results in a live fashion, that
is, the job and its test(s) results are constantly updated

.. literalinclude:: ../../../scripts/runner_output.txt

The most important thing is to remember that programs should never need to
parse human output to figure out what happened to a test job run.

As you can see, Avocado will print a nice UI with the job summary on the
console. If you would like to inspect a detailed output of your tests, you can
visit the folder: ``$HOME/avocado/job-results/latest/`` or a specific job
folder.

Results for machine
~~~~~~~~~~~~~~~~~~~

Another type of results are those intended to be parsed by other applications.
Several standards exist in the test community, and Avocado can in theory
support pretty much every result standard out there.

Out of the box, Avocado supports a couple of machine readable results. They are
always generated and stored in the results directory in `results.$type` files,
but you can ask for a different location too.

Currently, you can find three different formats available on this folder:
**xUnit (XML)**, **JSON** and **TAP**:

 **1. xUnit:**

The default machine readable output in Avocado is `xunit
<http://help.catchsoftware.com/display/ET/JUnit+Format>`__.

xUnit is an XML format that contains test results in a structured form, and are
used by other test automation projects, such as `jenkins
<http://jenkins-ci.org/>`__. If you want to make Avocado to generate xunit
output in the standard output of the runner, simply use

.. literalinclude:: ../../../scripts/runner_output_xunit.txt


.. note:: The dash `-` in the option `--xunit`, it means that the xunit result
          should go to the standard output.

.. note:: In case your tests produce very long outputs, you can limit the
          number of embedded characters by
          `--xunit-max-test-log-chars`. If the output in the log file is
          longer it only attaches up-to max-test-log-chars characters
          one half starting from the beginning of the content, the other
          half from the end of the content.


**2. JSON:**

`JSON <http://www.json.org/>`__ is a widely used data exchange format. The JSON
Avocado plugin outputs job information, similarly to the xunit output plugin

.. literalinclude:: ../../../scripts/runner_output_json.txt

.. note:: The dash `-` in the option `--json`, it means that the xunit result
          should go to the standard output.

Bear in mind that there's no documented standard for the Avocado JSON result
format. This means that it will probably grow organically to accommodate newer
Avocado features. A reasonable effort will be made to not break backwards
compatibility with applications that parse the current form of its JSON result.


 **3. TAP:**

Provides the basic `TAP <http://testanything.org/>`__ (Test Anything Protocol)
results, currently in v12. Unlike most existing Avocado machine readable
outputs this one is streamlined (per test results)

.. literalinclude:: ../../../scripts/runner_output_tap.txt


Using the option --show
~~~~~~~~~~~~~~~~~~~~~~~

Probably, you frequently want to look straight at the job log, without
switching screens or having to "tail" the job log.

In order to do that, you can use ``avocado --show=test run ...``::

    $ avocado --show=test run examples/tests/sleeptest.py
    ...
    Job ID: f9ea1742134e5352dec82335af584d1f151d4b85

    START 1-sleeptest.py:SleepTest.test

    PARAMS (key=timeout, path=*, default=None) => None
    PARAMS (key=sleep_length, path=*, default=1) => 1
    Sleeping for 1.00 seconds
    PASS 1-sleeptest.py:SleepTest.test

    Test results available in $HOME/avocado/job-results/job-2015-06-02T10.45-f9ea174

As you can see, the UI output is suppressed and only the job log is shown,
making this a useful feature for test development and debugging.

It's possible to silence all output to stdout (while keeping the error messages
being printed to stderr). One can then use the return code to learn about the
result::

    $ avocado --show=none run failtest.py
    $ echo $?
    1

In practice, this would usually be used by scripts that will in turn run
Avocado and check its results::

    #!/bin/bash
    ...
    $ avocado --show=none run /path/to/my/test.py
    if [ $? == 0 ]; then
       echo "great success!"
    elif
       ...

more details regarding exit codes in `Exit Codes` section.

Multiple results at once
~~~~~~~~~~~~~~~~~~~~~~~~

You can have multiple results formats at once, as long as only one of them uses
the standard output. For example, it is fine to use the xunit result on stdout
and the JSON result to output to a file

   .. literalinclude:: ../../../scripts/runner_output_multiple.txt

But you won't be able to do the same without the --json flag passed to
the program::

   $ avocado run sleeptest.py synctest.py --xunit - --json -
   avocado run: error: argument --json: Options --xunit --json are trying to
   use stdout simultaneously. Please set at least one of them to a file to
   avoid conflicts

That's basically the only rule, and a sane one, that you need to follow.

.. note:: Avocado support "paginator" option, which, on compatible
  terminals, basically pipes the colored output to `less` to simplify
  browsing of the produced output. One can disable it by `--paginator
  {on|off}`.

Running simple tests with arguments
-----------------------------------

This used to be supported out of the box by running ``avocado run "test arg1
arg2"`` but it was quite confusing and removed.  It is still possible to
achieve that by using shell and one can even combine normal tests and the
parametrized ones::

    $ avocado run --loaders file external:/bin/sh -- existing_file.py existing-file nonexisting-file

This will run 3 tests, the first one is a normal test defined by
``existing_file.py`` (most probably an instrumented test) and will be executed
by the "file" loader.  Then we have two script files which are going to be
executed with ``/bin/sh``.

Sysinfo collection
------------------

Avocado comes with a ``sysinfo`` plugin, which automatically gathers some
system information per each job or even between tests. This is very useful
when later we want to know what caused the test's failure. This system
is configurable but we provide a sane set of defaults for you.

In the default Avocado configuration (``/etc/avocado/avocado.conf``) there
is a section ``sysinfo.collect`` where you can enable/disable the sysinfo
collection as well as configure the basic environment. In
``sysinfo.collectibles`` section you can define basic paths of where
to look for what commands/tasks should be performed before/during
the sysinfo collection. Avocado supports three types of tasks:

1. commands - file with new-line separated list of commands to be executed
   before and after the job/test (single execution commands). It is possible
   to set a timeout which is enforced per each executed command in
   [sysinfo.collect] by setting "commands_timeout" to a positive number.
   You can also use the environment variable AVOCADO_SYSINFODIR which points
   to the sysinfo directory in results.
2. fail_commands - similar to commands, but gets executed only when the test
   fails.
3. files - file with new-line separated list of files to be copied.
4. fail_files - similar to files, but copied only when the test fails.
5. profilers - file with new-line separated list of commands to be executed
   before the job/test and killed at the end of the job/test (follow-like
   commands).

Additionally this plugin tries to follow the system log via ``journalctl``
if available.

By default these are collected per-job but you can also run them per-test by
setting ``per_test = True`` in the ``sysinfo.collect`` section.

The sysinfo is enabled by default and can also be disabled on the cmdline if
needed by ``--disable-sysinfo``.

After the job execution you can find the collected information in
``$RESULTS/sysinfo`` of ``$RESULTS/test-results/$TEST/sysinfo``. They
are categorized into ``pre``, ``post`` and ``profile`` folders and
the filenames are safely-escaped executed commands or file-names.
You can also see the sysinfo in html results when you have html
results plugin enabled.

It is also possible to save only the files / commands which were changed
during the course of the test, in the ``post`` directory, using the setting
``optimize = True`` in the ``sysinfo.collect`` section. This collects all
sysinfo on ``pre``, but saves only changed ones on ``post``. It is set to
False by default.

.. warning:: If you are using Avocado from sources, you need to manually place
   the ``commands``/``fail_commands``/``fail_files``/``files``/``profilers``
   into the ``/etc/avocado/sysinfo`` directories or adjust the paths in
   ``$AVOCADO_SRC/etc/avocado/avocado.conf``.
