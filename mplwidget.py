# coding: utf-8
'''
Created on 31 мая 2017 г.

@author: Sanin
'''

# import matplotlib
# matplotlib.rcParams['path.simplify'] = True
# matplotlib.rcParams['path.simplify_threshold'] = 1.0
# import matplotlib.style as mplstyle
# mplstyle.use('fast')

from matplotlib.figure import Figure

# Python Qt4 or Qt5 bindings for GUI objects
try:
    from PyQt5 import QtWidgets as QtGui
    from matplotlib.backends.backend_qt5agg \
        import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg \
        import NavigationToolbar2QT as NavigationToolbar
except:
    from PyQt4 import QtGui
    from matplotlib.backends.backend_qt4agg \
        import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt4agg \
        import NavigationToolbar2QT as NavigationToolbar


# import the Qt4(5)Agg FigureCanvas object, that binds Figure to
# Qt4(5)Agg backend. It also inherits from QWidget
# Matplotlib Figure object
# import the NavigationToolbar Qt4(5)Agg widget

class MplCanvas(FigureCanvas):
    """Class to represent the FigureCanvas widget"""

    def __init__(self):
        # setup Matplotlib Figure and Axis
        self.fig = Figure()
        self.fig.set_tight_layout(True)
        # self.fig.set_constrained_layout(True)
        self.ax = self.fig.add_subplot(111)
        # initialization of the canvas
        FigureCanvas.__init__(self, self.fig)
        # we define the widget as expandable
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        # notify the system of updated policy
        FigureCanvas.updateGeometry(self)


class MplWidget(QtGui.QWidget):
    """Widget defined in Qt Designer"""

    def __init__(self, parent=None, height=300, width=300):
        # initialization of Qt MainWindow widget
        QtGui.QWidget.__init__(self, parent)
        # set the canvas to the Matplotlib widget
        self.canvas = MplCanvas()
        # create a vertical box layout
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.setSpacing(0)

        self.ntb = NavigationToolbar(self.canvas, parent)
        self.ntb.hide()
        self.vbl.addWidget(self.ntb)

        # add mpl widget to vertical box
        self.vbl.addWidget(self.canvas)
        # set the layout to the vertical box
        self.setLayout(self.vbl)
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
