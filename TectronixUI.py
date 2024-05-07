# coding: utf-8
"""
Created on Aug 23, 2023

@author: sanin

s='s=%r;print(s%%s)';print(s%s)
"""
import collections
import datetime
import os.path
import sys
import time

import numpy
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

import utils

from Tectronix import TectronixTDS
from QtUtils import restore_settings, save_settings
from config_logger import config_logger
# from mplwidget import MplWidget
from pyqtgraphwidget import MplWidget
from smooth import smooth

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = os.path.basename(__file__).replace('.py', '')
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '4.1'
CONFIG_FILE = APPLICATION_NAME_SHORT + '.json'
UI_FILE = APPLICATION_NAME_SHORT + '.ui'

FALSE = [False, None, 'False', 'false', '0', '0.0', 0, 0.0]


class MainWindow(QMainWindow):
    PLOT_COLORS = ['y', 'c', 'm', 'g']
    FADED_COLORS = [(200, 200, 0), (0, 200, 200), (200, 0, 200), (0, 200, 0)]

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
                         widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2, self.checkBox,
                                  self.spinBox))
        # if self.comboBox.findText(self.folder) < 0:
        #     pass
        self.folder = self.config.get('folder', 'D:/tec_data')
        if self.comboBox_2.findText(self.folder) < 0:
            self.comboBox_2.insertItem(0, self.folder)
        self.out_dir = ''
        self.plots = {}
        self.prev_plots = {}
        self.history = self.deque = collections.deque(maxlen=100)
        self.history_index = 0
        self.make_data_folder()
        # Create new plot widget
        self.mplw = MplWidget()
        self.mplw.ntb.show()
        layout = self.frame_3.layout()
        layout.addWidget(self.mplw)
        self.mplw.getViewBox().setBackgroundColor('#1d648da0')
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
        #
        # Menu actions connection
        self.actionQuit.triggered.connect(qApp.quit)
        self.actionAbout.triggered.connect(self.show_about)
        # Clock at status bar
        self.clock = QLabel(" ")
        # self.clock.setFont(QFont('Open Sans Bold', 14, weight=QFont.Bold))
        self.clock.setFont(QFont('Open Sans Bold', 12))
        self.statusBar().setFont(QFont('Open Sans Bold', 12))
        self.statusBar().addPermanentWidget(self.clock)
        #
        self.rearm = False
        config = self.config.get('config', {})
        ip = self.config.get('ip', '192.168.1.222')
        if config is None or ip is None:
            self.logger.error("No Oscilloscopes defined")
            exit(-111)
        #
        # self.smooth = self.config.get('smooth', 1)
        # self.spinBox.setValue(self.smooth)
        # self.spinBox.valueChanged.connect(self.smooth_changed)
        reconnect_timeout = self.config.get('reconnect_timeout', 0.0)
        TectronixTDS.RECONNECT_TIMEOUT = reconnect_timeout
        timeout = self.config.get('timeout', 1.1)
        port = self.config.get('port', None)
        self.device = TectronixTDS(ip=ip, config=config, port=port, timeout=timeout)
        #
        if self.device.connected:
            self.read_config()
            self.config['ip'] = ip
        else:
            self.logger.info("Oscilloscope is not connected")
            # exit(-112)
        #
        self.trace_enable = {1: self.checkBox_12, 2: self.checkBox_11, 3: self.checkBox_14, 4: self.checkBox_13}
        # Connect signals with slots
        self.pushButton_7.clicked.connect(self.read_config)
        self.pushButton.clicked.connect(self.erase)
        self.comboBox.currentIndexChanged.connect(self.processing_changed)
        self.pushButton_2.clicked.connect(self.select_folder)
        self.comboBox_2.currentIndexChanged.connect(self.folder_changed)
        self.pushButton_3.clicked.connect(self.send_command_pressed)
        self.checkBox_1.clicked.connect(self.ch1_clicked)
        self.checkBox_2.clicked.connect(self.ch2_clicked)
        self.checkBox_3.clicked.connect(self.ch3_clicked)
        self.checkBox_4.clicked.connect(self.ch4_clicked)
        self.lineEdit_11.returnPressed.connect(self.ch1_scale_changed)
        self.lineEdit_12.returnPressed.connect(self.ch2_scale_changed)
        self.lineEdit_13.returnPressed.connect(self.ch3_scale_changed)
        self.lineEdit_14.returnPressed.connect(self.ch4_scale_changed)
        self.lineEdit_17.returnPressed.connect(self.ch1_position_changed)
        self.lineEdit_18.returnPressed.connect(self.ch2_position_changed)
        self.lineEdit_19.returnPressed.connect(self.ch3_position_changed)
        self.lineEdit_20.returnPressed.connect(self.ch4_position_changed)
        self.lineEdit_15.returnPressed.connect(self.horiz_scale_changed)
        self.lineEdit_16.returnPressed.connect(self.horiz_position_changed)
        self.pushButton_5.clicked.connect(self.force_trigger_pressed)
        self.pushButton_6.clicked.connect(self.single_seq_pressed)
        # self.pushButton_10.clicked.connect(self.prev_pressed)
        # self.pushButton_7.clicked.connect(self.next_pressed)
        self.pushButton_4.toggled.connect(self.run_toggled)
        self.pushButton_9.clicked.connect(self.send2_pressed)
        self.horizontalScrollBar.valueChanged.connect(self.scroll_action)
        self.checkBox_12.clicked.connect(self.enable_clicked)
        self.checkBox_11.clicked.connect(self.enable_clicked)
        self.checkBox_14.clicked.connect(self.enable_clicked)
        self.checkBox_13.clicked.connect(self.enable_clicked)
        #
        self.frame_6.hide()
        #
        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

    def read_config(self):
        if self.device.connected:
            sel = self.device.config['SELect?'].split(';')
            if sel[0] not in ['0', '1']:
                sel = sel[1:]
            v = sel[0] == '1'
            self.checkBox_1.setChecked(v)
            v = sel[1] == '1'
            self.checkBox_2.setChecked(v)
            v = sel[2] == '1'
            self.checkBox_3.setChecked(v)
            v = sel[3] == '1'
            self.checkBox_4.setChecked(v)
            self.update_widget(self.lineEdit_11, 'CH1:SCAle?', filter=self.float_filter)
            # v = self.device.send_command('CH1:SCAle?')
            # self.lineEdit_11.setText(v)
            self.update_widget(self.lineEdit_17, 'CH1:POSition?', filter=self.float_filter)
            # v = self.device.send_command('CH1:POSition?')
            # self.lineEdit_17.setText(v)
            # v = self.device.config['CH2?'].split(';')
            self.update_widget(self.lineEdit_12, 'CH2:SCAle?', filter=self.float_filter)
            # v = self.device.send_command('CH2:SCAle?')
            # self.lineEdit_12.setText(v)
            self.update_widget(self.lineEdit_18, 'CH2:POSition?', filter=self.float_filter)
            # v = self.device.send_command('CH2:POSition?')
            # self.lineEdit_18.setText(v)
            self.update_widget(self.lineEdit_13, 'CH3:SCAle?', filter=self.float_filter)
            # v = self.device.send_command('CH3:SCAle?')
            # self.lineEdit_13.setText(v)
            self.update_widget(self.lineEdit_19, 'CH3:POSition?', filter=self.float_filter)
            # v = self.device.send_command('CH3:POSition?')
            # self.lineEdit_19.setText(v)
            self.update_widget(self.lineEdit_14, 'CH4:SCAle?', filter=self.float_filter)
            # v = self.device.send_command('CH4:SCAle?')
            # self.lineEdit_14.setText(v)
            self.update_widget(self.lineEdit_20, 'CH4:POSition?', filter=self.float_filter)
            # v = self.device.send_command('CH4:POSition?')
            # self.lineEdit_20.setText(v)
            self.update_widget(self.lineEdit_15, 'HORizontal:MAIn:SCAle?', filter=self.float_filter)
            # v = self.device.send_command('HORizontal:MAIn:SCAle?')
            # self.lineEdit_15.setText(v)
            self.update_widget(self.lineEdit_16, 'HORizontal:TRIGger:POSition?', filter=self.float_filter)
            # v = self.device.send_command('HORizontal:TRIGger:POSition?')
            # self.lineEdit_16.setText(v)

    def erase(self):
        self.mplw.canvas.ax.clear()

    def send_command_pressed(self):
        txt = self.lineEdit_2.text()
        t0 = time.time()
        self.device.send_command(txt)
        dt = time.time() - t0
        self.label_11.setText("%5.3f" % dt)
        self.lineEdit_3.setText(str(self.device.response[0]))

    def send2_pressed(self):
        txt = self.comboBox_3.currentText()
        h = self.device.send_command('HEADer?')
        self.device._send_command('HEADer 1')
        self.device._send_command(txt)
        self.textEdit.setText(str(self.device.response[0]))
        if h == '0':
            self.device.send_command('HEADer 0')

    def force_trigger_pressed(self):
        self.device.send_command('TRIG FORC')

    def horiz_scale_changed(self):
        self.set_widget_float(self.lineEdit_15, 'HORizontal:MAIn:SCAle')

    # def smooth_changed(self):
    #     self.smooth = self.spinBox.value()

    def horiz_position_changed(self):
        self.set_widget_float(self.lineEdit_16, 'HORizontal:TRIGger:POSition')

    def ch1_position_changed(self):
        self.set_widget_float(self.lineEdit_17, 'CH1:POS')

    def ch2_position_changed(self):
        self.set_widget_float(self.lineEdit_18, 'CH2:POS')

    def ch3_position_changed(self):
        self.set_widget_float(self.lineEdit_19, 'CH3:POS')

    def ch4_position_changed(self):
        self.set_widget_float(self.lineEdit_20, 'CH4:POS')

    def ch1_scale_changed(self):
        self.set_widget_float(self.lineEdit_11, 'CH1:SCAle')

    def ch2_scale_changed(self):
        self.set_widget_float(self.lineEdit_12, 'CH2:SCAle')

    def ch3_scale_changed(self):
        self.set_widget_float(self.lineEdit_13, 'CH3:SCAle')

    def ch4_scale_changed(self):
        self.set_widget_float(self.lineEdit_14, 'CH4:SCAle')

    def update_widget(self, widget, command, function=None, filter=None):
        v = self.device.send_command(command)
        if v is None:
            return
        if filter is not None:
            v = filter(v)
        widget.blockSignals(True)
        if function is not None:
            if hasattr(widget, function):
                attr = getattr(widget, function)
                attr(v)
        else:
            if hasattr(widget, 'setChecked'):
                widget.setChecked(v not in FALSE)
            elif hasattr(widget, 'setValue'):
                widget.setValue(v)
            elif hasattr(widget, 'setText'):
                widget.setText(v)
        widget.blockSignals(False)

    def set_widget_float(self, widget, command):
        v = ''
        if hasattr(widget, 'value'):
            v = widget.value()
        elif hasattr(widget, 'text'):
            v = widget.text()
        v = str(v)
        try:
            f = float(v)
            if self.device.send_command(command + ' ' + v) is None:
                return
            self.update_widget(widget, command + '?', filter=self.float_filter)
        except ValueError:
            return

    def float_filter(self, v):
        try:
            s = '%5.3g' % float(v)
            return s
            # while '0e' in s:
            #     s = s.replace('0e', 'e')
            # s = s.replace('.e', 'e')
            # while 'e+0' in s:
            #     s = s.replace('e+0', 'e+')
            # while 'e-0' in s:
            #     s = s.replace('e-0', 'e-')
            # if s.endswith('e-'):
            #     s = s.replace('e-', '')
            # if s.endswith('e+'):
            #     s = s.replace('e+', '')
            # if s.endswith('.'):
            #     s = s.replace('.', '.0')
            # return s
        except ValueError:
            return "???"

    def ch1_clicked(self):
        if self.checkBox_1.isChecked():
            self.device.send_command('SELect:CH1 1')
        else:
            self.device.send_command('SELect:CH1 0')
        self.update_widget(self.checkBox_1, 'SELect:CH1?')

    def ch2_clicked(self):
        if self.checkBox_2.isChecked():
            self.device.send_command('SELect:CH2 1')
        else:
            self.device.send_command('SELect:CH2 0')
        self.update_widget(self.checkBox_2, 'SELect:CH2?')

    def ch3_clicked(self):
        if self.checkBox_3.isChecked():
            self.device.send_command('SELect:CH3 1')
        else:
            self.device.send_command('SELect:CH3 0')
        self.update_widget(self.checkBox_3, 'SELect:CH3?')

    def ch4_clicked(self):
        if self.checkBox_4.isChecked():
            self.device.send_command('SELect:CH4 1')
        else:
            self.device.send_command('SELect:CH4 0')
        self.update_widget(self.checkBox_4, 'SELect:CH4?')

    def turn_color(self, widget, color='white'):
        widget.setStyleSheet('QCheckBox::indicator:unchecked {background-color: %s;}' % color)

    def turn_red(self):
        self.turn_color(self.checkBox_5, 'red')
        # self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: red;}')

    def turn_green(self):
        self.turn_color(self.checkBox_5, 'green')
        # self.checkBox_5.setStyleSheet('QCheckBox::indicator:unchecked {background-color: green;}')

    def run_toggled(self):
        if self.pushButton_4.isChecked():
            a = self.device.start_aq()
            self.pushButton_4.setText('Stop')
            if a:
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
            self.turn_red()

    def enable_clicked(self):
        self.plot_data()

    def scroll_action(self, n, colors=None):
        if colors is None:
            colors = self.FADED_COLORS
        if n >= len(self.history) - 1:
            colors = self.PLOT_COLORS
        data = self.history[n]
        for i in data:
            self.lineEdit_4.setText(data[i]['dts'])
            if self.trace_enable[i].isChecked():
                self.plot_trace(data[i], color=colors[i - 1])

    def plot_data(self, data=None, colors=None):
        if data is None:
            data = self.plots
        if colors is None:
            colors = self.PLOT_COLORS
        if self.checkBox.isChecked():
            self.erase()
        self.mplw.clearScaleHistory()
        axes = self.mplw.canvas.ax
        for i in data:
            lst = 'Last Shot: ' + data[i]['dts']
            axes.set_title(lst)
            if self.trace_enable[i].isChecked():
                self.plot_trace(data[i], color=colors[i - 1])
        # axes.legend()
        self.mplw.canvas.draw()

    def plot_trace(self, trace, color='w'):
        axes = self.mplw.canvas.ax
        n = self.spinBox.value()
        y = smooth(trace['y'], n)
        x = smooth(trace['x'], n)
        # y = trace['y']
        if self.comboBox.currentIndex() == 0:
            p = trace['pos']
            y = (trace['y'] / trace['scale']) + p
            axes.set_yrange(-5.0, 5.0)
            axes.set_xrange(x[0], x[-1])
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
            axes.plot(fx, fp, color=color)
            self.mplw.autoRange()
        elif self.comboBox.currentIndex() == 2:
            fy = numpy.power(10.0, 1.667 * y - 11.46)*133.0
            axes.set_xlabel('Time, s')
            axes.set_ylabel('Pressure, Pa')
            axes.plot(x, fy, color=color)
            self.mplw.autoRange()
        else:
            evalstr = ''
            try:
                axes.set_xlabel('X value, a.u.')
                axes.set_ylabel('Processed Signal, a.u.')
                evalstr = self.comboBox.currentText()
                if evalstr:
                    (xp, yp) = eval(evalstr)
                    axes.plot(xp, yp, color=color)
                    self.mplw.autoRange()
            except KeyboardInterrupt:
                raise
            except:
                self.logger.warning('eval() ERROR in %s' % evalstr)

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME +
                                ' Version ' + APPLICATION_VERSION +
                                '\nTectronix oscilloscope control utility.', QMessageBox.Ok)

    def on_quit(self):
        timer.stop()
        self.frame_6.hide()
        # Save global settings
        save_settings(self, file_name=CONFIG_FILE,
                      widgets=(self.comboBox, self.comboBox_2, self.lineEdit_2, self.checkBox,
                               self.spinBox))
        self.device.disconnect()

    def timer_handler(self):
        t = time.strftime('%H:%M:%S')
        self.clock.setText(t)
        st = self.device.send_command('TRIGger:STATE?')
        if st is None:
            return
        if st.startswith('READY'):
            self.turn_green()
        elif st.startswith('ARMED'):
            self.turn_color(self.checkBox_5, 'yellow')
        elif st.startswith('SAV'):
            self.turn_color(self.checkBox_5, 'red')
        elif st.startswith('TRIG'):
            self.turn_color(self.checkBox_5, 'blue')
        elif st.startswith('AUTO'):
            self.turn_color(self.checkBox_5, 'magenta')
        if self.device.is_aq_finished():
            t = time.time()
            dts = self.dts()
            dts2 = self.dts2()
            plots = {}
            if self.device.connected:
                plots = self.device.read_plots()
                if len(plots) > 0:
                    self.save_isf(plots, dts)
                self.save_png(dts)
                if self.rearm:
                    self.device.start_aq()
            for i in plots:
                p = plots[i]
                p['time'] = t
                p['dts'] = dts2
                p['pos'] = 0.0
                p['scale'] = 1.0
                try:
                    p['pos'] = float(self.device.send_command('CH%s:POSition?' % i))
                    p['scale'] = float(self.device.send_command('CH%s:SCALe?' % i))
                    # p['scale'] = float(p['h']['wfid'].split(',')[2].replace('V/div', ''))
                except KeyboardInterrupt:
                    raise
                except:
                    pass
            self.plots = plots
            if len(plots) > 0:
                self.history.append(plots)
                n = len(self.history)
                self.history_index = n - 1
                self.horizontalScrollBar.setMaximum(n - 1)
                self.horizontalScrollBar.setSliderPosition(n - 1)
            self.plot_data(plots)
            colors = ['y', 'c', 'm', 'g']
            try:
                sou = self.device.send_command('TRIG:A:EDGE:SOU?')
                i = int(sou[2])
                clr = colors[i - 1]
            except KeyboardInterrupt:
                raise
            except:
                clr = 'w'
            axes = self.mplw.canvas.ax
            axes.plot([0.0, 0.0], [-5.0, 5.0], color=clr, symbol='t1', width=3, symbolPen={'color': clr, 'width': 1})

    @staticmethod
    def dts():
        return datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')

    @staticmethod
    def dts2():
        return datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

    def save_png(self, dts=None):
        return
        data = self.device.get_image()
        if data is None:
            self.logger.info("Can not read image")
            return
        if dts is None:
            dts = self.dts()
        file_name = dts + '.png'
        fn = os.path.join(self.out_dir, file_name)
        with open(fn, 'wb') as fid:
            fid.write(data)
        self.logger.info("png file saved to %s", fn)

    def save_isf(self, plots, dts=None, chnls=None):
        if dts is None:
            dts = self.dts()
        for i in plots:
            if chnls is None or i in chnls:
                file_name = dts + '-CH%s.isf' % i
                fn = os.path.join(self.out_dir, file_name)
                isf = plots[i]['isf']
                with open(fn, 'wb') as fid:
                    fid.write(isf)
                self.logger.info("isf file saved to %s", fn)

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
        self.folder = folder
        self.make_data_folder()

    def processing_changed(self, m):
        self.erase()
        self.plot_data()

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
