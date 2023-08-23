import http.client, urllib.parse
import io
import time
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from isfread import isfread


tec_ip = "192.168.1.222"

# conn = http.client.HTTPConnection(tec_ip)
# conn.request("GET", "/")
# r1 = conn.getresponse()
# print(r1.status, r1.reason)

# params = urllib.parse.urlencode({'COMMAND': '*idn?', '@gpibsend': 'Send', '@name': ''})
# command = '*idn?'
# command = 'CH1:COUP DC' # set channel 1 coupling to DC (AC, GND)
# command = 'CH1:IMP MEG' # set channel 1 impedance to 1MOhm (FIF)
# command = 'CH1:VOL 1.0' # set channel 1 impedance to 1MOhm (FIF)
# command = 'CH1:POS 2.0' # set channel 1 impedance to 1MOhm (FIF)
# command = 'HOR:SCAL 0.1'  # sampling 0.1 s|div
# command = 'HOR:TRIG:POS 50.0'  # horiz. trigger position % of screen
# command = 'CH1:POS 1.0'  # vertical position at + 1.0 division
# command = 'ID?'  # similar to *idn?
# command = '*LRN?'  # read all settings
# command = 'TRIG?'  # query trigger params
# command = 'TRIG FORC'  # force trigger
# command = 'TRIG:STATE?'  # trigger state


def tec_connect(ip):
    conn = http.client.HTTPConnection(ip)
    return conn


def tec_send_command(conn, cmd):
    params = ('COMMAND=' + cmd + '\n\rgpibsend=Send\n\rname=\n\r').encode()
    headers = {"Content-type": "text/plain",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
    conn.request("POST", "/Comm.html", params, headers)
    response = conn.getresponse()
    if response.status != 200:
        return None
    data = b''
    while True:
        d = response.read(1024)
        if not d:
            break
        data += d
    data = data.decode()
    n = data.find('<TEXTAREA')
    if n < 0:
        return None
    n1 = data[n:].find('>')
    if n1 < 0:
        return None
    m = data.find('</TEXTAREA>')
    if m < 0:
        return None
    return data[n + n1 + 1:m]


def tec_get_image(conn):
    params = b''
    headers = {"Accept": "image/avif,image/webp,*/*"}
    conn.request("GET", "/Image.png", params, headers)
    response = conn.getresponse()
    data = b''
    while True:
        d = response.read(1024)
        if not d:
            break
        data += d
    img = Image.open(io.BytesIO(data))
    return img


def tec_get_data(conn, chan_number):
    str = 'command=select:ch%s on\r\ncommand=save:waveform:fileformat internal\r\nwfmsend=Get\r\n' % chan_number
    params = str.encode()
    headers = {"Accept": "text/html, application/xhtml+xml, image/jxr, */*",
               "Content-Type": "text/plain",
               "Cache-Control": "no-cache"}
    conn.request("POST", "/getwfm.isf", params, headers)
    response = conn.getresponse()
    data = b''
    while True:
        d = response.read(1024)
        if not d:
            break
        data += d
    x, y, head = isfread(io.BytesIO(data))
    return (x, y, head)


t0 = time.time()
conn = tec_connect(tec_ip)
print('Elapsed', time.time() - t0, 's')

t0 = time.time()
result = tec_send_command(conn, 'TRIG:STATE?')
print('Elapsed', time.time() - t0, 's')
print(result)

t0 = time.time()
result = tec_get_image(conn)
print('Elapsed', time.time() - t0, 's')
imgplot = plt.imshow(result)
plt.show()

t0 = time.time()
x, y, head = tec_get_data(conn, 2)
print('Elapsed', time.time() - t0, 's')
plt.plot(x, y)
plt.xlabel('Time (ms)')
plt.ylabel('Voltage (mV)')
plt.show()

conn.close()

print('Finished')
