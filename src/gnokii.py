#!/usr/bin/env python
#-*- coding: UTF-8 -*-

from decoradores import Verbose, Timeout, debug
from subprocess import Popen, PIPE, STDOUT
from tempfile import mkstemp, mktemp
import fcntl
import fileinput
import os
import re
import sys
import time

READTIMEOUT = 5
RESULT_RE = r'(?ms)^.*?$\n(.*)^gnokii>\s*'

"""
    Why use this module instead of smsd (http://wiki.gnokii.org/index.php/SMSD)?
        - SMSD is bogus
        - Has not multi-phone features
"""


class Gnokii(object):
    def __init__(self, config=None, phone=None):
        """
        Create a server interface:

        :config: path to reads configuration from instead of trying default
            locations.
        :phone: phone section name of the config file to reads parameters.
            phone=foo reads the [phone_foo] section.
        """

        self._proc = None


    @Verbose(1, 1)
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

            file = self._proc.stdout
            flags = fcntl.fcntl(file, fcntl.F_GETFL)
            fcntl.fcntl(file, fcntl.F_SETFL, flags|os.O_NONBLOCK)

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
        Destructor method, ensures the lock is released.
        """
        return self.stop()


    @Verbose(1, 1)
    def send(self, command, *args):
        """
        Sends string to the server. This is a low level tool, try yo use the 
        specific method insteat.
        """
        if self.is_alive():
            command = " ".join([command] + list(args))
            debug(command)

            self._proc.stdin.write(command)
            return self.get_result()

        else:
            raise IOError("Server is not alive")


    @Verbose(1, 1)
    def get_result(self):
        """
        Read and parse the server output.
        """

        lasttime = time.time()
        result = None
        output = ""
        while not result and self.is_alive():
            if READTIMEOUT < (time.time() - lasttime):
                debug("TIMEOUT")
                break

            try:
                new = self._proc.stdout.read()
                debug("Added to output: %s" % new)
                output += new
                lasttime = time.time()
            except IOError, e:
                debug("Waiting stdout")
                if e.errno != 11:
                    raise
                else:
                    time.sleep(.1)

            result = re.match(RESULT_RE, output)

        output = result.group(1) if result else output
        return output


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


    def sendsms(self, message, destination, smsc=None, smscno=None,
        report=False, use8bits=False, clase=None, validity=None, imelody=False,
        animation=None, concat=None, wappush=None):
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

        message = '\n%s\n\03' % message
        smsc = '--smsc "%s"' % smsc if smsc else ""
        smscno = '--smscno "%s"' % smscno if (smscno and not smsc) else ""
        report = '--report' if report else ""
        use8bits = '--use8bits' if use8bits else ""
        clase = '--class "%s"' % clase if clase else ""
        validity = '--validity "%s"' % validity if validity else ""
        imelody = '--imelody' if imelody else ""
        animation = '--animatfon "%s"' if animation else ""
        concat = '--concat "%s"' % concat if concat else ""
        wappush = '--wappush "%s"' % wappush if wappush else ""
        
        return self.send("--sendsms", destination, smsc, smscno, report, 
            use8bits, clase, validity, imelody, animation, concat, wappush,
            message)


    def savesms(self, message, sender=None, smsc=None,
        smscno=None, folder=None, location=None, sent=None, deliver=False):
        """
        Saves SMS messages to phone.

        :sender: sender number. Only if deliver is True
        :smsc: message center number. Only if deliver is True
        :smscno: message center index, smsc is taken from phone memory from
            address smscno. Only if deliver is True
        :folder: folder id where to save the SMS to. For values see getsms.
        :location: save the message to location number
        :new: mark the message as no sent/no readed (depending on deliver)
        :deliver: set the message type to SMS_Deliver
        :datetime: YYMMDDHHMMSS, sets datetime of delivery
        """

        smsc = '--smsc "%s"' % smsc if smsc else ''
        smscno = '--smscno "%s"' % smscno if (smscno and not smsc) else ''
        folder = '--folder "%s"' % folder if folder else ''
        location = '--location "%s"' % location if location else ''
        sent = '--sent' if not new else ''
        delive = '--deliver' if deliver else ''
        datetime = '--datetime %s' % datetime if datetime else ''
        message = '\n%s\n\03' % message

        return self.send("--savesms", sender, smsc, smscno, folder, location,
            sent, deliver, message)


    def getsmsc(self, start_number=None, end_number=None, raw=False):
        """
        Get the SMSC parameters from specified location(s) or for all locations.
        """
        
        assert start_number or not end_number

        start_number = start_number if start_number else ''
        end_number = end_number if end_number else ''
        raw = '--raw' if raw else ''
        
        return self.send('--getsmsc', start_number, end_number, raw)


    def setsmsc(self, smsc):
        """
        Set SMSC parameters. See raw output of getsmsc for syntax.
        """
#        TODO: Documentar mejor

        smsc = "\n%s\n\03" % smsc

        return self.send('--setsmsc', smsc)


    def createsmsfolder(self, name):
        """
        Create SMS folder with name name.
        """

        return self.send('--createsmsfolder', name)


    def deletesmsfolder(self, number):
        """
        Delete folder # number of 'My Folders'.
        """

        return self.send('--deletesmsfolder', number)


    def getsmsfolderstatus(self):
        """
        List SMS folder names with memory types and total number of
        messages available.
        """

        return self.send('--showsmsfolderstatus')


    def smsreader(self):
        """
        Keeps reading incoming SMS and saves them into the mailbox.
        """

        return self.send('--smsreader')


    def getmms(self, memory_type, start, end='', format="human"):
        """
        Gets MMS messages from specified  memory  type  starting  at  entry
        start and ending at end.
        
        :format: output format, could be "human" (human redeable), "pdu"
            (binary as received by the phone or "raw" (as read from the phone).
        """

        file = mktemp(".smsd")

        if format != "human":
            assert format in ("pdu", "raw")
            format = "--%s" % format

        result = self.send('--getmms', memory_type, start, end, format, file,
            '--overwrite')
        debug(result)

        return open(file).read()


    @Verbose(1, 1)
    def identify(self):
        """
        Get IMEI, manufacturer, model, product name and revision.
        """

        return self.send('--identify')


    def entersecuritycode(self, type, code):
        """
        Sends the security code to the phone.

        :type: The code type could be PIN, PIN2, PUK, PUK2 or SEC
        """

        assert type in ('PIN', 'PIN2', 'PUK', 'PUK2', 'SEC')

        return send('--entersecuritycode', type, code)


    def getsecuritycode(self):
        """
        Shows the currently set security code.
        """

        return self.send('--getsecuritycode')


    def getsecuritycodestatus(self):
        """
        Show if a security code is needed.
        """

        return self.send('--getsecuritycodestatus')


    def getlocksinfo(self):
        """
        Show information about the (sim)locks of the phone: the lock data,
        whether a lock is open or closed, whether it is a user or factory
        lock and the number of unlock attempts.
        """

        return self.send('--getlocksinfo')



def main():
    gnokii = Gnokii()
    gnokii.start()
    input = fileinput.input()

    line = True
    while line:
        line = input.readline()
        if line:
            words = line.split()
            print(gnokii.command(words[0], *words[1:]))


if __name__ == "__main__":
    exit(main())
