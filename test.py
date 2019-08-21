from PyQt5 import QtNetwork


def data_arrived(self):
    print('Data has arrived')
    data, host, port = socket.readDatagram(512)
    print(data)
    print('From:')
    print(host.toString())
    print(port)

# Start UDP server
socket = QtNetwork.QUdpSocket()
socket.bind(7766)
# Send message
#addr = QtNetwork.QHostAddress('')
addr = QtNetwork.QHostAddress.LocalHost
status = socket.writeDatagram(b'Hello', addr, 7755)
print(status)

socket.readyRead.connect(data_arrived)

while True:
    if socket.bytesAvailable():
        data, host, port = socket.readDatagram(512)
        print(data)
        print('From:')
        print(host.toString())
        print(port)
