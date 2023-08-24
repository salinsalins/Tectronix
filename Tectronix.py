# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin

s='s=%r;print(s%%s)';print(s%s)
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
# from mplwidget import MplWidget
from pyqtgraphwidget import MplWidget
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
    return x, y, head, data


class TectronixTDS:
    default = {
        # '*LRN?': '',
        'ACQuire:STOPAfter': 'SEQ',  # RUNSTop | SEQuence
        'ACQuire:MODe': 'SAMple',  # PEKdetect | AVErage,
        'ACQuire:NUMACq?': '',
        'ACQuire:STATE': '0',  # 1 | 0 | RUN | STOP
        # 'BUSY?': '',  # 0 | 1
        # 'CH1:BANdwidth': '',
        # 'CH1:COUPling': '',
        # 'CH1:DESKew': '0.0',
        # 'CH1:IMPedance': '',
        # 'CH1:OFFSet': '',
        # 'CH1:POSition': '',
        # 'CH1:PRObe?': '',
        'CH1:SCAle': '',
        # 'CH2:BANdwidth': '',
        # 'CH2:COUPling': '',
        # 'CH2:DESKew': '0.0',
        # 'CH2:IMPedance': '',
        # 'CH2:OFFSet': '',
        # 'CH2:POSition': '',
        # 'CH2:PRObe?': '',
        'CH2:SCAle': '',
        # 'CH3:BANdwidth': '',
        # 'CH3:COUPling': '',
        # 'CH3:DESKew': '0.0',
        # 'CH3:IMPedance': '',
        # 'CH3:OFFSet': '',
        # 'CH3:POSition': '',
        # 'CH3:PRObe?': '',
        'CH3:SCAle': '',
        # 'CH4:BANdwidth': '',
        # 'CH4:COUPling': '',
        # 'CH4:DESKew': '0.0',
        # 'CH4:IMPedance': '',
        # 'CH4:OFFSet': '',
        # 'CH4:POSition': '',
        # 'CH4:PRObe?': '',
        'CH4:SCAle': '',
        # 'DATE': '',
        # 'HORizontal:DELay:TIMe?': '',
        'HORizontal:MAIn:SCAle': '',  # sec / div
        'HORizontal:TRIGger:POSition': '',
        'ID?': '',
        # 'SELect?': '',
        'SELect:CH1': '',  # 1 | 0 | ON | OFF
        'SELect:CH2': '',  # 1 | 0 | ON | OFF
        'SELect:CH3': '',  # 1 | 0 | ON | OFF
        'SELect:CH4': '',  # 1 | 0 | ON | OFF
        'TIMe': '',
        'TRIGger': '',
        # 'TRIGger:MAIn:EDGE:COUPling': '',
        # 'TRIGger:MAIn:EDGE:SLOpe': '',
        # 'TRIGger:MAIn:EDGE:SOUrce': '',
        # 'TRIGger:MAIn:LEVel': '',
        # 'TRIGger:MAIn:MODe': '',  # AUTO | NORMAL
        # 'TRIGger:MAIn:TYPe': '',
        'TRIGger:STATE?': '',  # ARMED or not
        # 'VERBose': '0',
        '*idn?': ''
    }

    def __init__(self, ip=None, config=None, logger=None):
        if logger is None:
            self.logger = config_logger()
        else:
            self.logger = logger
        self.config = {}
        if config is not None:
            self.config = config
        self.ip = '192.168.1.222'
        if ip is not None:
            self.ip = ip
        self.connection = None
        try:
            self.connection = tec_connect(self.ip)
        except:
            raise
        self.plots = {}
        self.isf = {}
        self.tec_type = ''
        self.last_aq = ''
        self.set_config()
        self.logger.debug('%s at %s has been initialized %s', self.tec_type, self.ip, self.last_aq)

    def send_command(self, cmd):
        result = tec_send_command(self.connection, cmd)
        # self.logger.debug('%s -> %s', cmd, result)
        return result

    def get_data(self, ch_n):
        return tec_get_data(self.connection, ch_n)

    def get_image(self):
        return tec_get_image(self.connection)

    def set_config(self, config=None):
        if config is None:
            config = self.config
        cfg = self.default.copy()
        cfg.update(config)
        self.config = cfg
        for key in self.config:
            if key.endswith('?') or self.config[key] == '':
                if key.endswith("?"):
                    key1 = key
                else:
                    key1 = key + "?"
                self.config[key] = self.send_command(key1)
                # self.logger.debug('Read %s = %s', key, self.config[key])
            else:
                self.send_command(key + ' ' + self.config[key])
                # self.logger.debug('Set  %s = %s', key, self.config[key])

        t = self.config['*idn?'].split(',')
        self.tec_type = ' '.join(t[0:2])
        self.last_aq = self.send_command('ACQuire:NUMACq?')
        self.config['ACQuire:NUMACq?'] = self.last_aq

    def is_aq_finished(self):
        num_aq = self.send_command('ACQuire:NUMACq?')
        if num_aq != self.last_aq:
            self.logger.debug('New shot detected %s %s', num_aq, self.last_aq)
            self.last_aq = num_aq
            return True
        return False

    def start_aq(self):
        self.send_command('ACQuire:STATE 0')
        self.send_command('ACQuire:STATE 1')
        self.last_aq = self.send_command('ACQuire:NUMACq?')
        st = self.send_command('TRIGger:STATE?')
        if st.upper().startswith('ARMED'):
            return True
        return False

    def stop_aq(self):
        self.send_command('ACQuire:STATE 0')
        # st = self.send_command('TRIGger:STATE?')
        # if st.upper().startswith('ARMED'):
        #     return False
        return True

    def is_aq_in_progeress(self):
        st = self.send_command('BUSY?')
        if st.upper().startswith('1'):
            return True
        return False

    def read_plots(self):
        self.plots = {}
        self.isf = {}
        sel = self.send_command('SEL?').split(';')
        for i in range(4):
            if sel[i] == '1':
                # if self.send_command('SELect:CH%s?'%ch) == '1':
                x, y, h, isf = tec_get_data(self.connection, i)
                self.plots[i] = {'x': x, 'y': y}
                self.isf[i] = isf
        return self.plots


