#! /usr/bin/env python
"""
Simple web interface for directory listings and picture gallery.

Usage:
    ./pycbox.py [-h HOST] [-p PORT] [--debug]

Options:
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
import subprocess
from stat import S_ISDIR
from functools import partial
from email.utils import formatdate # RFC 2822
from distutils.spawn import find_executable

import yaml
from flask import (Flask, request, abort, send_from_directory,
                   render_template, url_for)
from werkzeug.utils import secure_filename
from PIL import Image


try:
    with open(os.environ.get('PYCBOX_CONFIG', 'config.yml')) as f:
        cfg = yaml.safe_load(f)
except (FileNotFoundError, IOError):
    cfg = {}

ROOT         = os.path.dirname(__file__)
FILES        = cfg.get('files', os.path.join(ROOT, 'files'))
THUMBS       = cfg.get('thumbs', os.path.join(ROOT, 'thumbs'))
HILITE       = cfg.get('hilite', os.path.join(ROOT, 'hilite'))
THUMB_WIDTH  = cfg.get('thumb_width', 450)
THUMB_HEIGHT = cfg.get('thumb_height', 150)
IMAGE_EXTS   = cfg.get('image_exts', ('.jpg', '.jpeg', '.png', '.bmp', '.gif'))
FRONTPAGE    = cfg.get('frontpage', 'index')

FILES = os.path.abspath(FILES)
THUMBS = os.path.abspath(THUMBS)
HILITE = os.path.abspath(HILITE)


app = Flask(__name__)


def content_url(path, filename, action):
    return url_for(action, path=os.path.join('/', path, filename)[1:])


@app.route('/')
def frontpage():
    return directory_listing(FRONTPAGE, '')


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
    full = os.path.join(FILES, path)
    if not os.path.exists(full):
        return abort(404)
    names = ['.'] + (path and ['..'] or []) + os.listdir(full)
    files = [File(path, name) for name in names if not hidden(name)]
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
    full = os.path.join(FILES, path)
    if not os.path.exists(full):
        return abort(404)
    file = File(*os.path.split(path))
    if not file.is_image:
        return abort(404)
    create_thumb(path)
    return send_from_directory(THUMBS, path, as_attachment=False)


@app.route('/download/<path:path>')
def download(path):
    if not check_path(path):
        return abort(401)
    return send_from_directory(FILES, path, as_attachment=True)


@app.route('/view/<path:path>')
def view(path):
    if not check_path(path):
        return abort(401)
    return send_from_directory(FILES, path, as_attachment=False)


@app.route('/highlight/<path:path>')
def highlight(path):
    if not check_path(path):
        return abort(401)
    if not create_highlight(path):
        abort(404)
    return send_from_directory(HILITE, path+'.html', as_attachment=False)


@app.route('/upload/<path:path>', methods=['POST'])
def upload(path):
    if not check_path(path):
        return abort(401)
    path = normpath(path)
    full = os.path.join(FILES, path)
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
        self.full = os.path.join(FILES, self.path)
        self.base = base
        self.name = name
        self.stat = os.stat(self.full)
        self.mode = self.stat.st_mode
        self.size = self.stat.st_size
        self.time = self.stat.st_mtime
        self.is_dir = S_ISDIR(self.mode)
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
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def thumb_size(path):
    image = Image.open(path)
    return _thumb_size(*image.size)


def _thumb_size(image_width, image_height,
                thumb_width=THUMB_WIDTH,
                thumb_height=THUMB_HEIGHT):
    if image_width / image_height > thumb_width / thumb_height:
        thumb_height = thumb_width * image_height // image_width
    elif image_width / image_height < thumb_width / thumb_height:
        thumb_width = thumb_height * image_width // image_height
    return (thumb_width, thumb_height)


def create_thumb(path):
    orig = os.path.join(FILES, path)
    dest = os.path.join(THUMBS, path)
    if not os.path.exists(dest) or newer_than(orig, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
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
    orig = os.path.join(FILES, path)
    dest = os.path.join(HILITE, path) + '.html'
    if not os.path.exists(dest) or newer_than(orig, dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        return tool and 0 == subprocess.call(tool + [
            '-i', orig, '-o', dest,
            '-T', os.path.basename(orig),
            '--out-format', 'html', '--doc', '-q',
        ])
    return os.path.exists(dest)


if __name__ == '__main__':
    from docopt import docopt
    opts = docopt(__doc__)
    app.run(opts['--host'], opts['--port'], debug=opts['--debug'])
