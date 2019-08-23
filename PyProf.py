# coding: utf-8
'''
Created on Jul 28, 2019

@author: sanin
'''

import os
import os.path
import sys
import json
import logging
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
from PyQt5 import QtNetwork

import numpy
import scipy
from scipy import stats
from scipy import optimize
from scipy.interpolate import UnivariateSpline
from scipy.interpolate import LSQUnivariateSpline
from mplwidget import MplWidget
import matplotlib

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.widgets import RectangleSelector

from PIL import Image, ImageDraw

from widgetstate import set_state, get_state
from smooth import smooth
from isfread import isfread
import conf

ORGANIZATION_NAME = 'BINP'
APPLICATION_NAME = 'PyProf'
APPLICATION_NAME_SHORT = APPLICATION_NAME
APPLICATION_VERSION = '0_1'
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

# Global configuration dictionary

CONFIG = conf.CONFIG


def gauss(x, ampl, cent, sigma):
    return ampl*(1.0/(sigma*(numpy.sqrt(2.0*numpy.pi))))*(numpy.exp(-((x - cent) ** 2) / ((2.0 * sigma) ** 2)))


def lorentz(x, amp, cen, wid):
    return (amp*wid**2/((x-cen)**2+wid**2))\


def drawBox(ax, box, color=0, width=5):
    ax.plot((box[0],box[0],box[2],box[2],box[0]),(box[1],box[3],box[3],box[1],box[1]))
    pass


def profile(arr, box):
    # calculate profile
    prof = numpy.zeros(box[3] - box[1])
    for m in range(box[1], box[3]):
        prof[m - box[1]] = arr[m, box[0]:box[2]].mean()
    return prof


def profile_param(y, level=0.5):
    ymin = y.min()
    ymax = y.max()
    xmax = y.argmax()
    # scale y
    ys = (y - ymin) / (ymax - ymin)
    # FWHM = v.sum()
    v = ys > level
    return ymin, ymax, xmax, v.sum(), v


def fwhm(y, level = 0.5):
    return profile_param(y, level)[3]


