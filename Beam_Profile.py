import os

import numpy as np
import scipy
from scipy import stats
from scipy import optimize
from scipy.interpolate import UnivariateSpline
from scipy.interpolate import LSQUnivariateSpline

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.widgets import RectangleSelector

from PIL import Image, ImageDraw

import logging


def gauss(x, ampl, cent, sigma):
    return ampl*(1.0/(sigma*(np.sqrt(2.0*np.pi))))*(np.exp(-((x - cent) ** 2) / ((2.0 * sigma) ** 2)))


def lorentz(x, amp, cen, wid):
    return (amp*wid**2/((x-cen)**2+wid**2))\


def drawBox(ax, box, color=0, width=5):
    ax.plot((box[0],box[0],box[2],box[2],box[0]),(box[1],box[3],box[3],box[1],box[1]))
    pass


def profile(arr, box):
    # calculate profile
    prof = np.zeros(box[3] - box[1])
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
    x = np.arange(n)
    try:
        # calculate profile characteristics
        _, _, xmax, w, _ = profile_param(p, level)
        w1 = xmax - 2.0*w
        w1 = max(w1, 1)
        w2 = xmax + 2.0*w
        w2 = min(w2, n-1)
        # everything outside +- 2*w is background ( p[k] )
        k = np.logical_or(x < w1, x > w2)
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
tfiles = [f for f in files if f.endswith('.tiff') and (f.find('calibr') < 0)]

# Scale for pixel size
xscale = 20.0/216.0 # mm/pixel

# window position and size
wx = 50
wy = 50
wdx = 1500
wdy = 1000
# dpi for images
dpi = 100

# Left and right limits
x1 = 200
x2 = 1000
# number of slices for beam angle calculation
nx = 10
dx = int((x2 - x1) / nx)
mx = np.zeros(nx)
my = np.zeros(nx)
mw = np.zeros(nx)
ma = np.zeros(nx)

# define figure with two axes
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, dpi=dpi, figsize=[wdx/dpi, wdy/dpi])
# set window size and position
mngr = plt.get_current_fig_manager()
mngr.window.setGeometry(wx, wy, wdx, wdy)

plt.show(block=False)

