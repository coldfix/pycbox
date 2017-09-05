#! /usr/bin/env python
# encoding: utf-8
"""
Simple web interface for directory listings and picture gallery.

Usage:
    ./pycbox.py [-w WEBROOT] [-c CONFIG] [-h HOST] [-p PORT] [--debug]

Options:
    -w PATH, --webroot PATH     Serve files from this directory.
    -c PATH, --config PATH      Config file name
    -h HOST, --host HOST        Interface to listen on [default: 127.0.0.1]
    -p PORT, --port PORT        Port to listen on [default: 5000]
    --debug                     Turn on debug mode. NEVER use this in production!
                                It allows the client arbitrary code execution.

Running the pycbox from the command line is not recommended for deployment!
From http://flask.pocoo.org/docs/latest/deploying/:

    While lightweight and easy to use, Flask’s built-in server is not suitable
    for production as it doesn’t scale well and by default serves only one
    request at a time. Some of the options available for properly running
    Flask in production are documented here.

A more sophisticated server can e.g. be run using twisted:

    twistd --nodaemon --logfile=- web --port=tcp:5000 --wsgi=pycbox.app
"""

import os
import errno
import subprocess
from stat import S_ISDIR
from functools import partial
from distutils.spawn import find_executable

import yaml
from flask import (Flask, request, abort, send_from_directory,
                   render_template, url_for)
from werkzeug.utils import secure_filename
from PIL import Image


class Config(dict):
    def __getattr__(self, key):
        return self[key]


ROOT = os.path.dirname(__file__)
cfg = Config({
    'FILES':        os.path.join(ROOT, '..', 'files'),
    'CACHE':        os.path.join(ROOT, '..', 'cache'),
    'THUMBS':       'thumbs',
    'HILITE':       'hilite',
    'THUMB_WIDTH':  450,
    'THUMB_HEIGHT': 150,
    'IMAGE_EXTS':   ('.jpg', '.jpeg', '.png', '.bmp', '.gif'),
    'FRONTPAGE':    'index',
})


app = Flask(__name__)


def content_url(path, filename, action):
    return url_for(action, path=os.path.join('/', path, filename)[1:])


@app.route('/')
def frontpage():
    return directory_listing(cfg.FRONTPAGE, '')


@app.route('/index/')
@app.route('/index/<path:path>/')
def index(path=''):
    return directory_listing('index', path)


@app.route('/gallery/')
@app.route('/gallery/<path:path>/')
def gallery(path=''):
    return directory_listing('gallery', path)


def directory_listing(active, path):
    if not check_path(path):
        return abort(401)
    path = normpath(path)
    full = os.path.join(cfg.FILES, path)
    if not os.path.exists(full):
        return abort(404)
    names = ['.'] + (path and ['..'] or []) + os.listdir(full)
    files = [File(path, name) for name in names if not hidden(name)]
    files = [f for f in files if f.accessible]
    return render_template(active + '.html', **{
        'active': active,
        'files': files,
        'link': partial(content_url, path),
        'static': lambda name: url_for('static', filename=name),
        'can_upload': os.access(full, os.W_OK),
        'heading': active.title() + ': /' + path,
        'title': 'picbox: /' + path,
    })


@app.route('/thumb/<path:path>')
def thumb(path):
    if not check_path(path):
        return abort(401)
    path = normpath(path)
    full = os.path.join(cfg.FILES, path)
    if not os.path.exists(full):
        return abort(404)
    file = File(*os.path.split(path))
    if not file.is_image or not file.accessible:
        return abort(404)
    create_thumb(path)
    return send_from_directory(cfg.THUMBS, path, as_attachment=False)


@app.route('/download/<path:path>')
def download(path):
    if not check_path(path):
        return abort(401)
    return send_from_directory(cfg.FILES, path, as_attachment=True)


@app.route('/view/<path:path>')
def view(path):
    if not check_path(path):
        return abort(401)
    return send_from_directory(cfg.FILES, path, as_attachment=False)


@app.route('/highlight/<path:path>')
def highlight(path):
    if not check_path(path):
        return abort(401)
    if not create_highlight(path):
        return abort(404)
    return send_from_directory(cfg.HILITE, path+'.html', as_attachment=False)


@app.route('/upload/', methods=['POST'])
@app.route('/upload/<path:path>', methods=['POST'])
def upload(path=''):
    if not check_path(path):
        return abort(401)
    path = normpath(path)
    full = os.path.join(cfg.FILES, path)
    if not os.path.exists(full):
        return abort(404)
    file = request.files['file']
    name = secure_filename(file.filename)   # FIXME: secure_filename maybe too much?
    dest = os.path.join(full, name)
    file.save(dest)
    return render_template('upload.html', **{
        'path': path,
        'name': name,
        'referer': content_url(path, '.', request.form['referer']),
        'static': lambda name: url_for('static', filename=name),
    })


