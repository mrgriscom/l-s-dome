#!/usr/bin/python

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../admin_ui'))
import settings
import playlist

num_opcs = {
    'prometheus': 2,
}.get(settings.geometry, 1)

layout = playlist.fadecandy_config().replace('/fadecandy/', '/simulator_layouts/')

for i in xrange(num_opcs):
    os.popen('%s -l "%s" -p %d &' % (settings.opc_simulator_path, layout, int(settings.opcport) + i))
