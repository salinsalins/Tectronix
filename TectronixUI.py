# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin

s='s=%r;print(s%%s)';print(s%s)
"""
import datetime
import io

import os.path
import sys
import time
import numpy

import PyQt5
import pyqtgraph

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

from Tectronix import TectronixTDS

if '../TangoUtils' not in sys.path: sys.path.append('../TangoUtils')

from QtUtils import restore_settings, save_settings
from config_logger import config_logger
# from mplwidget import MplWidget
from pyqtgraphwidget import MplWidget
from isfread import isfread

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = os.path.basename(__file__).replace('.py', '')
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '1.1'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'


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
        restore_settings(self, file_name=CONFIG_FILE,
                         widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2, self.checkBox))
        self.folder = self.config.get('folder', 'D:/tec_data')
        if self.comboBox_2.findText(self.folder) < 0:
            self.comboBox_2.insertItem(0, self.folder)
        self.out_dir = ''
        self.make_data_folder()
        # Create new plot widget
        self.mplw = MplWidget()
        layout = self.frame_3.layout()
        layout.addWidget(self.mplw)
        self.mplw.getViewBox().setBackgroundColor('#1d648da0')
        # font = QFont('Open Sans', 14, weight=QFont.Bold)
        font = QFont('Open Sans', 16)
        self.mplw.getPlotItem().getAxis("bottom").setTickFont(font)
        self.mplw.getPlotItem().getAxis("bottom").setStyle(tickTextOffset=16)
        self.mplw.getPlotItem().getAxis("bottom").label.setFont(font)
        self.mplw.getPlotItem().getAxis("left").setTickFont(font)
        self.mplw.getPlotItem().getAxis("left").label.setFont(font)
        self.mplw.getPlotItem().showGrid(True, True)
        self.mplw.getPlotItem().setLabel('bottom', 'Time', units='s')
        self.mplw.getPlotItem().setLabel('left', 'Signal', units='div')
        self.plot = self.mplw.plot

        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionAbout.triggered.connect(self.show_about)
        # Clock at status bar
        self.clock = QLabel(" ")
        # self.clock.setFont(QFont('Open Sans Bold', 14, weight=QFont.Bold))
        self.clock.setFont(QFont('Open Sans Bold', 12))
        self.statusBar().addPermanentWidget(self.clock)
        #
        self.rearm = False
        config = self.config.get('config', None)
        ip = self.config.get('ip', None)
        if config is None or ip is None:
            self.logger.error("No Oscilloscopes defined")
            exit(-111)
        self.device = TectronixTDS(ip=ip, config=config)
        if self.device.connected:
            sel = self.device.config['SELect?'].split(';')
            v = sel[0] == '1'
            self.checkBox_1.setChecked(v)
            v = sel[1] == '1'
            self.checkBox_2.setChecked(v)
            v = sel[2] == '1'
            self.checkBox_3.setChecked(v)
            v = sel[3] == '1'
            self.checkBox_4.setChecked(v)
            v = self.device.config['CH1?'].split(';')[0]
            # v = self.device.send_command('CH1:SCAle?')
            self.lineEdit_11.setText(v)
            v = self.device.config['CH2?'].split(';')[0]
            # v = self.device.send_command('CH2:SCAle?')
            self.lineEdit_12.setText(v)
            v = self.device.config['CH3?'].split(';')[0]
            # v = self.device.send_command('CH3:SCAle?')
            self.lineEdit_13.setText(v)
            v = self.device.config['CH4?'].split(';')[0]
            # v = self.device.send_command('CH4:SCAle?')
            self.lineEdit_14.setText(v)
            v = self.device.send_command('HORizontal:MAIn:SCAle?')
            self.lineEdit_15.setText(v)
        else:
            self.logger.info("Oscilloscope is not connected")
            # exit(-112)
        # Connect signals with slots
        self.pushButton.clicked.connect(self.erase)
        self.comboBox.currentIndexChanged.connect(self.processing_changed)
        # self.listWidget.itemSelectionChanged.connect(self.list_selection_changed)
        self.pushButton_2.clicked.connect(self.select_folder)
        self.comboBox_2.currentIndexChanged.connect(self.folder_changed)

        self.pushButton_3.clicked.connect(self.send_command_pressed)

        self.checkBox_1.clicked.connect(self.ch1_clicked)
        self.checkBox_2.clicked.connect(self.ch2_clicked)
        self.checkBox_3.clicked.connect(self.ch3_clicked)
        self.checkBox_4.clicked.connect(self.ch4_clicked)
        self.lineEdit_11.editingFinished.connect(self.ch1_scale_changed)
        self.lineEdit_12.editingFinished.connect(self.ch2_scale_changed)
        self.lineEdit_13.editingFinished.connect(self.ch3_scale_changed)
        self.lineEdit_14.editingFinished.connect(self.ch4_scale_changed)

        self.lineEdit_15.editingFinished.connect(self.horiz_scale_changed)

        self.pushButton_5.clicked.connect(self.force_trigger_pressed)
        self.pushButton_6.clicked.connect(self.single_seq_pressed)

        self.pushButton_4.toggled.connect(self.run_toggled)
        #
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

        # x = numpy.linspace(0.0, 4. * numpy.pi, 1000)
        # y = numpy.sin(x)
        # self.plotWidget = pyqtgraph.PlotWidget(parent=self.frame_3)
        # self.frame_3.layout().addWidget(self.plotWidget)
        # # self.plotWidget.getViewBox().setBackgroundColor('k')
        # self.plotWidget.getViewBox().setBackgroundColor('#1d648da0')
        # # font = QFont('Open Sans', 14, weight=QFont.Bold)
        # font = QFont('Open Sans', 16)
        # self.plotWidget.getPlotItem().getAxis("bottom").setTickFont(font)
        # self.plotWidget.getPlotItem().getAxis("bottom").setStyle(tickTextOffset=16)
        # self.plotWidget.getPlotItem().getAxis("left").setTickFont(font)
        # self.plotWidget.getPlotItem().showGrid(True, True)
        # self.plotWidget.getPlotItem().getAxis("bottom").label.setFont(font)
        # self.plotWidget.getPlotItem().setLabel('bottom', 'Time', units='s')
        # self.plotWidget.getPlotItem().getAxis("left").label.setFont(font)
        # # self.plotWidget.getPlotItem().getAxis("left").setStyle(tickTextWidth=320, tickTextHeight=320)
        # self.plotWidget.getPlotItem().setLabel('left', 'Signal', units='div')
        # self.plotWidget.plot(x, y, pen={'color': 'g', 'width': 2})
        # self.plot = self.plotWidget.plot

    def erase(self):
        self.mplw.canvas.ax.clear()
        ###self.list_selection_changed()
        # self.mplw.canvas.draw()

    def send_command_pressed(self):
        txt = self.lineEdit_2.text()
        t0 = time.time()
        self.device.send_command(txt)
        dt = time.time() - t0
        self.label_11.setText("%5.3f" % dt)
        self.lineEdit_3.setText(str(self.device.response[0]))
        # self.label_6.setText(self.device.response[0])

    def force_trigger_pressed(self):
        self.device.send_command('TRIG FORC')

    def horiz_scale_changed(self):
        v = self.lineEdit_15.text()
        self.device.send_command('HORizontal:MAIn:SCAle ' + str(v))
        v = self.device.send_command('HORizontal:MAIn:SCAle?')
        self.lineEdit_15.blockSignals(True)
        self.lineEdit_15.setText(v)
        self.lineEdit_15.blockSignals(False)

    def ch1_scale_changed(self):
        v = self.lineEdit_11.text()
        self.device.send_command('CH1:SCAle ' + str(v))
        v = self.device.send_command('CH1:SCAle?')
        self.lineEdit_11.blockSignals(True)
        self.lineEdit_11.setText(v)
        self.lineEdit_11.blockSignals(False)

    def ch2_scale_changed(self):
        v = self.lineEdit_12.text()
        self.device.send_command('CH2:SCAle ' + str(v))
        v = self.device.send_command('CH2:SCAle?')
        self.lineEdit_12.blockSignals(True)
        self.lineEdit_12.setText(v)
        self.lineEdit_12.blockSignals(False)

    def ch3_scale_changed(self):
        v = self.lineEdit_13.text()
        self.device.send_command('CH3:SCAle ' + str(v))
        v = self.device.send_command('CH3:SCAle?')
        self.lineEdit_13.blockSignals(True)
        self.lineEdit_13.setText(v)
        self.lineEdit_13.blockSignals(False)

    def ch4_scale_changed(self):
        v = self.lineEdit_12.text()
        self.device.send_command('CH4:SCAle ' + str(v))
        v = self.device.send_command('CH4:SCAle?')
        self.lineEdit_14.blockSignals(True)
        self.lineEdit_14.setText(v)
        self.lineEdit_14.blockSignals(False)

    def ch1_clicked(self):
        if self.checkBox_1.isChecked():
            self.device.send_command('SELect:CH1 1')
        else:
            self.device.send_command('SELect:CH1 0')

    def ch2_clicked(self):
        if self.checkBox_2.isChecked():
            self.device.send_command('SELect:CH2 1')
        else:
            self.device.send_command('SELect:CH2 0')

    def ch3_clicked(self):
        if self.checkBox_3.isChecked():
            self.device.send_command('SELect:CH3 1')
        else:
            self.device.send_command('SELect:CH3 0')

    def ch4_clicked(self):
        if self.checkBox_4.isChecked():
            self.device.send_command('SELect:CH4 1')
        else:
            self.device.send_command('SELect:CH4 0')

    def turn_red(self):
        self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: red;}')

    def turn_green(self):
        self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: green;}')

    def run_toggled(self):
        if self.pushButton_4.isChecked():
            self.device.start_aq()
            self.pushButton_4.setText('Stop')
            self.turn_green()
            # self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: green;}')
            self.rearm = True
        else:
            self.device.stop_aq()
            self.pushButton_4.setText('Run')
            self.turn_red()
            self.rearm = False

    def single_seq_pressed(self):
        self.device.stop_aq()
        if self.device.start_aq():
            self.turn_green()
            self.rearm = False
        else:
            self.turn_ref()

    def plot_data(self, data):
        # self.logger.debug('Entry')
        colors = ['y', 'c', 'm', 'g']
        if self.checkBox.isChecked():
            self.erase()
        axes = self.mplw.canvas.ax
        # axes.grid(color='k', linestyle='--')
        axes.set_title('Data from ' + self.folder)
        for i in data:
            self.plot_trace(data[i], color=colors[i - 1])
        # axes.legend()
        self.mplw.canvas.draw()

    def plot_trace(self, trace, color='w'):
        axes = self.mplw.canvas.ax
        x = trace['x']
        y = trace['y']
        p = trace['pos']
        if self.comboBox.currentIndex() == 0:
            axes.set_xlabel('Time, s')
            axes.set_ylabel('Signal, div')
            axes.plot(x, y, color=color)
            dx = x[1] - x[0]
            axes.plot(x[0] * 2 - x[0:2] - 150 * dx, [p, p], color=color, symbol='t2',
                      symbolPen={'color': color, 'width': 3})
            return
        if self.comboBox.currentIndex() == 1:
            fy = numpy.fft.rfft(y)
            fx = numpy.arange(len(fy)) / len(y) / (x[1] - x[0])
            fp = numpy.abs(fy) ** 2
            fp[0] = 0.0
            axes.set_xlabel('Frequency, Hz')
            axes.set_ylabel('Spectral Power, a.u.')
            axes.plot(fx, fp)
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
            axes.plot(fx, pf)
        else:
            evalsrt = ''
            try:
                axes.set_xlabel('X value, a.u.')
                axes.set_ylabel('Processed Signal, a.u.')
                evalsrt = self.comboBox.currentText()
                (xp, yp) = eval(evalsrt)
                axes.plot(xp, yp)
            except:
                self.logger.warning('eval() ERROR in %s' % evalsrt)

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME +
                                ' Version ' + APPLICATION_VERSION +
                                '\nTextronix oscilloscope control utility.', QMessageBox.Ok)

    def on_quit(self):
        # Save global settings
        save_settings(self, file_name=CONFIG_FILE,
                      widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2, self.checkBox))
        timer.stop()
        self.device.connection.close()

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        plots = {}
        if self.device.is_armed():
            self.turn_green()
        else:
            self.turn_red()
        if self.device.is_aq_finished():
            if self.device.connected:
                plots = self.device.read_plots()
                self.save_isf(plots)
                self.save_png()
                if self.rearm:
                    self.device.start_aq()
            p = {}
            for i in plots:
                p = plots[i]
                s = float(p['h']['wfid'].split(',')[2].replace('V/div', ''))
                p['scale'] = s
                p['pos'] = float(self.device.send_command('CH%s:POSition?' % i))
            axes = self.mplw.canvas.ax
            axes.set_yrange(-5.0, 5.0)
            p = {}
            for i in plots:
                p = plots[i]
                p['y'] /= p['scale']
                p['y'] += p['pos']
            self.plot_data(plots)
            colors = ['y', 'c', 'm', 'g']
            try:
                sou = self.device.send_command('TRIG:A:EDG:SOU?')
                i = int(sou[2])
                clr = colors[i-1]
            except KeyboardInterrupt:
                raise
            except:
                clr = 'w'
            if 'x' in p:
                x = p['x'][int(len(p['x'])/2)]
                axes.plot([x,x], [-5.0, 5.0], color=clr, symbol='t1', width=3, symbolPen={'color': clr, 'width': 3})

    def save_png(self):
        png, data = self.device.get_image()
        file_name = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '.png'
        fn = os.path.join(self.out_dir, file_name)
        with open(fn, 'wb') as fid:
            fid.write(data)
        self.logger.debug("png file saved to %s", fn)

    def save_isf(self, plots):
        for i in plots:
            file_name = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S') + '-CH%s.isf' % i
            fn = os.path.join(self.out_dir, file_name)
            isf = plots[i]['isf']
            with open(fn, 'wb') as fid:
                fid.write(isf)
            self.logger.debug("isf file saved to %s", fn)

    def select_folder(self):
        """Opens a file select dialog"""
        # Define current dir
        if self.folder is None:
            self.folder = "./"
        dialog = QFileDialog(self, caption='Select folder', directory=self.folder)
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
