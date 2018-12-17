# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Functions dedicated to find and run external commands.
"""

import logging
import os
import select
import shlex
import signal
import time
import threading

try:
    import subprocess32 as subprocess
    SUBPROCESS32_SUPPORT = True
except ImportError:
    import subprocess
    SUBPROCESS32_SUPPORT = False

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


log = logging.getLogger('process')
stdout_log = logging.getLogger('process.stdout')
stderr_log = logging.getLogger('process.stderr')


class CmdNotFoundError(Exception):

    """
    Indicates that the command was not found in the system after a search.

    :param cmd: String with the command.
    :param paths: List of paths where we looked after.
    """

    def __init__(self, cmd, paths):
        super(CmdNotFoundError, self)
        self.cmd = cmd
        self.paths = paths

    def __str__(self):
        return ("Command '%s' could not be found in any of the PATH dirs: %s" %
                (self.cmd, self.paths))


def find_command(cmd, default=None):
    """
    Try to find a command in the PATH, paranoid version.

    :param cmd: Command to be found.
    :param default: Command path to use as a fallback if not found
                    in the standard directories.
    :raise: :class:`avocado.utils.path.CmdNotFoundError` in case the
            command was not found and no default was given.
    """
    common_bin_paths = ["/usr/libexec", "/usr/local/sbin", "/usr/local/bin",
                        "/usr/sbin", "/usr/bin", "/sbin", "/bin"]
    try:
        path_paths = os.environ['PATH'].split(":")
    except IndexError:
        path_paths = []
    path_paths = list(set(common_bin_paths + path_paths))

    for dir_path in path_paths:
        cmd_path = os.path.join(dir_path, cmd)
        if os.path.isfile(cmd_path):
            return os.path.abspath(cmd_path)

    if default is not None:
        return default
    else:
        raise CmdNotFoundError(cmd, path_paths)


class CmdError(Exception):

    def __init__(self, command=None, result=None, additional_text=None):
        self.command = command
        self.result = result
        self.additional_text = additional_text

    def __str__(self):
        if self.result is not None:
            if self.result.interrupted:
                msg = "Command '%s' interrupted by %s"
                msg %= (self.command, self.result.interrupted)
            elif self.result.exit_status is None:
                msg = "Command '%s' failed and is not responding to signals"
                msg %= self.command
            else:
                msg = "Command '%s' failed (rc=%d)"
                msg %= (self.command, self.result.exit_status)
            if self.additional_text:
                msg += ", " + self.additional_text
            return msg
        else:
            return "CmdError"


class CmdResult(object):

    """
    Command execution result.

    :param command: String containing the command line itself
    :param exit_status: Integer exit code of the process
    :param stdout: String containing stdout of the process
    :param stderr: String containing stderr of the process
    :param duration: Elapsed wall clock time running the process
    :param pid: ID of the process
    """

    def __init__(self, command="", stdout="", stderr="",
                 exit_status=None, duration=0, pid=None):
        self.command = command
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.interrupted = False
        self.pid = pid

    def __repr__(self):
        cmd_rep = ("Command: %s\n"
                   "Exit status: %s\n"
                   "Duration: %s\n"
                   "Stdout:\n%s\n"
                   "Stderr:\n%s\n"
                   "PID:\n%s\n" % (self.command, self.exit_status,
                                   self.duration, self.stdout, self.stderr,
                                   self.pid))
        if self.interrupted:
            cmd_rep += "Command interrupted by %s\n" % self.interrupted
        return cmd_rep


class SubProcess(object):

    """
    Run a subprocess in the background, collecting stdout/stderr streams.
    """

    def __init__(self, cmd, verbose=True, allow_output_check='all',
                 shell=False, env=None, sudo=False,
                 ignore_bg_processes=False):
        """
        Creates the subprocess object, stdout/err, reader threads and locks.

        :param cmd: Command line to run.
        :type cmd: str
        :param verbose: Whether to log the command run and stdout/stderr.
        :type verbose: bool
        :param allow_output_check: Whether to log the command stream outputs
                                   (stdout and stderr) in the test stream
                                   files. Valid values: 'stdout', for
                                   allowing only standard output, 'stderr',
                                   to allow only standard error, 'all',
                                   to allow both standard output and error
                                   (default), and 'none', to allow
                                   none to be recorded.
        :type allow_output_check: str
        :param shell: Whether to run the subprocess in a subshell.
        :type shell: bool
        :param env: Use extra environment variables.
        :type env: dict
        :param sudo: Whether the command requires admin privileges to run,
                     so that sudo will be prepended to the command.
                     The assumption here is that the user running the command
                     has a sudo configuration such that a password won't be
                     prompted. If that's not the case, the command will
                     straight out fail.
        :param ignore_bg_processes: When True the process does not wait for
                    child processes which keep opened stdout/stderr streams
                    after the main process finishes (eg. forked daemon which
                    did not closed the stdout/stderr). Note this might result
                    in missing output produced by those daemons after the
                    main thread finishes and also it allows those daemons
                    to be running after the process finishes.
        """
        # Now assemble the final command considering the need for sudo
        self.cmd = self._prepend_sudo(cmd, sudo, shell)
        self.verbose = verbose
        self.allow_output_check = allow_output_check
        self.result = CmdResult(self.cmd)
        self.shell = shell
        if env:
            self.env = os.environ.copy()
            self.env.update(env)
        else:
            self.env = None
        self._popen = None
        self._ignore_bg_processes = ignore_bg_processes

    def __repr__(self):
        if self._popen is None:
            rc = '(not started)'
        elif self.result.exit_status is None:
            rc = '(running)'
        else:
            rc = self.result.exit_status
        return '%s(cmd=%r, rc=%r)' % (self.__class__.__name__, self.cmd, rc)

    def __str__(self):
        if self._popen is None:
            rc = '(not started)'
        elif self.result.exit_status is None:
            rc = '(running)'
        else:
            rc = '(finished with exit status=%d)' % self.result.exit_status
        return '%s %s' % (self.cmd, rc)

    @staticmethod
    def _prepend_sudo(cmd, sudo, shell):
        if sudo and os.getuid() != 0:
            try:
                sudo_cmd = '%s -n' % find_command('sudo')
            except CmdNotFoundError as details:
                log.error(details)
                log.error('Parameter sudo=True provided, but sudo was '
                          'not found. Please consider adding sudo to '
                          'your OS image')
                return cmd
            if shell:
                if ' -s' not in sudo_cmd:
                    sudo_cmd = '%s -s' % sudo_cmd
            cmd = '%s %s' % (sudo_cmd, cmd)
        return cmd

    def _init_subprocess(self):
        if self._popen is None:
            if self.verbose:
                log.info("Running '%s'", self.cmd)
            if self.shell is False:
                cmd = shlex.split(self.cmd)
            else:
                cmd = self.cmd
            try:
                self._popen = subprocess.Popen(cmd,
                                               stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE,
                                               shell=self.shell,
                                               env=self.env)
            except OSError as details:
                details.strerror += " (%s)" % self.cmd
                raise details

            self.start_time = time.time()
            self.stdout_file = StringIO()
            self.stderr_file = StringIO()
            self.stdout_lock = threading.Lock()
            ignore_bg_processes = self._ignore_bg_processes
            self.stdout_thread = threading.Thread(target=self._fd_drainer,
                                                  name="%s-stdout" % self.cmd,
                                                  args=[self._popen.stdout,
                                                        ignore_bg_processes])
            self.stdout_thread.daemon = True
            self.stderr_lock = threading.Lock()
            self.stderr_thread = threading.Thread(target=self._fd_drainer,
                                                  name="%s-stderr" % self.cmd,
                                                  args=[self._popen.stderr,
                                                        ignore_bg_processes])
            self.stderr_thread.daemon = True
            self.stdout_thread.start()
            self.stderr_thread.start()

            def signal_handler(signum, frame):
                self.result.interrupted = "signal/ctrl+c"
                self.wait()
                signal.default_int_handler()
            try:
                signal.signal(signal.SIGINT, signal_handler)
            except ValueError:
                if self.verbose:
                    log.info("Command %s running on a thread", self.cmd)

    def _fd_drainer(self, input_pipe, ignore_bg_processes=False):
        """
        Read from input_pipe, storing and logging output.

        :param input_pipe: File like object to the stream.
        """
        stream_prefix = "%s"
        if input_pipe == self._popen.stdout:
            prefix = '[stdout] %s'
            if self.allow_output_check in ['none', 'stderr']:
                stream_logger = None
            else:
                stream_logger = stdout_log
            output_file = self.stdout_file
            lock = self.stdout_lock
        elif input_pipe == self._popen.stderr:
            prefix = '[stderr] %s'
            if self.allow_output_check in ['none', 'stdout']:
                stream_logger = None
            else:
                stream_logger = stderr_log
            output_file = self.stderr_file
            lock = self.stderr_lock

        fileno = input_pipe.fileno()

        bfr = ''
        while True:
            if ignore_bg_processes:
                # Exit if there are no new data and the main process finished
                if (not select.select([fileno], [], [], 1)[0] and
                        self.result.exit_status is not None):
                    break
                # Don't read unless there are new data available:
                if not select.select([fileno], [], [], 1)[0]:
                    continue
            tmp = os.read(fileno, 8192).decode()
            if tmp == '':
                break
            lock.acquire()
            try:
                output_file.write(tmp)
                if self.verbose:
                    bfr += tmp
                    if tmp.endswith('\n'):
                        for line in bfr.splitlines():
                            log.debug(prefix, line)
                            if stream_logger is not None:
                                stream_logger.debug(stream_prefix, line)
                        bfr = ''
            finally:
                lock.release()
        # Write the rest of the bfr unfinished by \n
        if self.verbose and bfr:
            for line in bfr.splitlines():
                log.debug(prefix, line)
                if stream_logger is not None:
                    stream_logger.debug(stream_prefix, line)

    def _fill_results(self, rc):
        self._init_subprocess()
        self.result.exit_status = rc
        if self.result.duration == 0:
            self.result.duration = time.time() - self.start_time
        if self.verbose:
            log.info("Command '%s' finished with %s after %ss", self.cmd, rc,
                     self.result.duration)
        self.result.pid = self._popen.pid
        self._fill_streams()

    def _fill_streams(self):
        """
        Close subprocess stdout and stderr, and put values into result obj.
        """
        # Cleaning up threads
        self.stdout_thread.join()
        self.stderr_thread.join()
        # Clean subprocess pipes and populate stdout/err
        self._popen.stdout.close()
        self._popen.stderr.close()
        self.result.stdout = self.get_stdout()
        self.result.stderr = self.get_stderr()

    def start(self):
        """
        Start running the subprocess.

        This method is particularly useful for background processes, since
        you can start the subprocess and not block your test flow.

        :return: Subprocess PID.
        :rtype: int
        """
        self._init_subprocess()
        return self._popen.pid

    def get_stdout(self):
        """
        Get the full stdout of the subprocess so far.

        :return: Standard output of the process.
        :rtype: str
        """
        self._init_subprocess()
        self.stdout_lock.acquire()
        stdout = self.stdout_file.getvalue()
        self.stdout_lock.release()
        return stdout

    def get_stderr(self):
        """
        Get the full stderr of the subprocess so far.

        :return: Standard error of the process.
        :rtype: str
        """
        self._init_subprocess()
        self.stderr_lock.acquire()
        stderr = self.stderr_file.getvalue()
        self.stderr_lock.release()
        return stderr

    def terminate(self):
        """
        Send a :attr:`signal.SIGTERM` to the process.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGTERM)

    def kill(self):
        """
        Send a :attr:`signal.SIGKILL` to the process.
        """
        self._init_subprocess()
        self.send_signal(signal.SIGKILL)

    def send_signal(self, sig):
        """
        Send the specified signal to the process.

        :param sig: Signal to send.
        """
        self._init_subprocess()
        self._popen.send_signal(sig)

    def poll(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        self._init_subprocess()
        rc = self._popen.poll()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def wait(self):
        """
        Call the subprocess poll() method, fill results if rc is not None.
        """
        self._init_subprocess()
        rc = self._popen.wait()
        if rc is not None:
            self._fill_results(rc)
        return rc

    def stop(self):
        """
        Stop background subprocess.

        Call this method to terminate the background subprocess and
        wait for it results.
        """
        self._init_subprocess()
        if self.result.exit_status is None:
            self.terminate()
        return self.wait()

    def get_pid(self):
        """
        Reports PID of this process
        """
        self._init_subprocess()
        return self._popen.pid

    def run(self, timeout=None, sig=signal.SIGTERM):
        """
        Start a process and wait for it to end, returning the result attr.

        If the process was already started using .start(), this will simply
        wait for it to end.

        :param timeout: Time (seconds) we'll wait until the process is
                        finished. If it's not, we'll try to terminate it
                        and get a status.
        :type timeout: float
        :param sig: Signal to send to the process in case it did not end after
                    the specified timeout.
        :type sig: int
        :returns: The command result object.
        :rtype: A :class:`CmdResult` instance.
        """
        def timeout_handler():
            self.send_signal(sig)
            self.result.interrupted = "timeout after %ss" % timeout

        self._init_subprocess()

        if timeout is None:
            self.wait()
        elif timeout > 0.0:
            timer = threading.Timer(timeout, timeout_handler)
            try:
                timer.start()
                self.wait()
            finally:
                timer.cancel()

        if self.result.exit_status is None:
            stop_time = time.time() + 1
            while time.time() < stop_time:
                self.poll()
                if self.result.exit_status is not None:
                    break
            else:
                self.kill()
                self.poll()

        # If all this work fails, we're dealing with a zombie process.
        e_msg = 'Zombie Process %s' % self._popen.pid
        assert self.result.exit_status is not None, e_msg

        self.result.stdout = self.result.stdout.rstrip('\n\r')
        return self.result


def run(cmd, timeout=None, verbose=True, ignore_status=False,
        allow_output_check='all', shell=False, env=None, sudo=False,
        ignore_bg_processes=False):
    """
    Run a subprocess, returning a CmdResult object.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :type ignore_status: bool
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.

    :return: An :class:`CmdResult` object.
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    #klass = get_sub_process_klass(cmd)
    sp = SubProcess(cmd=cmd, verbose=verbose,
                    allow_output_check=allow_output_check, shell=shell,
                    env=env, sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    cmd_result = sp.run(timeout=timeout)
    fail_condition = cmd_result.exit_status != 0 or cmd_result.interrupted
    if fail_condition and not ignore_status:
        raise CmdError(cmd, sp.result)
    return cmd_result


def system(cmd, timeout=None, verbose=True, ignore_status=False,
           allow_output_check='all', shell=False, env=None, sudo=False,
           ignore_bg_processes=False):
    """
    Run a subprocess, returning its exit code.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :type ignore_status: bool
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables.
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.

    :return: Exit code.
    :rtype: int
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check, shell=shell, env=env,
                     sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    return cmd_result.exit_status


def system_output(cmd, timeout=None, verbose=True, ignore_status=False,
                  allow_output_check='all', shell=False, env=None, sudo=False,
                  ignore_bg_processes=False, strip_trail_nl=True):
    """
    Run a subprocess, returning its output.

    :param cmd: Command line to run.
    :type cmd: str
    :param timeout: Time limit in seconds before attempting to kill the
                    running process. This function will take a few seconds
                    longer than 'timeout' to complete if it has to kill the
                    process.
    :type timeout: float
    :param verbose: Whether to log the command run and stdout/stderr.
    :type verbose: bool
    :param ignore_status: Whether to raise an exception when command returns
                          =! 0 (False), or not (True).
    :param allow_output_check: Whether to log the command stream outputs
                               (stdout and stderr) in the test stream
                               files. Valid values: 'stdout', for
                               allowing only standard output, 'stderr',
                               to allow only standard error, 'all',
                               to allow both standard output and error
                               (default), and 'none', to allow
                               none to be recorded.
    :type allow_output_check: str
    :param shell: Whether to run the command on a subshell
    :type shell: bool
    :param env: Use extra environment variables
    :type env: dict
    :param sudo: Whether the command requires admin privileges to run,
                 so that sudo will be prepended to the command.
                 The assumption here is that the user running the command
                 has a sudo configuration such that a password won't be
                 prompted. If that's not the case, the command will
                 straight out fail.
    :type sudo: bool
    :param ignore_bg_processes: Whether to ignore background processes
    :type ignore_bg_processes: bool
    :param strip_trail_nl: Whether to strip the trailing newline
    :type strip_trail_nl: bool

    :return: Command output.
    :rtype: str
    :raise: :class:`CmdError`, if ``ignore_status=False``.
    """
    cmd_result = run(cmd=cmd, timeout=timeout, verbose=verbose, ignore_status=ignore_status,
                     allow_output_check=allow_output_check, shell=shell, env=env,
                     sudo=sudo, ignore_bg_processes=ignore_bg_processes)
    if strip_trail_nl:
        return cmd_result.stdout.rstrip('\n\r')
    return cmd_result.stdout
