import logging
import os
import shutil
import subprocess

DEVNULL = open(os.devnull, 'wb')


class ShellError(Exception):
    def __init__(self, command, err_no, message=None):
        self.command = command
        self.errno = err_no
        self.message = message

    def __str__(self):
        string = "Command '%s' failed with exit code %d" % (self.command, self.errno)
        if self.message is not None:
            string += ': ' + repr(self.message)
        return string

    def __repr__(self):
        return self.__str__()


def shell_exec(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, background=False, env=None):
    str_cmd = cmd if isinstance(cmd, str) else ' '.join(cmd)
    logging.getLogger('shell_exec').debug(str_cmd)

    message = None
    if background:
        if stdout == subprocess.PIPE:
            stdout = DEVNULL
        if stderr == subprocess.PIPE:
            stderr = DEVNULL
    elif stdin is not None and isinstance(stdin, str):
        message = stdin
        stdin = subprocess.PIPE

    process = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr, shell=isinstance(cmd, str), env=env)

    stdout_dump = None
    stderr_dump = None
    return_code = 0

    if message is not None or stdout == subprocess.PIPE or stderr == subprocess.PIPE:
        stdout_dump, stderr_dump = process.communicate(message)
        return_code = process.returncode
    elif not background:
        return_code = process.wait()

    if background:
        return process
    else:
        if stdout_dump is not None:
            stdout_dump = stdout_dump.decode('utf-8')
        if stderr_dump is not None:
            stderr_dump = stderr_dump.decode('utf-8')

        if return_code != 0:
            raise ShellError(str_cmd, return_code, stderr_dump)
        else:
            return stdout_dump, stderr_dump


def mem_size(megabytes=True):
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    return mem_bytes / (1024. ** 2) if megabytes else mem_bytes


def lc(filename):
    with open(filename) as stream:
        count = 0
        for _ in stream:
            count += 1

        return count


def cat(files, output, buffer_size=10 * 1024 * 1024):
    with open(output, 'wb') as blob:
        for f in files:
            with open(f, 'rb') as source:
                shutil.copyfileobj(source, blob, buffer_size)
