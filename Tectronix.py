import http.client, urllib.parse

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
command = 'HOR:SCAL 0.1'    # sampling 0.1 s|div
command = 'HOR:TRIG:POS 50.0'    # horiz. trigger position % of screen
command = 'CH1:POS 1.0'     # vertical position at + 1.0 division
command = 'ID?'             # similar to *idn?
command = '*LRN?'           # read all settings
command = 'TRIG?'           # query trigger params
command = 'TRIG FORC'       # force trigger
command = 'TRIG:STATE?'     # trigger state
params = ('COMMAND=' + command + '\n\rgpibsend=Send\n\rname=\n\r').encode()
headers = {"Content-type": "text/plain",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
conn = http.client.HTTPConnection(tec_ip)
conn.request("POST", "/Comm.html", params, headers)
response = conn.getresponse()
print(response.status, response.reason)

data = b''
while True:
    get = response.read(1024)
    if not get:
        break
    data += get
print(data)
d_data = data.decode()
n = d_data.find('<TEXTAREA')
n1 = d_data[n:].find('>')
m = d_data.find('</TEXTAREA>')
print(d_data[n+n1+1:m])
conn.close()