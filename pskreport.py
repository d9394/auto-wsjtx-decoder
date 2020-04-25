#
# send a report to pskreporter.info.
#
# https://pskreporter.info/pskdev.html
#

import struct
import time
import socket
import sys

# turn an array of 8-bit numbers into a string.
def hx(a):
    s = b''
    for x in a:
        s = s + x
    return s

# pack a string, preceded by length.
def pstr(s):
    return (chr(len(s)) + s).encode('utf-8')

# pack a 32-bit int.
def p32(i):
    z = struct.pack(">I", i)
    assert len(z) == 4
    return z

# pack a 16-bit int.
def p16(i):
    z = struct.pack(">H", i)
    assert len(z) == 2
    return z

# pad to a multiple of four byte.
def pad(s):
    while (len(s) % 4) != 0:
        s += chr(0).encode('utf-8')
    return s

#
# format and send reports.
#
class T:

    def __init__(self, mycall, mygrid, mysw, testing=False):
        self.testing = testing
        self.seq = 1
        self.sessionId = int(time.time())
        self.mycall = mycall
        self.mygrid = mygrid
        self.mysw = mysw

        host = "report.pskreporter.info"
        if self.testing:
            port = 14739 # test server
            # test view: https://pskreporter.info/cgi-bin/psk-analysis.pl
        else:
            port = 4739 # production server

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.connect((host, port))

        # accumulate a list, send only every 5 minutes.
        self.pending = [ ]
        self.last_send = 0

    # seq should increment once per packet.
    # sessionId should stay the same.
    # mysw is the name of the software.
    # each senders element is [ call, freq, snr, grid, time ]
    # e.g. [ "KB1MBX", 14070987, "PSK31", "FN42", 1200960104 ]
    # modes: JT65, PSK31
    def fmt(self, senders):
    
        # receiver record format descriptor.
        # callsign, locator, s/w.
        rrf = hx([b'\x00', b'\x03', b'\x00', b'\x24', b'\x99', b'\x92', b'\x00', b'\x03', b'\x00', b'\x00',
                  b'\x80', b'\x02', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                  b'\x80', b'\x04', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                  b'\x80', b'\x08', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                  b'\x00', b'\x00',])
    
        # sender record format descriptor.
        if False:
            # senderCallsign', frequency', sNR (1 byte)', iMD (1 byte)', mode (1 byte)', informationSource', flowStartSeconds.
            srf = hx([ b'\x00', b'\x02', b'\x00', b'\x3C', b'\x99', b'\x93', b'\x00', b'\x07',
                       b'\x80', b'\x01', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x05', b'\x00', b'\x04', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x06', b'\x00', b'\x01', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x07', b'\x00', b'\x01', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x0A', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x0B', b'\x00', b'\x01', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x00', b'\x96', b'\x00', b'\x04',])
    
        if True:
            # senderCallsign', frequency', mode', informationSource=1', senderLocator', flowStartSeconds
            srf = hx([ b'\x00', b'\x02', b'\x00', b'\x34', b'\x99', b'\x93', b'\x00', b'\x06',
                       b'\x80', b'\x01', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x05', b'\x00', b'\x04', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x0A', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x0B', b'\x00', b'\x01', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x80', b'\x03', b'\xFF', b'\xFF', b'\x00', b'\x00', b'\x76', b'\x8F',
                       b'\x00', b'\x96', b'\x00', b'\x04',])
    
        # receiver record.
        # first cook up the data part of the record, since length comes first.
        rr = b''
        rr += pstr(self.mycall)
        rr += pstr(self.mygrid)
        rr += pstr(self.mysw)
        rr = pad(rr)
        # prepend rr's header.
        rr = hx([b'\x99', b'\x92']) + p16(len(rr) + 4) + rr
    
        # sender records.
        # first the array of per-sender records, so we can find the length.
        sr = b''
        for snd in senders:
            # snd = [ "KB1MBX", 14070987, "PSK", "FN42", 1200960104 ]
            sr += pstr(snd[0]) # call sign
            sr += p32(snd[1])  # frequency
            sr += pstr(snd[2]) # "JT65"
#            sr += chr(1).encode('utf-8') # informationSource
            sr += b'\x01'
            sr += pstr(snd[3]) # grid
            sr += p32(int(snd[4])) #time
        sr = pad(sr)
        # prepend the sender records header, with length.
        sr = hx([b'\x99', b'\x93']) + p16(len(sr) + 4) + sr
    
        # now the overall header (16 bytes long).
        h = b''
        h += hx([ b'\x00', b'\x0a' ])
        h += p16(len(rrf) + len(srf) + len(rr) + len(sr) + 16)
        h += p32(int(time.time()))
        h += p32(self.seq)
        self.seq += 1
        h += p32(self.sessionId)
    
        pkt = h + rrf + srf + rr + sr
    
        return pkt

    def dump(self, pkt):
        for i in range(0, 20):
            sys.stdout.write("%02x " % ord(pkt[i]))
        sys.stdout.write("\n")

    def send(self, pkt):
        print("Sended to pskreport %d" % len(pkt))
        self.s.send(pkt)

    # caller received something. buffer it until 5 minutes
    # since last send.
    # XXX what if packet would be > MTU but not yet 5 minutes?
    def got(self, call, hz, mode, grid, tm):
        info = [ call, int(hz), mode, grid, int(tm) ]
        self.pending.append(info)
        if time.time() - self.last_send >= 5*60:
            pkt = self.fmt(self.pending)
            self.send(pkt)
            self.pending = [ ]
            self.last_send = time.time()
