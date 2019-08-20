import os

import numpy

import matplotlib.pyplot as plt

import logging

from smooth import smooth
from isfread import isfread

# configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                                  datefmt='%H:%M:%S')
console_handler = logging.StreamHandler()
# self.console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.FATAL)

folder = '.\\'
# All files in the folder
files = os.listdir(folder)
# Filter tiff files without 'calibr' in the name
isffiles = [f for f in files if f.endswith('.isf')]

# window position and size
wx = 50
wy = 50
wdx = 1200
wdy = 800
# dpi for images
dpi = 100

# define figure with two axes
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, dpi=dpi, figsize=[wdx/dpi, wdy/dpi])
# set window size and position
mngr = plt.get_current_fig_manager()
mngr.window.setGeometry(wx, wy, wdx, wdy)
ax1.clear()
ax2.clear()

f1 = 5e4
f2 = 2e6
f3 = 6e6
f4 = 14e6
fbands = [(f1, f2), (f3, f4), (5e4, 5e7)]

def in_range(y, f, f1, f2):
    n = float(len(y))
    index = numpy.logical_and(f > f1, f < f2)
    s = y[index].sum()
    result = numpy.sqrt(s) / n * 2.0 / 100.0 * 1000.0
    return result

with open('list.txt', 'w') as listfile:
    print('{:<17s}; {:<17s}; '.format('File', 'Current, mA'), end='')
    for b in fbands:
        print('[mA] > {:<8.1e} '.format(b[0]), end='')
        print('< {:<8.1e} Hz; '.format(b[1]), end='')
    print('')
    listfile.write('{:<17s}; {:<17s}; '.format('File', 'Current, mA'))
    for b in fbands:
        listfile.write('[mA] > {:<8.1e} '.format(b[0]))
        listfile.write('< {:<8.1e} Hz; '.format(b[1]))
    listfile.write('\n'.format(b[1]))

    for fn in isffiles:
        print('{:<17s}; '.format(fn), end='')
        listfile.write('{:<17s}; '.format(fn))
        x,y,head = isfread(fn)
        #x = numpy.arange(0.0, 100., 0.01)
        #y = 7.0 + numpy.sin(2.0*numpy.pi*x)*2.0 + numpy.sin(2.0*numpy.pi*2.0*x)*3.0 + numpy.sin(2.0*numpy.pi*20.0*x)*5.0
        n = float(len(y))
        # Plot signal to ax1
        ax1.clear()
        ax1.set_xlabel('Time, s')
        ax1.set_ylabel('Signal, V')
        ax1.set_title('Track. File: ' + fn)
        ax1.grid(color='k', linestyle='--')
        ax1.plot(x, y)
        fy = numpy.fft.rfft(y)
        fx = numpy.arange(len(fy)) / n / (x[1]-x[0])
        fp = numpy.abs(fy)**2
        zero = fp[0]
        fp[0] = 0.0
        # Plot Fourier spectrum to ax2
        ax2.clear()
        ax2.set_title('Fourier Spectrum ')
        ax2.set_xlabel('Frequency, Hz')
        ax2.set_ylabel('Power Spectrum, a.u.')
        #ax2.semilogy()
        ax2.plot(fx, smooth(fp, window_len=1))
        ax2.grid(color='k', linestyle='--')
        current = numpy.sqrt(zero)/n/100.0*1000.0
        print('{:<10.2f}; '.format(current), end='')
        listfile.write('{:<10.2f}; '.format(current))
        for b in fbands:
            ap = in_range(fp, fx, b[0], b[1])
            print('{:<10.2f}; '.format(ap), end='')
            listfile.write('{:<10.2f}; '.format(ap))
        print('')
        listfile.write('\n')
        pf = fp * 0.0
        pf[-1] = fp[-1]
        for i in range(fx.size-2, -1, -1):
            pf[i] = pf[i+1] + fp[i]
        ax3.clear()
        ax3.set_title('Cumulative Noise Power')
        ax3.set_xlabel('Frequency, Hz')
        ax3.set_ylabel('Noise Power, a.u.')
        ax3.grid(color='k', linestyle='--')
        ax3.plot(fx, pf)
        ax4.clear()
        ax3.set_title('Normalized Cumulative Noise Power')
        ax4.set_xlabel('Frequency, Hz')
        ax4.set_ylabel('Noise Power Cumulative, a.u.')
        ax4.plot(fx, pf/pf[1])
        ax4.grid(color='k', linestyle='--')
        plt.tight_layout()
        #plt.show()
        #plt.show(block=False)
        plt.savefig(fn.replace(".isf", '.png'))
        #input('PAK')
    #plt.show()

if __name__ == "__main__":

    ##filein = sys.argv[1]
    x, v, head = isfread('getwfm (19).isf')

#    print(head)
#    for i in range(len(x)):
#        print('%g %g' % (x[i], v[i]))
