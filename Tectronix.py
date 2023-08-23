# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin
"""
import datetime
import http.client
import io
from PIL import Image
import os.path
import sys
import json
import logging
import time
import numpy

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QCheckBox
from PyQt5.QtWidgets import QPlainTextEdit
from PyQt5 import uic
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QFont
import PyQt5.QtGui as QtGui
from PyQt5 import QtNetwork

import matplotlib
import matplotlib.pyplot as plt

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')

from QtUtils import restore_settings, save_settings
from config_logger import config_logger
from mplwidget import MplWidget
from isfread import isfread

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = os.path.basename(__file__).replace('.py', '')
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '0.1'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

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


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        # Initialization of the superclass
        super(MainWindow, self).__init__(parent)
        # logging config
        self.logger = config_logger()
        # Load the UI
        uic.loadUi(UI_FILE, self)
        # Default window parameters
        self.setMinimumSize(QSize(480, 240))  # Set sizes
        self.resize(QSize(640, 480))
        self.move(QPoint(50, 50))
        self.setWindowTitle(APPLICATION_NAME)  # Set a title
        # self.setWindowIcon(QtGui.QIcon('icon.png'))
        restore_settings(self, file_name=CONFIG_FILE)
        self.folder = self.config.get('folder', 'D:/tec_data')
        self.make_data_folder()
        # Create new plot widget
        self.mplw = MplWidget()
        layout = self.frame_3.layout()
        layout.addWidget(self.mplw)
        # Connect signals with slots
        self.pushButton.clicked.connect(self.erase)
        self.comboBox.currentIndexChanged.connect(self.processing_changed)
        self.listWidget.itemSelectionChanged.connect(self.list_selection_changed)
        self.pushButton_2.clicked.connect(self.select_folder)
        self.comboBox_2.currentIndexChanged.connect(self.folder_changed)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionAbout.triggered.connect(self.show_about)
        # Additional decorations
        # self.radioButton.setStyleSheet('QRadioButton {background-color: red}')
        # self.lineEdit.setStyleSheet('QLineEdit {background-color: red}')
        # self.doubleSpinBox_4.setSingleStep(0.1)
        # Clock at status bar
        self.clock = QLabel(" ")
        # self.clock.setFont(QFont('Open Sans Bold', 14, weight=QFont.Bold))
        self.clock.setFont(QFont('Open Sans Bold', 12))
        self.statusBar().addPermanentWidget(self.clock)
        #
        self.read_folder(self.folder)
        self.ip = self.config.get('ip', "192.168.1.222")
        self.connection = tec_connect(self.ip)
        #
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

    def read_folder(self, folder):
        self.erase()
        # All files in the folder
        files = os.listdir(folder)
        # Filter *.isf files
        self.files = [f for f in files if f.endswith('.isf')]
        self.listWidget.setUpdatesEnabled(False)
        self.listWidget.blockSignals(True)
        self.listWidget.clear()
        self.listWidget.addItems(self.files)
        self.listWidget.blockSignals(False)
        if self.listWidget.count() <= 0:
            return
        self.listWidget.setUpdatesEnabled(True)
        self.listWidget.item(0).setSelected(True)

    def erase(self):
        self.mplw.canvas.ax.clear()
        ###self.list_selection_changed()
        # self.mplw.canvas.draw()

    def list_selection_changed(self):
        axes = self.mplw.canvas.ax
        if self.checkBox.isChecked():
            self.erase()
        axes.grid(color='k', linestyle='--')
        axes.set_title(self.folder)
        sel = self.listWidget.selectedItems()
        for item in sel:
            # print(item.text())
            full_name = os.path.join(self.folder, item.text())
            x, y, head = isfread(full_name)
            fy = numpy.fft.rfft(y)
            fx = numpy.arange(len(fy)) / len(y) / (x[1] - x[0])
            fp = numpy.abs(fy) ** 2
            zero = fp[0]
            fp[0] = 0.0
            if self.comboBox.currentIndex() == 1:
                axes.set_xlabel('Frequency, Hz')
                axes.set_ylabel('Spectral Power, a.u.')
                axes.plot(fx, fp, label=item.text())
            elif self.comboBox.currentIndex() == 2:
                fy = numpy.fft.rfft(y)
                fx = numpy.arange(len(fy)) / len(y) / (x[1] - x[0])
                fp = numpy.abs(fy) ** 2
                zero = fp[0]
                fp[0] = 0.0
                pf = fp * 0.0
                pf[-1] = fp[-1]
                for i in range(fx.size - 2, -1, -1):
                    pf[i] = pf[i + 1] + fp[i]
                axes.set_xlabel('Frequency, Hz')
                axes.set_ylabel('Cumulative Power, a.u.')
                axes.plot(fx, pf, label=item.text())
            elif self.comboBox.currentIndex() == 0:
                axes.set_xlabel('Time, s')
                axes.set_ylabel('Signal, V')
                axes.plot(x, y, label=item.text())
            else:
                evalsrt = ''
                try:
                    axes.set_xlabel('X value, a.u.')
                    axes.set_ylabel('Processed Signal, a.u.')
                    evalsrt = self.comboBox.currentText()
                    (xp, yp) = eval(evalsrt)
                    axes.plot(xp, yp, label=item.text())
                except:
                    self.logger.warning('eval() ERROR in %s' % evalsrt)
        axes.legend()
        self.mplw.canvas.draw()

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME +
                                ' Version ' + APPLICATION_VERSION +
                                '\nTextronix oscilloscope control utility.', QMessageBox.Ok)

    def on_quit(self):
        # Save global settings
        save_settings(self, file_name=CONFIG_FILE)
        timer.stop()
        self.connection.close()

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)

    def select_folder(self):
        """Opens a file select dialog"""
        # Define current dir
        if self.folder is None:
            self.folder = "./"
        dialog = QFileDialog(caption='Select folder', directory=self.folder)
        dialog.setFileMode(QFileDialog.Directory)
        # Open file selection dialog
        fn = dialog.getExistingDirectory()
        # if a fn is not empty
        if fn:
            # Qt4 and Qt5 compatibility workaround
            if len(fn[0]) > 1:
                fn = fn[0]
            # different file selected
            if self.folder == fn:
                return
            i = self.comboBox_2.findText(fn)
            if i < 0:
                # add item to history
                self.comboBox_2.setUpdatesEnabled(False)
                self.comboBox_2.blockSignals(True)
                self.comboBox_2.insertItem(-1, fn)
                self.comboBox_2.blockSignals(False)
                self.comboBox_2.setUpdatesEnabled(True)
                i = 0
            # change selection abd fire callback
            self.comboBox_2.setCurrentIndex(i)

    def folder_changed(self, m):
        folder = self.comboBox_2.currentText()
        # self.folder = self.comboBox_2.itemText(m)
        self.folder = folder
        self.read_folder(folder)

    def processing_changed(self, m):
        self.erase()
        # self.list_selection_changed()

    @staticmethod
    def get_log_folder():
        ydf = datetime.datetime.today().strftime('%Y')
        mdf = datetime.datetime.today().strftime('%Y-%m')
        ddf = datetime.datetime.today().strftime('%Y-%m-%d')
        folder = os.path.join(ydf, mdf, ddf)
        return folder

    def make_data_folder(self):
        of = os.path.join(self.folder, self.get_log_folder())
        try:
            if not os.path.exists(of):
                os.makedirs(of)
                self.logger.debug("Output folder %s has been created", of)
            self.out_dir = of
            return True
        except KeyboardInterrupt:
            raise
        except:
            self.logger.warning("Can not create output folder %s", of)
            self.out_dir = None
            return False


if __name__ == '__main__':
    # Create the GUI application
    app = QApplication(sys.argv)
    # Instantiate the main window
    dmw = MainWindow()
    app.aboutToQuit.connect(dmw.on_quit)
    # Show it
    dmw.show()
    # Defile and start timer task
    timer = QTimer()
    timer.timeout.connect(dmw.timer_handler)
    timer.start(1000)
    # Start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())

tec_ip = "192.168.1.222"


# conn = http.client.HTTPConnection(tec_ip)
# conn.request("GET", "/")
# r1 = conn.getresponse()
# print(r1.status, r1.reason)
# params = urllib.parse.urlencode({'COMMAND': '*idn?', '@gpibsend': 'Send', '@name': ''})

# command = '*idn?'       # read device id
# command = 'CH1:COUP DC' # set channel 1 coupling to DC (AC, GND)
# command = 'CH1:IMP MEG' # set channel 1 impedance to 1MOhm (FIF)
# command = 'CH1:VOL 1.0' # set channel 1 voltage rang 1 V/dib (real)
# command = 'CH1:POS 2.0' # set channel 1 position +2 divisions (real)
# command = 'HOR:SCAL 0.1'  # sampling 0.1 s/div
# command = 'HOR:TRIG:POS 50.0'  # horiz. trigger position 50% of screen
# command = 'ID?'  # similar to *idn?
# command = '*LRN?'  # read all settings
# command = 'TRIG?'  # query trigger params
# command = 'TRIG FORC'  # force trigger
# command = 'TRIG:STATE?'  # trigger state



print('Connecting')
t0 = time.time()
conn = tec_connect(tec_ip)
print('Elapsed', time.time() - t0, 's')

print('Sending command')
t0 = time.time()
result = tec_send_command(conn, 'TRIG:STATE?')
print('Elapsed', time.time() - t0, 's')
print(result)

print('Reading image')
t0 = time.time()
result = tec_get_image(conn)
print('Elapsed', time.time() - t0, 's')
imgplot = plt.imshow(result)
plt.show()

print('Reading data')
t0 = time.time()
x, y, head = tec_get_data(conn, 2)
print('Elapsed', time.time() - t0, 's')
print(head)
plt.plot(x, y)
plt.xlabel('Time, s')
plt.ylabel('Signal, V')
plt.show()

conn.close()

print('Finished')
