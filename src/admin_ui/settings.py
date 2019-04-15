import os.path
import ConfigParser

py_root = os.path.dirname(os.path.abspath(__file__))
repo_root = reduce(lambda a, b: os.path.dirname(a), xrange(2), py_root)

placements_dir = os.path.join(py_root, 'placements')
playlists_dir = os.path.join(py_root, 'playlists')

def load_java_settings(path):
    from StringIO import StringIO
    mock_section = 'dummy'
    with open(path) as f:
        content = '[%s]\n' % mock_section + f.read()
    config = ConfigParser.ConfigParser()
    config.readfp(StringIO(content))
    for k, v in config.items(mock_section):
        if v == 'true':
            v = True
        elif v == 'false':
            v = False
        globals()[k] = v
load_java_settings(os.path.join(repo_root, 'config.properties'))

# true if the installation has speakers
audio_out = True
kinect = False

media_path = '/home/drew/lsdome-media/'
roms_path = '/home/drew/roms/'

default_duration = 150

# when the sketch controls its own duration, if it sets a duration of
# 'indefinite', use this instead
sketch_controls_duration_failsafe_timeout = 300

default_sketch_properties = {
    'dynamic_subsampling': 1,
}

opc_simulator_path = '/home/drew/dev/lsdome/openpixelcontrol/bin/gl_server'

# in some installs tornado callbacks don't seem to work correctly; set this
# to true to disable them (this could in theory break things, but in practice
# it seems to work fine).
tornado_callbacks_hack = False

enable_security = False
login_password = None
ssl_config = {
    'certfile': os.path.join(os.path.dirname(__file__), 'private/ssl/selfsigned.crt'),
    'keyfile': os.path.join(os.path.dirname(__file__), 'private/ssl/selfsigned.key'),
}

try:
    from localsettings import *
except ImportError:
    pass
