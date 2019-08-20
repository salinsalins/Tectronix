from PyQt5 import QtNetwork

socket = QtNetwork.QUdpSocket()
socket.bind(7755)
addr = QtNetwork.QHostAddress('')
addr = QtNetwork.QHostAddress.LocalHost
status = socket.writeDatagram(b'Hello', addr, 7755)

print(status)
