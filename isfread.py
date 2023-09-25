import struct
import numpy


def isfread(filename):
    """ Read isf file and return x y and head information.

    input:
        string with the ISF-filename.
    output:
        Returns a tuple of three elements:
        x - list with the x values
        y - list with the y values
        head - dictionary with the head-information stored in the file.

    """

    # Subroutines used to extract information from the head --------------------
    def getnum(string, tag):
        """ Look into the string for the tag and extract the consequent number"""
        n1 = string.find(tag)
        n2 = string.find(b';', n1)

        s2 = string[n1 + len(tag):n2]
        j = s2.find(b'.')
        if j == -1:
            return int(string[n1 + len(tag):n2])
        else:
            return float(string[n1 + len(tag):n2])

    def getstr(string, tag):
        """ Look into the string for the tag and extract the consequent string"""
        n1 = string.find(tag)
        n2 = string.find(b';', n1)
        return string[n1 + len(tag):n2].decode('ascii').lstrip()

    def getquotedstr(string, tag):
        """ Look into the string for the tag and extract the consequent quoted
        string"""
        n1 = string.find(tag)
        n2 = string.find(b'"', n1 + 1)
        n3 = string.find(b'"', n2 + 1)
        return string[n2+1:n3].decode('ascii')

    if isinstance(filename, str):
        fid = open(filename, 'rb')
    else:
        fid = filename
    hdata = fid.read(511)  # read first 511 bytes
    head = {'bytenum': getnum(hdata, b'BYT_NR'),
            'bitnum': getnum(hdata, b'BIT_NR'),
            'encoding': getstr(hdata, b'ENCDG'),
            'binformat': getstr(hdata, b'BN_FMT'),
            'byteorder': getstr(hdata, b'BYT_OR'),
            'wfid': getquotedstr(hdata, b'WFID'),
            'pointformat': getstr(hdata, b'PT_FMT'),
            'xunit': getquotedstr(hdata, b'XUNIT'),
            'yunit': getquotedstr(hdata, b'YUNIT'),
            'xzero': getnum(hdata, b'XZERO'),
            'xincr': getnum(hdata, b'XINCR'),
            'ptoff': getnum(hdata, b'PT_OFF'),
            'ymult': getnum(hdata, b'YMULT'),
            'yzero': getnum(hdata, b'YZERO'),
            'yoff': getnum(hdata, b'YOFF'),
            'npts': getnum(hdata, b'NR_PT')}

    # The only cases that this code (at this moment) not take into account.
    if ((head['bytenum'] != 2) or (head['bitnum'] != 16) or
            (head['encoding'] != 'BIN') or (head['binformat'] != 'RI') or
            (head['pointformat'] != 'Y')):
        fid.close()
        raise ValueError('Wrong format of *.isf file.')

    # Reading the <Block> part corresponding to the "CURVe" command [TekMan].
    # <Block> = ":CURVE #<x><yy..y><data>"
    # <x> number of bytes defining <yy..y>
    # <yy..y> number of bytes to "transfer"/read in the data part.
    # <data>: the data in binary
    #
    # Comment: It should be happend that: NR_PT times BYT_NR = <yy..y>

    # Skipping the #<x><yy...y> part of the <Block> bytes
    ii = hdata.find(b':CURVE #')
    fid.seek(ii + 8)
    skip = int(fid.read(1))
    n1 = int(fid.read(skip))

    # information from the head needed to read and to convert the data
    npts = head['npts']
    yzero = head['yzero']
    ymult = head['ymult']
    xzero = head['xzero']
    xincr = head['xincr']
    ptoff = head['ptoff']
    yoff = head['yoff']

    dict_endian = {  # Dictionary to converts significant bit infor-
        'MSB': '>',  # mation to struct module definitions.
        'LSB': '<'
    }
    fmt = dict_endian[head['byteorder']] + str(npts) + 'h'
    n2 = struct.calcsize(fmt)

    # "n1" is the number of bytes to be red directly from Tek-ISF-file.
    # Meanwhile "n2" is the number of bytes to be red calculated through:
    #                    NumOfPoints x BytePerPoint
    if n1 != n2:
        print("\nWARNING: Errors in *.isf file srudcture.")
    string_data = fid.read(n2)
    fid.close()
    data = struct.unpack(fmt, string_data)

    # Absolute values of data obtained as is defined in [Tek-Man] WFMPre:PT_Fmt
    # command description.
    #v = [yzero + ymult * (y - yoff) for y in data]
    #x = [xzero + xincr * (i - ptoff) for i in range(npts)]
    v = (numpy.array(data) - yoff) * ymult + yzero
    x = (numpy.arange(npts) - ptoff) * xincr + xzero

    return x, v, head