def background(p, level=0.5):
    n = len(p)
    x = numpy.arange(n)
    try:
        # calculate profile characteristics
        _, _, xmax, w, _ = profile_param(p, level)
        w1 = xmax - 2.0*w
        w1 = max(w1, 1)
        w2 = xmax + 2.0*w
        w2 = min(w2, n-1)
        # everything outside +- 2*w is background ( p[k] )
        k = numpy.logical_or(x < w1, x > w2)
        # interpolate background with spline fit
        t = [1]
        t.extend(range(5, int(w1), 10))
        t.extend(range(int(w2+1), n-1, 10))
        #t = [1, 20, w1-50, w2+50, 800, np-1]
        spl = LSQUnivariateSpline(x[k], p[k], t)
        return spl(x)
    except:
        logger.error("Fitting exception ", exc_info=True)
        return x * 0.0


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
        # self.mplw.ntb.setIconSize(QSize(18, 18))
        # self.mplw.ntb.setFixedSize(300, 24)
        layout = self.frame_3.layout()
        layout.addWidget(self.mplw)
        axes = self.mplw.canvas.ax

        # Class members definition
        self.folder = None
        self.files = []

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
        # Clock at status bar
        self.clock = QLabel(" ")
        self.clock.setFont(QFont('Open Sans Bold', 12))
        self.statusBar().addPermanentWidget(self.clock)

        print(APPLICATION_NAME + ' version ' + APPLICATION_VERSION + ' started')

        self.restore_settings()

    def read_folder(self, folder):
        print('read_folder')
        self.erase()
        # All files in the folder
        files = os.listdir(folder)
        # Filter *.isf files
        self.files = [f for f in files if f.endswith('.tiff')]
        print(self.files)
        self.listWidget.blockSignals(True)
        self.listWidget.setUpdatesEnabled(False)
        self.listWidget.clear()
        self.listWidget.addItems(self.files)
        self.listWidget.blockSignals(False)
        self.listWidget.setUpdatesEnabled(True)
        if len(self.files) > 0:
            print('selesct 0')
            self.listWidget.item(0).setSelected(True)

    def erase(self):
        print('erase')
        self.mplw.canvas.ax.clear()
        ####self.list_selection_changed()
        #self.mplw.canvas.draw()

    def list_selection_changed(self):
        print('list_selection_changed')
        # Scale for pixel size
        xscale = 20.0 / 216.0  # mm/pixel
        # dpi for images
        dpi = 100
        # Left and right limits
        x1 = 200
        x2 = 1000
        # number of slices for beam angle calculation
        nx = 10
        dx = int((x2 - x1) / nx)
        mx = numpy.zeros(nx)
        my = numpy.zeros(nx)
        mw = numpy.zeros(nx)
        ma = numpy.zeros(nx)

        axes = self.mplw.canvas.ax
        if self.checkBox.isChecked():
            self.erase()
        #axes.grid(color='k', linestyle='--')
        axes.set_title(self.folder)
        sel = self.listWidget.selectedItems()
        if len(sel) <= 0:
            return
        for item in sel:
            print(item.text())
            fn = os.path.join(self.folder, item.text())
            img = Image.open(fn)
            print(img.size)
            # Convert image to numpy array
            arr = numpy.array(img)
            xs = arr.shape[1]
            ys = arr.shape[0]
            #print(arr.shape, arr.dtype)
            X = numpy.arange(xs)
            x = numpy.arange(ys)
            mp = numpy.zeros((nx, ys))
            # set selection box and title
            box = (500, 0, 800, ys)
            if self.comboBox.currentIndex() == 0:
                # Plot image
                axes.imshow(arr, aspect='equal', cmap='gray')
            elif self.comboBox.currentIndex() == 1:
                # Plot raw profile
                axes.set_xlabel('X, pixels')
                axes.set_ylabel('Signal, quanta')
                axes.set_title('Raw Profile')
                p = profile(arr, box)
                axes.plot(x, p)
                ymax, ymin, xmax, w, v = profile_param(p)
                # Plot line at half mximum
                axes.plot(x[v], 0.5 * (ymax + ymin) + p[v] * 0.0)
                axes.annotate("FWHM = %5.2f mm; %i pixels" % (w * xscale, w), (0.45, 0.9), xycoords='axes fraction')
                axes.annotate("Max = %5.2f at %5.2f mm; %i pixels" % (p[xmax], xmax * xscale, xmax), (0.45, 0.8),
                            xycoords='axes fraction')
                # Plot background
                axes.plot(x, background(p))
            elif self.comboBox.currentIndex() == 2:
                # Profile with subtracted background
                axes.set_title('Background subtracted')
                axes.set_xlabel('X, pixels')
                axes.set_ylabel('Signal, quanta')
                p1 = p - background(p)
                axes.plot(x, p1)
                ymax, ymin, xmax, w, v = profile_param(p1)
                axes.plot(x[v], 0.5 * (ymax + ymin) + p1[v] * 0.0)
                axes.annotate("FWHM = %5.2f mm; %i pixels" % (w * xscale, w), (0.45, 0.9), xycoords='axes fraction')
                axes.annotate("Max = %5.2f at %5.2f mm; %i pixels" % (p1[xmax], xmax * xscale, xmax), (0.45, 0.8),
                             xycoords='axes fraction')
                # Calculate gaussian and lorentzian fitting
                try:
                    popt_gauss, pcov_gauss = scipy.optimize.curve_fit(gauss, x[v], p1[v], p0=[p1[xmax], xmax, w])
                    popt_lorentz, pcov_lorentz = scipy.optimize.curve_fit(lorentz, x[v], p1[v], p0=[p1[xmax], xmax, w])
                    # perr_gauss = numpy.sqrt(numpy.diag(pcov_gauss))
                    ygf = gauss(x, *popt_gauss)
                    ylf = lorentz(x, *popt_lorentz)
                    # plot fitting profiles
                    axes.plot(x, ygf)
                    axes.plot(x, ylf)
                except:
                    logger.error("Fitting exception ", exc_info=True)
            elif self.comboBox.currentIndex() == 3:
                # Beam tilt and widths dependence on X
                for m in range(nx):
                    box = (x1 + dx * m, 0, x1 + dx * (m + 1) - 1, ys)
                    # Calculate profile
                    p = profile(arr, box)
                    # Subtract background
                    p = p - background(p)
                    mp[m, :] = p
                    # calculate gaussian (lorentzian) fitting
                    ymax, ymin, xmax, w, v = profile_param(p)
                    popt_gauss = [ymax, xmax, w]
                    pf = p
                    try:
                        popt_gauss, pcov_gauss = scipy.optimize.curve_fit(gauss, x[v], p[v], p0=[ymax, xmax, w])
                        # popt_lorentz, pcov_lorentz = scipy.optimize.curve_fit(lorentz, x[v], y[v], p0=[ymax, xmax, w[m]])
                        pf = gauss(x, *popt_gauss)
                        # plot profile
                        # ax4.plot(x, pf)
                    except:
                        logger.error("Exception ", exc_info=True)
                    mx[m] = (box[0] + box[2]) / 2.0
                    ma[m] = popt_gauss[0]
                    my[m] = popt_gauss[1]
                    mw[m] = popt_gauss[2]
                # Tilt of the beam
                slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(mx, my)
                # print("Angle %5.2f deg" % (slope/numpy.pi*180.))
                axes.plot(mx, my, '.')
                axes.plot(X, slope * X + intercept)
                axes.annotate("Angle = %5.2f deg" % (slope / numpy.pi * 180.), (0.55, 0.8), xycoords='axes fraction',
                             color='white')

                # Remove tilt
                rotated = img.rotate(slope / numpy.pi * 180.)
                arr2 = numpy.array(rotated)
                # imgplot2 = ax4.imshow(arr2, aspect='equal', cmap='gray')

                axes.clear()
                axes.set_xlabel('X, pixels')
                axes.set_ylabel('HWFM, pixels')
                axes.set_title('Width over X')
                axes.plot(mx, mw, 'o--')
                axes.set_ylim(bottom=0.0)

                #print("%3d %10s FWHM = %5.2f mm MAX = %5.2f at %5.2f mm Angle = %5.2f deg" % (n,
                #      tfiles[n], w * xscale,
                #      p[xmax], xmax * xscale,
                #      slope / numpy.pi * 180.))

        #axes.legend()
        self.mplw.canvas.draw()

    def show_about(self):
        QMessageBox.information(self, 'About', APPLICATION_NAME + ' Version ' + APPLICATION_VERSION +
                                '\nUser interface programm to control Negative Ion Source stand.', QMessageBox.Ok)

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

    def select_folder(self):
        print('select_folder')
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
        print('folder_changed')
        folder = self.comboBox_2.currentText()
        self.folder = folder
        self.read_folder(self.folder)

    def processing_changed(self, m):
        print('processing_changed')
        self.erase()
        #self.list_selection_changed()


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
