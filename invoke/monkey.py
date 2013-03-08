# Fuckin' A.

import select, errno, os, sys

from subprocess import Popen as OriginalPopen, mswindows, PIPE


class Popen(OriginalPopen):
    #
    # Custom code
    #
    def __init__(self, *args, **kwargs):
        hide = kwargs.pop('hide', [])
        super(Popen, self).__init__(*args, **kwargs)
        self.hide = hide


    #
    # Copy/modified code from upstream
    #
    if mswindows:
        def _readerthread(self, fh, buffer):
            # TODO: How to determine which sys.std(out|err) to use?
            buffer.append(fh.read())
    else: # Sane operating systems
        # endtime + timeout are new for py3; we don't currently use them but
        # they must exist to be compatible.
        def _communicate(self, input, endtime, timeout):
            read_set = []
            write_set = []
            stdout = None # Return
            stderr = None # Return

            if self.stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if input:
                    write_set.append(self.stdin)
                else:
                    self.stdin.close()
            if self.stdout:
                read_set.append(self.stdout)
                stdout = []
            if self.stderr:
                read_set.append(self.stderr)
                stderr = []

            input_offset = 0
            while read_set or write_set:
                try:
                    rlist, wlist, xlist = select.select(read_set, write_set, [])
                except select.error as e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                if self.stdin in wlist:
                    # When select has indicated that the file is writable,
                    # we can write up to PIPE_BUF bytes without risk
                    # blocking.  POSIX defines PIPE_BUF >= 512
                    chunk = input[input_offset : input_offset + 512]
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                    input_offset += bytes_written
                    if input_offset >= len(input):
                        self.stdin.close()
                        write_set.remove(self.stdin)

                if self.stdout in rlist:
                    data = os.read(self.stdout.fileno(), 1)
                    if data == "":
                        self.stdout.close()
                        read_set.remove(self.stdout)
                    if 'out' not in self.hide:
                        sys.stdout.write(data)
                    stdout.append(data)

                if self.stderr in rlist:
                    data = os.read(self.stderr.fileno(), 1)
                    if data == "":
                        self.stderr.close()
                        read_set.remove(self.stderr)
                    if 'err' not in self.hide:
                        sys.stderr.write(data)
                    stderr.append(data)

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = ''.join(stdout)
            if stderr is not None:
                stderr = ''.join(stderr)

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)
