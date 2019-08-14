# coding: utf-8
'''
Created on Jul 28, 2019

@author: sanin
''' 

import os.path
import sys
import json
import logging
import zipfile
import time

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import qApp
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtWidgets import QTableWidget
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

import numpy as np
from mplwidget import MplWidget

from widgetstate import set_state, get_state

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'PyTec'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '0_1'
CONFIG_FILE = APPLICATION_NAME + '.json'

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                                       datefmt='%H:%M:%S')
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# Global configuration dictionary
CONFIG = {}


def print_exception_info(level=logging.DEBUG):
    logger.log(level, "Exception ", exc_info=True)


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        global logger, log_formatter
        # Initialization of the superclass
        super(MainWindow, self).__init__(parent)

        # Load the UI
        uic.loadUi('PyIonSourceUI.ui', self)
        # Default window parameters
        self.setMinimumSize(QSize(480, 240))  # Set sizes
        self.resize(QSize(640, 480))
        self.move(QPoint(50, 50))
        self.setWindowTitle(APPLICATION_NAME)  # Set a title
        self.setWindowIcon(QtGui.QIcon('icon.png'))

        # Additional logging config
        self.logger = logger
        text_edit_handler = TextEditHandler(self.plainTextEdit)
        text_edit_handler.setFormatter(log_formatter)
        self.logger.addHandler(text_edit_handler)

        # Class members definition
        self.refresh_flag = False
        self.last_selection = -1

        # Connect signals with slots
        ##self.pushButton_1.clicked.connect(self.selectLogFile)
        ##self.comboBox_1.currentIndexChanged.connect(self.logLevelIndexChanged)
        ##self.tableWidget_3.itemSelectionChanged.connect(self.table_sel_changed)
        ##self.plainTextEdit_1.textChanged.connect(self.refresh_on)
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        ##self.actionOpen.triggered.connect(self.selectLogFile)
        self.actionPlot.triggered.connect(self.show_main_pane)
        self.actionLog.triggered.connect(self.show_log_pane)
        self.actionParameters.triggered.connect(self.show_param_pane)
        self.actionAbout.triggered.connect(self.show_about)
        # Additional decorations
        # Disable text wrapping in log window
        self.plainTextEdit.setLineWrapMode(0)
        #self.pushButton_2.setStyleSheet('QPushButton {background-color: red}')
        #self.radioButton.setStyleSheet('QRadioButton {background-color: red}')
        self.lineEdit.setStyleSheet('QLineEdit {background-color: red}')
        self.doubleSpinBox_4.setSingleStep(0.1)
        # Clock at status bar
        self.clock = QLabel(" ")
        self.clock.setFont(QFont('Open Sans Bold', 14, weight=QFont.Bold))
        self.statusBar().addPermanentWidget(self.clock)

        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

        self.restore_settings()

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + ' Version ' + APPLICATION_VERSION +
                                '\nUser interface programm to control Negative Ion Source stand.', QMessageBox.Ok)

    def show_main_pane(self):
        self.stackedWidget.setCurrentIndex(0)
        self.actionPlot.setChecked(True)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(False)

    def show_log_pane(self):
        self.stackedWidget.setCurrentIndex(1)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(True)
        self.actionParameters.setChecked(False)

    def show_param_pane(self):
        self.stackedWidget.setCurrentIndex(2)
        self.actionPlot.setChecked(False)
        self.actionLog.setChecked(False)
        self.actionParameters.setChecked(True)

    def log_level_changed(self, m):
        levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                  logging.WARNING, logging.ERROR, logging.CRITICAL]
        if m >= 0:
            self.logger.setLevel(levels[m])
 
    def on_quit(self) :
        # Save global settings
        self.save_settings()
        timer.stop()
        
    def save_settings(self, file_name=CONFIG_FILE) :
        global CONFIG
        try:
            # Save window size and position
            p = self.pos()
            s = self.size()
            CONFIG['main_window'] = {'size':(s.width(), s.height()), 'position':(p.x(), p.y())}
            get_state(self.comboBox_1, 'comboBox_1')
            with open(file_name, 'w') as configfile:
                configfile.write(json.dumps(CONFIG, indent=4))
            self.logger.info('Configuration saved to %s' % file_name)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration save error to %s' % file_name)
            self.print_exception_info()
            return False
        
    def restore_settings(self, file_name=CONFIG_FILE) :
        global CONFIG
        try :
            with open(file_name, 'r') as configfile:
                s = configfile.read()
            CONFIG = json.loads(s)
            # Restore log level
            if 'log_level' in CONFIG:
                v = CONFIG['log_level']
                self.logger.setLevel(v)
                levels = [logging.NOTSET, logging.DEBUG, logging.INFO,
                          logging.WARNING, logging.ERROR, logging.CRITICAL, logging.CRITICAL+10]
                for m in range(len(levels)):
                    if v < levels[m]:
                        break
                self.comboBox_1.setCurrentIndex(m-1)
            # Restore window size and position
            if 'main_window' in CONFIG:
                self.resize(QSize(CONFIG['main_window']['size'][0], CONFIG['main_window']['size'][1]))
                self.move(QPoint(CONFIG['main_window']['position'][0], CONFIG['main_window']['position'][1]))
            #set_state(self.plainTextEdit_1, 'plainTextEdit_1')
            set_state(self.comboBox_1, 'comboBox_1')
            self.logger.log(logging.INFO, 'Configuration restored from %s' % file_name)
            return True
        except :
            self.logger.log(logging.WARNING, 'Configuration restore error from %s' % file_name)
            print_exception_info()
            return False

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)


# Logging to the text panel
class TextEditHandler(logging.Handler):
    def __init__(self, widget=None):
        logging.Handler.__init__(self)
        self.widget = widget

    def emit(self, record):
        log_entry = self.format(record)
        if self.widget is not None:
            self.widget.appendPlainText(log_entry)


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
