#!/usr/bin/env python
#-*- coding: UTF-8 -*-

from subprocess import Popen, PIPE, STDOUT
import fileinput
import sys
import os
import time
import fcntl
from decoradores import Verbose, Timeout

READTIMEOUT = 60

class Gnokii(object):
    def __init__(self, config=None, phone=None):
        """
        Create a server interface:

        config -- path to reads configuration from instead of trying default
            locations.
        phone -- phone section name of the config file to reads parameters.
            phone=foo reads the [phone_foo] section.
        """
        self._proc = None
        self._prompt = "gnokii> "


    def is_alive(self):
        """
        Return whether the server is alive.
        """
        if self._proc is None:
            return False
        elif self._proc.poll() is None:
            return True
        else:
            return False

    
    def start(self):
        """
        Is not alive try to run the server, returns True if successful.
        """
        if not self.is_alive():
            exepath = "".join(Popen(['which', 'gnokii'], 
                stdout=PIPE).stdout.readlines()).strip()
            self._proc = Popen([exepath, '--shell'], stdin=PIPE,
                stdout=PIPE, stderr=STDOUT)

            for file in (self._proc.stdout,):
                flags = fcntl.fcntl(file, fcntl.F_GETFL)
                fcntl.fcntl(file, fcntl.F_SETFL, flags|os.O_NONBLOCK)

            self.get_result()

            return self.is_alive()
        else:
            return False

    
    def stop(self):
        """
        Is alive try to stop the server, returns True if successful.
        """
        if self.is_alive():
            self._proc.stdin.close()
            self._proc.terminate()
            self._proc.wait()
            return not self.is_alive()
        else:
            return False


    def restart(self):
        """
        Start or restart the server, returns True if successful.
        """
        if self.is_alive():
            self.stop()
        return self.start()


    def __del__(self):
        """
        Destructor method to ensure the lock is released.
        """
        return self.stop()


    def send(self, command, *args):
        """
        Sends string to the server. This is a low level tool, try yo use the 
        specific method insteat.
        """
        if self.is_alive():
            if args:
                self._proc.stdin.write("%s %s\n" % (command, " ".join(args)))
            else:
                self._proc.stdin.write("%s\n" % (command))
            return self.get_result()
        else:
            raise IOError("Server is not alive")


    @Timeout(READTIMEOUT * 2)
    def get_result(self):
        """
        Read and parse the server output.
        """
        result = ""
        lasttime = time.time()
        while (self.is_alive() and not result.endswith(self._prompt)
            and (time.time() - lasttime) < READTIMEOUT):
            try:
                result += self._proc.stdout.read()
                lasttime = time.time()
            except IOError, e:
                if e.errno != 11:
                    raise
                else:
                    time.sleep(.1)

        result = [line for line in result.splitlines()
            if not line.startswith(self._prompt)]
        return "\n".join(result)


    def help(self, section=""):
        """
        Get usage information

        section can be one of [all, monitor, sms, mms, phonebook,  calendar,
            todo, dial, profile, settings, wap, logo, ringtone, security, file,
            other]
        """
        return self.send("--help", section)


    def version(self):
        """
        Get version and copyright information.
        """
        return self.send("--version")


    def monitor(self):
        """
        Get phone status.
        """
        #FIXME: Replace this
        return self.send("--monitor", "once")


    def getspeeddial(self, location):
        """
        Reads speed dial from the specified location.
        """
        return self.send("--monitor", location)

    
    def setspeeddial(self, number, memory_type, location):
        """
        Specify speed dial. Location number 1 us usually reserved for voice
        mailbox number and it is unavailable.
        """
        return self.send("--monitor", number, memory_type, location)
    

    def dialvoice(self, number):
        """
        Initiate voice call. Returns the callid to be used with hanhup.
        """
        return self.send("--dialvoice", number)


    def senddtmf(self, string):
        """
        Send DTMF sequence.
        """
        return self.send("--senddtmf", string)


    def answercall(self, callid):
        """
        Answer an incoming call.
        """
        return self.send("--answercall", callid)


    def hangup(self, callid):
        """
        Hangup an incoming call or an already established call.
        """
        return self.send("--hangup", callid)


    def divert(self, operations="all"):
        """
        Manage call diverting/forwarding.
        """
        raise NotImplementedError("Confusing syntax")
        return self.send("--divert")


    def getdisplaystatus(self):
        """
        Show what icons are displayed.
        """
        return self.send("--getdisplaystatus")

    
    def displayoutput(self):
        """
        Show texts displayed in phone's screen.
        """
        return self.send("--displayoutput")


    def getprofile(self, number=""):
        """
        Show settings for selected(all) profile(s).
        """
        return self.send("--getprofile", number)


    def setprofile(self):
        """
        Sets settings for selected(all) profile(s).
        """
        raise NotImplementedError("Uh? No documented.")
        return self.send("--setprofile")


    def getactiveprofile(self):
        """
        Reads the active profile.
        """
        return self.send("--getactiveprofile")


    def setactiveprofile(self, profile_no):
        """
        Sets the active profile to the profile number.
        """
        return self.send("--setactiveprofile", profile_no)


    def netmonitor(self, setup=""):
        """
        Setting/querying netmonitor mode.
        reset - ???
        off - disable net monitor
        field - enable net monitor "Operator field tests"
        devel - enable net monitor "R&D field tests"
        next - show next page
        nr - show page number nr in range 1..239
        """
        return self.send("--netmonitor", setup)


    def reset(self, hard=False):
        """
        Resets the phone.
        """
        return self.send("--reset", "hard" if hard else "soft")


    def gettodo(self, start=1, end="", vcal=True):
        """
        Get the notes with numbers from start to end from  ToDo  list. "end"
        is a keyword that denotes 'everything till the end
        """
        return self.send("--gettodo", start, end, "--vCal" if vcal else "")


    def writetodo(self, vcalfile, start, end=""):
        """
        Write the notes with numbers from start to end from vCal file vcalfile
        to ToDo list. More than one note a time can be saved. "end" is a 
        keyword that denotes 'everything till the end'
        """
        return self.send("--writetodo", vcalfile, start, end)


    def deletealltodos(self):
        """
        Delete all notes from the ToDo list.
        """
        return self.send("--deletealltodos")


    def getcalendarnote(self, start, end="", vcal=True):
        """
        Get the notes with numbers from start_number to end_number from 
        calendar. "end" is a keyword that denotes 'everything till the end'.
        """
        return self.send("--getcalendarnote", start, end, "--vCal"
            if vcal else "")


    def writecalendarnote(self, vcalfile, start, end=""):
        """
        Write the notes with numbers from start to end from vCal file vcalfile
        to a phone calendar. More than one note a time can be saved. "end" is a
        keyword that denotes 'everything till the end'.
        """
        return self.send("--writecalendarnote", vcalfile, start, end)


    def deletecalendarnote(self, start, end=""):
        """
        Delete the notes with numbers from start to end from calendar. "end" is
        a keyword that denotes 'everything till the end'.
        """
        return self.send("--deletecalendarnote", start, end)


    def getsms(self, memory_type, start, end="", file="", append=True,
        delete=False):
        """
        gets SMS messages from specified memory type starting at entry start
        and ending at end.
        
        memory_type - you usually uses:
            "SM" for the SIM card
            "ME" for the phone memory
            "MT" for mixed phone and SIM memory
            
            The exception are the nk7110 and nk6510 drivers:
            "IN" for the Inbox
            "OU" for the Outbox
            "AR" for the  Archive
            "TE2 for the Templates
            "F1", "F2", ... for your own folders

            Use the showsmsfolderstatus method to get a list of memory types
            available in your phone.
        
        end  - can be a number or the string 'end'. If end is not specified
            only the location start is read.
        file - is file is used, messages are saved in file in mbox format.
        append - True by default, if False specified the file will be replaced.
        delete - if used the  message is deleted from the phone after reading.
        """

        if file:
            mode = "--append-file" if append else "--force-file"
        else:
            mode = ""

        return self.send("--deletecalendarnote", memory_type, start, end, mode,
            file, "--delete" if delete else "")


    def deletesms(self, memory_type, start, end=""):
        """
        Deletes SMS messages from specified memory type starting at entry start
        and ending at end. If end is not specified only the location start is
        deleted.
        """
        return self.send("--deletesms", memory_type, start, end)


    def sendsms(self, destination, message, smsc=None, smscno=None,
        report=False, use8bits=False, clase=None, validity=None, imelody=False,
        animation=None, concat="this", wappush=None):
        """
        Sends an SMS message to destination via smsc or SMSC number taken from
        phone memory from address smscno. If this argument is omitted SMSC 
        number is taken from phone memory from location 1.
        
        smsc - number, message center number
        smscno - number, messager center index ignored if smsc is given
        report - boolean, request for delivery report if True
        use8bit - boolean, set 8bit encoding
        clase - number, class message number, can be [0, 1, 2, 3]
        validity - minutes, validity in minutes
        imelody - boolean, send iMelody within SMS
        animation - url, send animation message
        concat - string this:total:serial, send this part of all total parts
            identified by serial
        wappush - url, send wappush to the given url
        """

        smsc = '--smsc "%s"' % smsc if smsc else ""
        smscno = '--smscno "%s"' % smscno if (smscno and not smsc) else ""
        report = '--report' is report else ""
        use8bits = '--use8bits' if use8bits else ""
        clase = '--class "%s"' % clase if clase else ""
        validity = '--validity "%s"' % validity if validity else ""
        imelody = '--imelody' if imelody else ""
        animation = '--animation "%s"' if animation else ""
        concat = '--concat "%s"' % concat
        wappush = '--wappush "%s"' % wappush if wappush else ""
        
        return self.send("--sendsms", destination, smsc, smscno, report, 
            use8bits, clase, validity, imelody, animation, concat, wappush)

    def savesms(self, sender=None, smsc=None, smscno=None, folder=None,
        location=None, sent):
        """
        Saves SMS messages to phone.

        """




def main():
    gnokii = Gnokii()
    input = fileinput.input()

    line = True
    while line:
        line = input.readline()
        if line:
            words = line.split()
            print gnokii.command(words[0], *words[1:])


if __name__ == "__main__":
    exit(main())
