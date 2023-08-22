import http.client, urllib.parse

tec_ip = "192.168.1.222"

# conn = http.client.HTTPConnection(tec_ip)
# conn.request("GET", "/")
# r1 = conn.getresponse()
# print(r1.status, r1.reason)

# params = urllib.parse.urlencode({'COMMAND': '*idn?', '@gpibsend': 'Send', '@name': ''})
# command = '*idn?'
command = 'CH1:COUP DC'
params = ('COMMAND=' + command + '\n\rgpibsend=Send\n\rname=\n\r').encode()
headers = {"Content-type": "text/plain",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"}
conn = http.client.HTTPConnection(tec_ip)
conn.request("POST", "/Comm.html", params, headers)
response = conn.getresponse()
print(response.status, response.reason)
data = response.read(1300)
# while True:
#     data = response.read(1300)
#     if not data:
#         break
print(data)
d_data = data.decode()
n = d_data.find('<TEXTAREA')
n1 = d_data[n:].find('>')
m = d_data.find('</TEXTAREA>')
print(d_data[n+n1+1:m])
conn.close()