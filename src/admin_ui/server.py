import sys
import os.path
import os

import settings
import animations
import playlist
import launch

from tornado.ioloop import IOLoop
import tornado.web as web
import tornado.gen as gen
from tornado.template import Template
import tornado.websocket as websocket
from optparse import OptionParser
import logging
import json
import zmq
import threading
import Queue
import time
import psutil

def web_path(*args):
    return os.path.join(settings.py_root, *args)

class MainHandler(web.RequestHandler):
    def get(self):
        self.render('main.html', onload='init')

class WebSocketTestHandler(websocket.WebSocketHandler):
    def initialize(self, manager, static_data, zmq_send):
        self.manager = manager
        self.static_data = static_data
        self.zmq_send = zmq_send

    def open(self):
        placements = list(self.static_data['placements'])
        ix = len(placements)
        for f in os.listdir(settings.placements_dir):
            if f.startswith('.'):
                continue
            try:
                preset = animations.load_placements(os.path.join(settings.placements_dir, f))[0]
                preset['ix'] = ix
                ix += 1
                placements.append(preset)
            except:
                print 'error loading preset'
        msg = {
            'type': 'init',
            'playlists': sorted([{'name': k} for k in self.static_data['playlists'].keys()], key=lambda e: e['name']),
            'contents': sorted([{'name': playlist.content_name(c), 'config': c} for c in self.static_data['contents']], key=lambda e: e['name']),
            'placements': placements,
            'ac_power': psutil.sensors_battery().power_plugged,
        }
        self.write_message(json.dumps(msg))
        self.manager.subscribe(self)

    def on_message(self, message):
        data = json.loads(message)
        print 'incoming message:', data

        action = data.get('action')
        if action == 'stop_all':
            self.manager.stop_all()
        if action == 'stop_current':
            self.manager.stop_current()
        if action == 'play_content':
            self.manager.play([c for c in self.static_data['contents'] if playlist.content_name(c) == data['name']][0], data['duration'])
        if action == 'set_playlist':
            self.manager.set_playlist(self.static_data['playlists'][data['name']], data['duration'])
        if action == 'set_trim':
            self.manager.set_wing_trim(data['state'])
        if action == 'set_placement':
            self.set_placement(self.static_data['placements'][data['ix']])
        if action == 'interactive':
            self.interactive(data['id'], data['sess'], data['type'], data.get('val'))
        if action == 'extend_duration':
            self.manager.extend_duration(data['duration'])

    def on_close(self):
        self.manager.unsubscribe(self)

    def set_placement(self, placement):
        broadcast_event('xo', '~%s' % placement.get('xo', 0))
        broadcast_event('yo', '~%s' % placement.get('yo', 0))
        broadcast_event('rot', '~%s' % placement.get('rot', 0))
        broadcast_event('scale', '~%s' % placement.get('scale', 1))
        broadcast_event('wingmode', '~%s' % placement['wing_mode'])
        broadcast_event('stretch', '~%s' % ('yes' if placement['stretch'] else 'no'))

    def interactive(self, id, session, control_type, val):
        if control_type in ('button', 'button-keepalive'):
            button_thread.handle(id, session, {True: 'press', False: 'release', None: 'keepalive'}[val])
        if control_type == 'slider':
            broadcast_event(id, val)
        if control_type == 'jog':
            broadcast_event(id, 'inc' if val > 0 else 'dec')
        if control_type == 'raw':
            if id == 'saveplacement':
                from datetime import datetime
                val += ' ' + datetime.now().strftime('%m-%d %H%M')
            broadcast_event(id, '~' + val)

    def notify(self, msg):
        if 'content' in msg:
            self.write_message(json.dumps({'type': 'content', 'content': msg['content']}))
        if 'playlist' in msg:
            self.write_message(json.dumps({'type': 'playlist', 'playlist': msg['playlist']}))
        if 'duration' in msg:
            self.write_message(json.dumps({'type': 'duration', 'duration': msg['duration']}))
            
