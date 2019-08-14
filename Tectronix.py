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
wdy = 600
# dpi for images
dpi = 100

# define figure with two axes
fig, (ax1, ax2) = plt.subplots(1, 2, dpi=dpi, figsize=[wdx/dpi, wdy/dpi])
# set window size and position
mngr = plt.get_current_fig_manager()
mngr.window.setGeometry(wx, wy, wdx, wdy)
ax1.clear()
ax2.clear()

listfile = open('list.txt', 'w')

print('{:<17s}'.format('File'), end='; ')
listfile.write('{:<17s}; '.format('File'))
fr = [5e4, 5e6]
f1 = 5e4
f2 = 5e6
print('> {:<8.1e}'.format(f1), end='; ')
listfile.write('> {:<8.1e}; '.format(f1))
print('> {:<8.1e}'.format(f2))
listfile.write('> {:<8.1e}\n'.format(f2))

for f in isffiles:
    print('{:<17s}'.format(f), end='; ')
    listfile.write('{:<17s}; '.format(f))
    x,y,head = isfread(f)
    #x = numpy.arange(0.0, 100., 0.01)
    #y = numpy.sin(2.0*numpy.pi*x) + numpy.sin(2.0*numpy.pi*2.0*x) + numpy.sin(2.0*numpy.pi*20.0*x)
    # Plot signal to ax1
    ax1.clear()
    ax1.set_xlabel('Time, s')
    ax1.set_ylabel('Signal, V')
    ax1.set_title('File: ' + f)
    ax1.plot(x, y)
    fy = numpy.fft.rfft(y)
    fx = numpy.arange(len(fy)) / len(y) / (x[1]-x[0])
    # Plot Fourier spectrum to ax2
    ax2.clear()
    ax2.set_title('File: ' + f)
    ax2.set_xlabel('Frequency, Hz')
    ax2.set_ylabel('Power Spectrum, a.u.')
    ax2.plot(fx[1:], smooth(numpy.abs(fy)[1:]**2, window_len=1)[0:5000])
    plt.show(block=False)
    plt.savefig(f.replace(".isf", '.png'))
    #input('PAK')
    index = fx > f1
    np = (numpy.abs(fy)[index]**2).sum()
    print('{:<10.1e}'.format(np), end='; ')
    listfile.write('{:<10.1e}; '.format(np))
    index1 = fx > f2
    np1 = (numpy.abs(fy)[index1] ** 2).sum()
    print('{:<10.1e}'.format(np1))
    listfile.write('{:<10.1e}\n'.format(np1))
#plt.show()
listfile.close()





if __name__ == "__main__":

    ##filein = sys.argv[1]
    x, v, head = isfread('getwfm (19).isf')

#    print(head)
#    for i in range(len(x)):
#        print('%g %g' % (x[i], v[i]))