class PlotItem:
    colors = ['r', 'g', 'b', 'y', 'c', 'm']
    color_index = 0
    label_index = 0

    def __init__(self, x, y, label=None, color=None):
        self.x = x
        self.y = y
        self.label = label
        if label is None:
            self.label = 'Label%s' % PlotItem.label_index
            PlotItem.label_index += 1
        self.color = color
        if color is None:
            self.color = self.colors[PlotItem.color_index]
            PlotItem.color_index += 1
            if PlotItem.color_index >= len(PlotItem.colors):
                PlotItem.color_index = 0


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
        restore_settings(self, file_name=CONFIG_FILE, widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2))
        self.folder = self.config.get('folder', 'D:/tec_data')
        self.comboBox_2.insertItem(0, self.folder)
        self.out_dir = ''
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
        self.pushButton_3.clicked.connect(self.send_command_pressed)
        self.checkBox_1.clicked.connect(self.ch1_clicked)
        self.checkBox_2.clicked.connect(self.ch2_clicked)
        self.checkBox_3.clicked.connect(self.ch3_clicked)
        self.checkBox_4.clicked.connect(self.ch4_clicked)
        self.pushButton_4.toggled.connect(self.run_toggled)
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
        self.read_folder(self.out_dir)
        devices = self.config.get('devices', {})
        if len(devices) <= 0:
            self.logger.error("No Oscilloscopes defined in config")
            exit(-111)
        self.devices = {}
        for d in devices:
            self.devices[d] = TectronixTDS(ip=d, config=devices[d])
            self.devices[d].start_aq()
        self.device = list(self.devices.values())[0]
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

    def send_command_pressed(self):
        txt = self.lineEdit_2.text()
        rsp = list(self.devices.values())[0].send_command(txt)
        # print(rsp)
        self.label_6.setText(rsp)

    def ch1_clicked(self):
        if self.checkBox_1.isChecked():
            for d in self.devices:
                self.devices[d].send_command('SELect:CH1 1' )
        else:
            for d in self.devices:
                self.devices[d].send_command('SELect:CH1 0' )

    def ch2_clicked(self):
        if self.checkBox_2.isChecked():
            for d in self.devices:
                self.devices[d].send_command('SELect:CH2 1' )
        else:
            for d in self.devices:
                self.devices[d].send_command('SELect:CH2 0' )

    def ch3_clicked(self):
        if self.checkBox_3.isChecked():
            for d in self.devices:
                self.devices[d].send_command('SELect:CH3 1' )
        else:
            for d in self.devices:
                self.devices[d].send_command('SELect:CH3 0' )

    def ch4_clicked(self):
        if self.checkBox_4.isChecked():
            for d in self.devices:
                self.devices[d].send_command('SELect:CH4 1' )
        else:
            for d in self.devices:
                self.devices[d].send_command('SELect:CH4 0' )

    def run_toggled(self):
        if self.pushButton_4.isChecked():
            for d in self.devices:
                self.devices[d].start_aq()
            self.pushButton_4.setText('Stop')
            self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: green;}')
        else:
            for d in self.devices:
                self.devices[d].stop_aq()
            self.pushButton_4.setText('Run')
            self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: red;}')

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

    def plot_data(self, data):
        axes = self.mplw.canvas.ax
        if self.checkBox.isChecked():
            self.erase()
        # axes.grid(color='k', linestyle='--')
        axes.set_title(self.folder)
        for item in data:
            self.plot_trace(item)
        # axes.legend()
        self.mplw.canvas.draw()

    def plot_trace(self, item):
        axes = self.mplw.canvas.ax
        x = item.x
        y = item.y
        if self.comboBox.currentIndex() == 0:
            axes.set_xlabel('Time, s')
            axes.set_ylabel('Signal, V')
            axes.plot(x, y, label=item.label, color=item.color)
            return
        if self.comboBox.currentIndex() == 1:
            fy = numpy.fft.rfft(y)
            fx = numpy.arange(len(fy)) / len(y) / (x[1] - x[0])
            fp = numpy.abs(fy) ** 2
            fp[0] = 0.0
            axes.set_xlabel('Frequency, Hz')
            axes.set_ylabel('Spectral Power, a.u.')
            axes.plot(fx, fp, label=item.label, color=item.color)
        elif self.comboBox.currentIndex() == 2:
            fy = numpy.fft.rfft(y)
            fx = numpy.arange(len(fy)) / len(y) / (x[1] - x[0])
            fp = numpy.abs(fy) ** 2
            fp[0] = 0.0
            pf = fp * 0.0
            pf[-1] = fp[-1]
            for i in range(fx.size - 2, -1, -1):
                pf[i] = pf[i + 1] + fp[i]
            axes.set_xlabel('Frequency, Hz')
            axes.set_ylabel('Cumulative Power, a.u.')
            axes.plot(fx, pf, label=item.label, color=item.color)
        else:
            evalsrt = ''
            try:
                axes.set_xlabel('X value, a.u.')
                axes.set_ylabel('Processed Signal, a.u.')
                evalsrt = self.comboBox.currentText()
                (xp, yp) = eval(evalsrt)
                axes.plot(xp, yp, label=item.label, color=item.color)
            except:
                self.logger.warning('eval() ERROR in %s' % evalsrt)

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME +
                                ' Version ' + APPLICATION_VERSION +
                                '\nTextronix oscilloscope control utility.', QMessageBox.Ok)

    def on_quit(self):
        # Save global settings
        save_settings(self, file_name=CONFIG_FILE, widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2))
        timer.stop()
        for d in self.devices.values():
            d.connection.close()

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        for d in self.devices:
            if self.devices[d].is_aq_finished():
                data = []
                plots = self.devices[d].read_plots()
                for p in plots.values():
                    data.append(PlotItem(p['x'], p['y']))
                self.plot_data(data)
                self.save_isf(self.devices[d].isf)
                self.devices[d].start_aq()

    def save_isf(self, isf):
        for i in isf:
            file_name = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '-CH%s.isf' % (i+1)
            with open(os.path.join(self.out_dir, file_name), 'wb') as fid:
                fid.write(isf[i])


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
            # if current folder selected
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
            # change selection and fire callback
            if self.comboBox_2.currentIndex() != i:
                self.comboBox_2.setCurrentIndex(i)
            else:
                self.folder_changed(i)

    def folder_changed(self, m):
        folder = self.comboBox_2.currentText()
        # self.folder = self.comboBox_2.itemText(m)
        self.folder = folder
        self.make_data_folder()
        self.read_folder(self.out_dir)

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