def normpath(path):
    path = os.path.normpath(path)
    if path == '.':
        path = ''
    return path


def check_path(path):
    """Prevent users from breaking out of the files/ directory."""
    path = os.path.normpath(path)
    comp = path.split(os.path.sep)
    return (not os.path.isabs(path) and
            not any(map(hidden, comp)) and
            not '..' in comp)


def hidden(name):
    return name.startswith('.') and name not in ('.', '..')


class File:

    def __init__(self, base, name):
        self.path = os.path.join(base, name)
        self.full = os.path.join(cfg.FILES, self.path)
        self.base = base
        self.name = name
        self.stat = os.stat(self.full)
        self.mode = self.stat.st_mode
        self.size = self.stat.st_size
        self.time = self.stat.st_mtime
        self.is_dir = S_ISDIR(self.mode)
        self.accessible = os.access(self.full, os.R_OK | (self.is_dir and os.X_OK))
        if not self.accessible:     # prevent exception below by returning
            return                  # immediately
        self.is_image = not self.is_dir and is_image(self.full)
        self.is_code = not self.is_dir and not self.is_image and create_highlight(self.path)
        self.is_other = not any((self.is_dir, self.is_image, self.is_code))
        if self.is_image:
            self.thumb_width, self.thumb_height = thumb_size(self.full)
        if self.is_dir:
            self.size = len(os.listdir(self.full))

    def filesize_unit(self):
        size = self.size
        if size >= 1e10:  return "GiB"
        elif size >= 1e7: return "MiB"
        else:             return "KiB"

    def filesize(self, unit=None):
        size = self.size
        unit = unit or self.filesize_unit()
        pow = ('Byte', 'KiB', 'MiB', 'GiB').index(unit)
        return "{:.2f}".format(size / 1024**pow) if pow else size


def newer_than(a, b):
    return os.path.getmtime(a) > os.path.getmtime(b)


# Images / thumbnails

def is_image(path):
    return os.path.splitext(path)[1].lower() in cfg.IMAGE_EXTS


def thumb_size(path):
    image = Image.open(path)
    return _thumb_size(*image.size)


def _thumb_size(image_width, image_height, thumb_width=None, thumb_height=None):
    thumb_width = thumb_width or cfg.THUMB_WIDTH
    thumb_height = thumb_height or cfg.THUMB_HEIGHT
    if image_width / image_height > thumb_width / thumb_height:
        thumb_height = thumb_width * image_height // image_width
    elif image_width / image_height < thumb_width / thumb_height:
        thumb_width = thumb_height * image_width // image_height
    return (thumb_width, thumb_height)


def create_thumb(path):
    orig = os.path.join(cfg.FILES, path)
    dest = os.path.join(cfg.THUMBS, path)
    if not os.path.exists(dest) or newer_than(orig, dest):
        mkdir_p(os.path.dirname(dest))
        image = Image.open(orig)
        image.thumbnail(_thumb_size(*image.size))
        image.save(dest)


# source highlights

def source_highlight():
    if find_executable('source-highlight'):
        return ['source-highlight']
    if find_executable('highlight'):
        return ['highlight', '--inline-css']


def create_highlight(path):
    tool = source_highlight()
    orig = os.path.join(cfg.FILES, path)
    dest = os.path.join(cfg.HILITE, path) + '.html'
    if not os.path.exists(dest) or newer_than(orig, dest):
        mkdir_p(os.path.dirname(dest))
        return tool and 0 == subprocess.call(tool + [
            '-i', orig, '-o', dest,
            '-T', os.path.basename(orig),
            '--out-format', 'html', '--doc', '-q',
        ])
    return os.path.exists(dest)


# py2 compatibility

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(path):
            raise


def load_config(filename):
    try:
        with open(filename) as f:
            conf = yaml.safe_load(f)
        return {key.upper(): val for key, val in conf.items()}
    except (FileNotFoundError, IOError):
        return {}


def sanitize_config(conf):
    conf.FILES  = os.path.abspath(conf.FILES)
    conf.CACHE  = os.path.abspath(conf.CACHE)
    conf.THUMBS = os.path.join(conf.CACHE, conf.THUMBS)
    conf.HILITE = os.path.join(conf.CACHE, conf.HILITE)


def main(args=None):
    from docopt import docopt
    opts = docopt(__doc__, args)
    if opts['--config']:
        cfg.update(load_config(opts['--config']))
    if opts['--webroot']:
        cfg.FILES = opts['--webroot']
    sanitize_config(cfg)
    app.run(opts['--host'], int(opts['--port']), debug=opts['--debug'])


path = os.environ.get('PYCBOX_CONFIG', 'config.yml')
cfg.update(load_config(path))
sanitize_config(cfg)
