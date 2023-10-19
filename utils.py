"""
Created on Ost 18, 2023
@author: sanin
"""

import os
import sys
__u = os.path.dirname(os.path.realpath(sys.argv[0]))
__u = os.path.join(os.path.split(__u)[0], 'TangoUtils')
if not os.path.exists(__u):
    print('Can not find Utils folder.')
    exit(-2)
if __u not in sys.path:
    sys.path.append(__u)
del __u