keepalive_timeout = 5.
class ButtonPressManager(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.up = True
        self.queue = Queue.Queue()

        self.presses = {}
        self.active = set()

    def handle(self, id, session, val):
        self.queue.put((id, session, val))

    def terminate(self):
        self.up = False

    def run(self):
        while self.up:
            try:
                id, session, val = self.queue.get(True, .01)
                if val in ('press', 'keepalive'):
                    self.presses[(id, session)] = time.time()
                elif val == 'release':
                    try:
                        del self.presses[(id, session)]
                    except KeyError:
                        pass
            except Queue.Empty:
                pass

            expired = []
            for k, v in self.presses.iteritems():
                if time.time() > v + keepalive_timeout:
                    expired.append(k)
            for e in expired:
                del self.presses[k]
            pressed = set(k[0] for k in self.presses.keys())
            for id in (pressed | self.active):
                is_pressed = id in pressed
                is_active = id in self.active
                if is_pressed and not is_active:
                    # send press
                    print 'press', id
                    broadcast_event(id, 'press')
                elif not is_pressed and is_active:
                    # send release
                    print 'release', id
                    broadcast_event(id, 'release')
            self.active = pressed

def broadcast_event(id, val):
    # intercept some ourselves
    if id == 'projectm-next' and val == 'press' and manager.window_id is not None:
        launch.projectm_control(manager.window_id, 'next')
    if id == 'audio-sens':
        min_sens = .3
        max_sens = 3.
        sens = min_sens * (1-val) + max_sens * val
        try:
            launch.set_audio_source_volume([p.pid for p in manager.running_processes], sens)
        except:
            pass

    zmq_send('0:server:%s:%s' % (id, val))

class ZMQListener(threading.Thread):
    def __init__(self, context, manager):
        threading.Thread.__init__(self)
        self.up = True

        self.socket = context.socket(zmq.SUB)
        self.socket.connect("tcp://localhost:%s" % settings.zmq_port_outbound)
        self.socket.setsockopt(zmq.SUBSCRIBE, '')
        
        self.manager = manager

    def handle(self, msg):
        if msg.startswith('videoremain:'):
            amt = float(msg.split(':')[1])
            if (manager.running_content or {}).get('sketch_controls_duration', False):
                manager.extend_duration(amt if amt > 0 else settings.sketch_controls_duration_failsafe_timeout, True)
            
    def terminate(self):
        self.up = False

    def run(self):
        while self.up:
            try:
                msg = self.socket.recv(flags=zmq.NOBLOCK)
                self.handle(msg)
            except zmq.Again as e:
                time.sleep(.01)


if __name__ == "__main__":

    parser = OptionParser()

    (options, args) = parser.parse_args()

    try:
        port = int(args[0])
    except IndexError:
        port = 8000
    ssl = None

    threads = []
    def add_thread(th):
        th.start()
        threads.append(th)
    
    manager = animations.PlayManager()
    add_thread(manager)

    static_data = {
        'playlists': playlist.load_playlists(),
        'contents': list(playlist.get_all_content()),
        'placements': animations.load_placements(),
    }
    for i, e in enumerate(static_data['placements']):
        e['ix'] = i

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:%s" % settings.zmq_port_inbound)
    def zmq_send(msg):
        socket.send(msg.encode('utf8'))

    zmqlisten = ZMQListener(context, manager)
    add_thread(zmqlisten)
        
    button_thread = ButtonPressManager()
    add_thread(button_thread)

    application = web.Application([
        (r'/', MainHandler),
        (r'/socket', WebSocketTestHandler, {'manager': manager, 'static_data': static_data, 'zmq_send': zmq_send}),
        (r'/(.*)', web.StaticFileHandler, {'path': web_path('static')}),
    ], template_path=web_path('templates'))
    application.listen(port, ssl_options=ssl)

    try:
        IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
    except Exception, e:
        print e
        raise

    for th in threads:
        th.terminate()
    logging.info('shutting down...')
