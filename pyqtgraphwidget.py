# coding: utf-8
'''
Created on 16 april 2021
@author: Sanin
s='s=%r;print(s%%s)';print(s%s)
'''
import threading

import pyqtgraph
# import qtpy
# from qtpy.QtWidgets import QMenu
from PyQt5.QtWidgets import QMenu
from pyqtgraph.Qt import QtCore

# pg = pyqtgraph

# pyqtgraph.setConfigOption('background', '#1d648d')
pyqtgraph.setConfigOption('background', 'w')
pyqtgraph.setConfigOption('foreground', 'k')
# pyqtgraph.setConfigOption('antialias', True)
pyqtgraph.setConfigOption('leftButtonPan', False)


class CustomViewBox(pyqtgraph.ViewBox):
    MENU = ['Hide plot', 'Show new plot', 'Show plot (all)']
    def __init__(self, parent=None, *args, **kwds):
        super().__init__(parent, *args, **kwds)
        self.setMouseMode(self.RectMode)
        self.setBackgroundColor('#1d648da0')
        # self.setBorder(pen=('green', 5))
        self.my_menu = QMenu()
        # self.my_menu.setTitle("Double click test menu")
        # self.my_menu.addAction('Plot Info')
        # self.my_menu.addSeparator()
        self.my_menu.addAction(self.MENU[0])
        self.my_menu.addAction(self.MENU[1])
        self.my_menu.addSeparator()
        self.my_menu.addAction(self.MENU[2])

    # reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.double() and ev.button() == QtCore.Qt.LeftButton:
            ev.accept()
            # self.my_menu.popup(ev.screenPos().toPoint())
            action = self.my_menu.exec(ev.screenPos().toPoint())
            if action is None:
                return
            if action.text() == self.MENU[0]:
                self.mplw.my_action.hide_plot(self.mplw.my_name, self.mplw.my_index)
            elif action.text() == self.MENU[1]:
                self.mplw.my_action.show_plot(self.mplw.my_name, self.mplw.my_index)
            elif action.text() == self.MENU[2]:
                self.mplw.my_action.show_plot_on_right(self.mplw.my_name, self.mplw.my_index)
        elif ev.button() == QtCore.Qt.RightButton:
            ev.accept()
            if ev.double():
                self.timer.cancel()
                pyqtgraph.ViewBox.mouseClickEvent(self, ev)
            else:
                self.timer = threading.Timer(0.3, self.double_click_timer_handler)
                self.timer.start()
                # self.autoRange()

    def double_click_timer_handler(self):
        self.autoRange()
        return True

    def mouseDragEvent(self, ev, **kwargs):
        if ev.button() != QtCore.Qt.LeftButton:
            ev.accept()
            # ev.ignore()
        else:
            pyqtgraph.ViewBox.mouseDragEvent(self, ev, **kwargs)

    def wheelEvent(self, ev, axis=None):
        # print('wheel1')
        ev.ignore()
        # ev.accept()

    def clearScaleHistory(self):
        if len(self.axHistory) > 0:
            self.showAxRect(self.axHistory[0])
        self.axHistory = []  # maintain a history of zoom locations
        self.axHistoryPointer = -1  # pointer into the history. Allows forward/backward movement, not just "undo"
        # zoom = (s, s) if in_or_out == "in" else (1 / s, 1 / s)
        # self.plot.vb.scaleBy(zoom)

    def resetScaleHistory(self):
        if len(self.axHistory) > 0:
            self.showAxRect(self.axHistory[0])

    def action(self):
        print('action')


class MplWidget(pyqtgraph.PlotWidget):
    def __init__(self, parent=None, height=300, width=300):
        vb = CustomViewBox()
        vb.mplw = self
        super().__init__(parent, viewBox=vb)
        self.canvas = MplAdapter(self)
        self.canvas.ax = self.canvas
        self.ntb = ToolBar()
        self.setMinimumHeight(height)
        self.setMinimumWidth(width)
        self.getPlotItem().showGrid(True, True)
        # self.getPlotItem().getAxis('left').setBackgroundColor('w')
        # pyqtgraph.GridItem().setPen('k')

    def clearScaleHistory(self):
        self.getPlotItem().vb.clearScaleHistory()

    def wheelEvent(self, ev, axis=None):
        # print('wheel2')
        ev.ignore()
        # ev.accept()

    def mouseDragEvent(self, ev, **kwargs):
        ev.ignore()

    def mouseClickEvent(self, ev):
        ev.ignore()


class MplAdapter:
    def __init__(self, item):
        self.item = item
        # self.plot_item_count = 0
        # super().__init__()

    def grid(self, val=True):
        self.item.getPlotItem().showGrid(val, val)

    def set_title(self, val=''):
        self.item.getPlotItem().setTitle(val)

    def set_xlabel(self, val=''):
        self.item.setLabel('bottom', val)

    def set_ylabel(self, val=''):
        self.item.setLabel('left', val)
        pass

    def draw(self, val=''):
        pass

    def plot(self, x, y, color='#ffffff', width=1, symbol=None, **kwargs):
        self.item.plot(x, y, pen={'color': color, 'width': width}, symbol=symbol, **kwargs)
        # pci = pyqtgraph.PlotCurveItem(x, y, pen={'color': color, 'width': width})
        # self.item.addItem(pci)

    def clear(self):
        self.item.getPlotItem().vb.clearScaleHistory()
        self.item.clear()

    def clearScaleHistory(self):
        self.item.getPlotItem().vb.clearScaleHistory()


# empty plug class
class ToolBar:
    def __init__(self, *args):
        pass

    def hide(self, *args):
        pass

    def show(self, *args):
        pass

    def setIconSize(self, *args):
        pass

    def setFixedSize(self, *args):
        pass
