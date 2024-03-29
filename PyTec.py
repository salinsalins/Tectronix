# coding: utf-8
'''
Created on Jul 28, 2019

@author: sanin
'''

import json
import logging
import os.path
import sys
import time

import numpy
from PyQt5 import QtNetwork
from PyQt5 import uic
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QSize
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import qApp

# Global configuration dictionary
import conf
from isfread import isfread
from mplwidget import MplWidget
from widgetstate import set_state, get_state

#from conf import CONFIG
#CONFIG = conf.CONFIG

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'PyTec'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '1.0'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                                  datefmt='%H:%M:%S')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)



def print_exception_info(level=logging.DEBUG):
    logger.log(level, "Exception ", exc_info=True)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        global logger, log_formatter
        # Initialization of the superclass
        super(MainWindow, self).__init__(parent)

        # Load the UI
        uic.loadUi(UI_FILE, self)
        # Default window parameters
        self.setMinimumSize(QSize(480, 240))  # Set sizes
        self.resize(QSize(640, 480))
        self.move(QPoint(50, 50))
        self.setWindowTitle(APPLICATION_NAME)  # Set a title
        # self.setWindowIcon(QtGui.QIcon('icon.png'))

        # Create new plot widget
        self.mplw = MplWidget()
        self.mplw.ntb.show()
        # self.mplw.ntb.setIconSize(QSize(18, 18))
        # self.mplw.ntb.setFixedSize(300, 24)
        layout = self.frame_3.layout()
        layout.addWidget(self.mplw)
        axes = self.mplw.canvas.ax
        #axes.clear()
        #axes.set_xlabel('Time, s')
        #axes.set_ylabel('Signal, V')
        #axes.grid(color='k', linestyle='--')
        #x = numpy.arange(100.0)
        #y = numpy.sin(x)
        #axes.plot(x, y)
        # self.mplw.getViewBox().setBackgroundColor('#1d648da0')
        # font = QFont('Open Sans', 14, weight=QFont.Bold)
        font = QFont('Open Sans', 16)
        # axes.setFont(font)
        # self.mplw.getPlotItem().getAxis("bottom").setTickFont(font)
        # self.mplw.getPlotItem().getAxis("bottom").setStyle(tickTextOffset=16)
        # self.mplw.getPlotItem().getAxis("bottom").label.setFont(font)
        # self.mplw.getPlotItem().getAxis("left").setTickFont(font)
        # self.mplw.getPlotItem().getAxis("left").label.setFont(font)
        # self.mplw.getPlotItem().showGrid(True, True)
        # self.mplw.getPlotItem().setLabel('bottom', 'Time', units='s')
        # self.mplw.getPlotItem().setLabel('left', 'Signal', units='div')
        # self.plot = self.mplw.plot

        # Class members definition
        self.folder = None

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
        #self.lineEdit.setStyleSheet('QLineEdit {background-color: red}')
        # self.doubleSpinBox_4.setSingleStep(0.1)
        # Clock at status bar
        self.clock = QLabel(" ")
        # self.clock.setFont(QFont('Open Sans Bold', 14, weight=QFont.Bold))
        self.clock.setFont(QFont('Open Sans Bold', 12))
        self.statusBar().addPermanentWidget(self.clock)

        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

        self.restore_settings()
        #self.read_folder('./')

    def read_folder(self, folder):
        sel = self.listWidget.selectedItems()
        if len(sel) > 0:
            row = self.listWidget.row(sel[0])
        else:
            row = 0
        # All files in the folder
        files = os.listdir(folder)
        # Filter *.isf files
        self.files = [f for f in files if f.endswith('.isf')]
        self.listWidget.setUpdatesEnabled(False)
        self.listWidget.blockSignals(True)
        self.listWidget.clear()
        self.listWidget.addItems(self.files)
        self.listWidget.blockSignals(False)
        self.listWidget.setUpdatesEnabled(True)
        # self.listWidget.item(row).setSelected(True)
        self.listWidget.setCurrentRow(row)

    def erase(self):
        self.mplw.canvas.ax.clear()
        ###self.list_selection_changed()
        #self.mplw.canvas.draw()

    def list_selection_changed(self):
        axes = self.mplw.canvas.ax
        if self.checkBox.isChecked():
            self.erase()
        axes.grid(color='k', linestyle='--')
        axes.set_title(self.folder)
        sel = self.listWidget.selectedItems()
        for item in sel:
            #print(item.text())
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
                try:
                    axes.set_xlabel('X value, a.u.')
                    axes.set_ylabel('Processed Signal, a.u.')
                    evalsrt = self.comboBox.currentText()
                    (xp, yp) = eval(evalsrt)
                    axes.plot(xp, yp, label=item.text())
                except:
                    logger.log(logging.WARNING, 'eval() ERROR in %s' % evalsrt)
        axes.legend()
        self.mplw.canvas.draw()

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + ' Version ' + APPLICATION_VERSION +
                                '\nTextroix *.isf data file plot utility.', QMessageBox.Ok)

    def on_quit(self):
        # Save global settings
        self.save_settings()
        timer.stop()

    def save_settings(self, file_name=CONFIG_FILE):
        #global CONFIG
        try:
            # Save window size and position
            p = self.pos()
            s = self.size()
            conf.CONFIG['main_window'] = {'size': (s.width(), s.height()), 'position': (p.x(), p.y())}
            get_state(self.checkBox, 'checkBox')
            get_state(self.comboBox_2, 'comboBox_2')
            get_state(self.comboBox, 'comboBox')
            with open(file_name, 'w') as configfile:
                configfile.write(json.dumps(conf.CONFIG, indent=4))
            logger.info('Configuration saved to %s' % file_name)
            return True
        except:
            logger.log(logging.WARNING, 'Configuration save error to %s' % file_name)
            print_exception_info()
            return False

    def restore_settings(self, file_name=CONFIG_FILE):
        #global CONFIG
        try:
            with open(file_name, 'r') as configfile:
                s = configfile.read()
            conf.CONFIG = json.loads(s)
            # Restore log level
            if 'log_level' in conf.CONFIG:
                logger.setLevel(conf.CONFIG['log_level'])
            # Restore window size and position
            if 'main_window' in conf.CONFIG:
                self.resize(QSize(conf.CONFIG['main_window']['size'][0], conf.CONFIG['main_window']['size'][1]))
                self.move(QPoint(conf.CONFIG['main_window']['position'][0], conf.CONFIG['main_window']['position'][1]))
            set_state(self.checkBox, 'checkBox')
            set_state(self.comboBox, 'comboBox')
            set_state(self.comboBox_2, 'comboBox_2')
            logger.log(logging.INFO, 'Configuration restored from %s' % file_name)
            return True
        except:
            logger.log(logging.WARNING, 'Configuration restore error from %s' % file_name)
            print_exception_info()
            return False

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        files = os.listdir(self.folder)
        # Filter *.isf files
        isf_files = [f for f in files if f.endswith('.isf')]
        if len(isf_files) > len(self.files):
            self.read_folder(self.folder)


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
        self.folder = folder
        self.erase()
        self.read_folder(folder)

    def processing_changed(self, m):
        self.erase()
        #self.list_selection_changed()

    def data_arrived(self):
        print('Data has arrived')
        data, host, port = socket.readDatagram(512)
        print(data)
        print('From:')
        print(host.toString())
        print(port)
        # Sending back
        addr = QtNetwork.QHostAddress.LocalHost
        status = socket.writeDatagram(b'Hello there', host, port)
        print('Sending back', status)
        #status = socket.writeDatagram(b'Hello', addr, 7755)
        #print('Sending to 7755', status)


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
    # Start UDP server
    socket = QtNetwork.QUdpSocket()
    socket.bind(7755)
    socket.readyRead.connect(dmw.data_arrived)
    # Start the Qt main loop execution, exiting from this script
    # with the same return code of Qt application
    sys.exit(app.exec_())