n = 0
nonstop = True
for f in tfiles:
    fn = folder + f
    img = Image.open(fn)
    #print(img.size)
    # convert image to numpy array
    arr = np.array(img)
    xs = arr.shape[1]
    ys = arr.shape[0]
    #print(arr.shape, arr.dtype)
    X = np.arange(xs)
    x = np.arange(ys)
    mp = np.zeros((nx, ys))

    # set selection box and title
    box = (500, 0, 800, ys)
    ax2title = 'profile, side view'
    if f.startswith('2'):
        box = (500, 0, 800, ys)
        ax2title = 'profile, top view'

    # Plot image to ax1
    ax1.clear()
    ax1.set_title('File: ' + f)
    imgplot = ax1.imshow(arr, aspect='equal', cmap='gray')

    # plot raw profile to ax2
    ax2.clear()
    ax2.set_xlabel('X, pixels')
    ax2.set_ylabel('Y, pixels')
    ax2.set_title('Raw ' + ax2title)
    ax2.set_xlabel('Y, pixels')
    ax2.set_ylabel('Signal, quanta')
    p = profile(arr, box)
    ax2.plot(x, p)
    ymax, ymin, xmax, w, v = profile_param(p)
    # Plot line at half mximum
    ax2.plot(x[v], 0.5*(ymax + ymin)+p[v]*0.0)
    ax2.annotate("FWHM = %5.2f mm; %i pixels"%(w*xscale, w), (0.45, 0.9), xycoords='axes fraction')
    ax2.annotate("Max = %5.2f at %5.2f mm; %i pixels"%(p[xmax], xmax*xscale, xmax), (0.45, 0.8), xycoords='axes fraction')
    # Plot background
    ax2.plot(x, background(p))

    # Profile with subtracted background
    ax3.clear()
    ax3.set_xlabel('X, pixels')
    ax3.set_ylabel('Y, pixels')
    ax3.set_title('Background subtracted ' + ax2title)
    ax3.set_xlabel('Y, pixels')
    ax3.set_ylabel('Signal, quanta')
    p1 = p - background(p)
    ax3.plot(x, p1)
    ymax, ymin, xmax, w, v = profile_param(p1)
    ax3.plot(x[v], 0.5*(ymax + ymin)+p1[v]*0.0)
    ax3.annotate("FWHM = %5.2f mm; %i pixels"%(w*xscale, w), (0.45, 0.9), xycoords='axes fraction')
    ax3.annotate("Max = %5.2f at %5.2f mm; %i pixels"%(p1[xmax], xmax*xscale, xmax), (0.45, 0.8), xycoords='axes fraction')

    # calculate gaussian and lorentzian fitting
    try:
        popt_gauss, pcov_gauss = scipy.optimize.curve_fit(gauss, x[v], p1[v], p0=[p1[xmax], xmax, w])
        popt_lorentz, pcov_lorentz = scipy.optimize.curve_fit(lorentz, x[v], p1[v], p0=[p1[xmax], xmax, w])
        # perr_gauss = np.sqrt(np.diag(pcov_gauss))
        ygf = gauss(x, *popt_gauss)
        ylf = lorentz(x, *popt_lorentz)
        # plot fitting profiles
        ax3.plot(x, ygf)
        ax3.plot(x, ylf)
    except:
        logger.error("Fitting exception ", exc_info=True)

    # Beam tilt and widths dependence on X
    for m in range(nx):
        # plot image
        #ax4.clear()
        #imgplot = ax4.imshow(arr, aspect='equal', cmap='gray')
        box = (x1+dx*m, 0, x1+dx*(m+1)-1, ys)
        # plot box
        #drawBox(ax4, box)
        # calculate profile
        p = profile(arr, box)
        # subtract background
        p = p - background(p)
        mp[m,:] = p
        # plot profile
        #ax4.clear()
        #ax4.plot(x, p)

        # calculate gaussian (lorentzian) fitting
        ymax, ymin, xmax, w, v = profile_param(p)
        popt_gauss = [ymax, xmax, w]
        pf = p
        try:
            popt_gauss, pcov_gauss = scipy.optimize.curve_fit(gauss, x[v], p[v], p0=[ymax, xmax, w])
            #popt_lorentz, pcov_lorentz = scipy.optimize.curve_fit(lorentz, x[v], y[v], p0=[ymax, xmax, w[m]])
            pf = gauss(x, *popt_gauss)
            # plot profile
            #ax4.plot(x, pf)
        except:
            logger.error("Exception ", exc_info=True)
        mx[m] = (box[0] + box[2]) / 2.0
        ma[m] = popt_gauss[0]
        my[m] = popt_gauss[1]
        mw[m] = popt_gauss[2]

    # Tilt of the beam
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(mx, my)
    #print("Angle %5.2f deg" % (slope/np.pi*180.))
    ax1.plot(mx, my, '.')
    ax1.plot(X, slope*X+intercept)
    ax1.annotate("Angle = %5.2f deg" % (slope/np.pi*180.), (0.55, 0.8), xycoords='axes fraction', color='white')

    # Remove tilt
    rotated = img.rotate(slope/np.pi*180.)
    arr2 = np.array(rotated)
    #imgplot2 = ax4.imshow(arr2, aspect='equal', cmap='gray')

    ax4.clear()
    ax4.set_xlabel('X, pixels')
    ax4.set_ylabel('HWFM, pixels')
    ax4.set_title('Width over X')
    ax4.plot(mx, mw, 'o--')
    ax4.set_ylim(bottom=0.0)

    print("%3d %10s FWHM = %5.2f mm MAX = %5.2f at %5.2f mm Angle = %5.2f deg" % (n,
              tfiles[n], w*xscale, p[xmax], xmax*xscale, slope/np.pi*180.))

    plt.savefig(f.replace(".tiff", '_fig.png'))

    if not nonstop:
        inp = input('Q to quit, G to non stop, anything else to continue')
        if inp == 'G' or inp == 'g':
            nonstop = True
        if inp == 'Q' or inp == 'q':
            break

    n += 1

