"""This is a utility class to make shell scripting easier in Python.
It combines Pexpect and wraps many Standard Python Library functions
to make them look more shell-like.

$Id: psh.py 519 2008-12-06 03:57:06Z noah $
"""

import pexpect, os, sys, re
from types import *

class ExceptionPsh(pexpect.ExceptionPexpect):

    """Raised for Psh exceptions.
    """

class ExceptionErrorCode(ExceptionPsh):

    """Raised when an program returns an error code.
    """

    def __init__(self, string, err_code, cmd_output):

        ExceptionPsh.__init__(self,string)
        self.error  = err_code
        self.output = cmd_output 

class psh (object):

    def __init__ (self,exp):

        self.exp = exp
        self.default_timeout = 30 # Seconds
    
    def ls (self, path=''):

        fileStr = self.run("ls %s" % path)
        return fileStr.split()
      
    def cd (self, path='-'):

        return self.run("cd %s" % path)
      
    def rm (self, path=''):

        return self.run("/bin/rm -f %s" % path)
      
    def cp (self, path_from='', path_to=''):

        return self.run("/bin/cp %s %s" % (path_from, path_to))

    def mv (self, path_from='', path_to=''):

        return self.run("/bin/mv %s %s" % (path_from, path_to))
      
    def pwd (self):

        return self.run("/bin/pwd")
      
    def which (self, exe_name):

        return self.run("/usr/bin/which %s" % exe_name)
                            
    def chown (self, path, user='', group=None, recurse=False):

        xtra_flags = ""
        if recurse: xtra_flags = "-R"
        if group: group = ':' + group
        else: group = ""
        
        return self.run("/bin/chmod %s %s%s %s" % (recurse,user,group,path))

    def chmod (self, path, perms='', recurse=False):

        xtra_flags = ""
        if recurse: xtra_flags = "-R"        
        return self.run("/usr/bin/chmod %s %s %s" % (xtra_flags, perms, path))
      
    def chattr (self, path, attrs='', recurse=False):

        xtra_flags = ""
        if recurse: xtra_flags = "-R"        
        return self.run("/usr/bin/chattr %s %s %s" % (xtra_flags, attrs, path))

    def cat (self, path):

        return self.run("/bin/cat %s" % path)
      
    def run (self, cmd, stim_resp_dict = {}, timeout=None):

       (ret, output) = self.run_raw(cmd, stim_resp_dict, timeout)
       if ret == 0: return output
       raise ExceptionErrorCode("Running command [%s] returned error [%d]" % (cmd,ret), ret, output)

    def run_raw(self, cmd, stim_resp_dict=None, timeout=None):

        """Someone contributed this, but now I've lost touch and I forget the motive of this.
        It was sort of a sketch at the time which doesn't make this any easier to prioritize, but
        it seemed important at the time.
        """

        if not timeout: timeout = self.default_timeout

        def cmd_exp_loop(param):
            if type(param) is DictType:
                param = (param,)
            for item in param:
                if type(item) is type(()) or type(item) is type([]):
                    cmd_exp_loop(item)
                elif type(item) is type(""):
                    self.exp.send(item)
                elif type(item) is type({}):
                    dict = item
                    while(1):
                        stimulus = dict.keys()
                        idx = self.exp.expect_exact(stimulus, timeout)
                        keys = dict.keys()
                        respond = dict[keys[idx]]
                        if type(respond) is type({}) or type(respond) is type(()) or type(item) is type([]):
                            cmd_exp_loop(respond)
                        if type(respond) is type(""):
                            self.exp.send(respond)
                        elif type(respond) is InstanceType and Exception in inspect.getmro(respond.__class__):
                            raise respond
                        elif type(respond) is type(0):
                            return (respond, self.exp.before)
                        elif respond is None:
                            break
                        else:
                            self.exp.send(str(respond))

        if stim_resp_dict == None:
            stim_resp_dict = {}

        self.exp.sendline("")
        if not self.exp.prompt(): raise SessionException("No prompt")
        self.exp.sendline(cmd)
        self.exp.expect_exact([cmd])
        stim_resp_dict[re.compile(self.exp.PROMPT)] = None
        cmd_exp_loop(stim_resp_dict)

        output = self.exp.before
        # Get the return code
        self.exp.sendline("echo $?")
        self.exp.expect_exact(["echo $?"])
        if not self.exp.prompt(): raise SessionException("No prompt", 0, self.exp.before)
        try:
            reg = re.compile("^(\d+)")
            s = self.exp.before.strip()
            #print s
            #pdb.set_trace()
            s = reg.search(s).groups()[0]
            error_code = int(s)
        except ValueError:
            log.error("Cannot parse %s into an int!" % self.exp.before)
            raise

        if not output[0:2] == '\r\n':
            log.warning("Returned output lacks leading \\r\\n which may indicate a tae error")
            log.debug2("Offending output string: [%s]" % output)
            return (error_code, output)
        else:
            return(error_code, output[2:])
  
#    def pipe (self, cmd, string_to_send):
