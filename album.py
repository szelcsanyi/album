#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import os.path
import shutil
import sys
import re
import socket

from flask import current_app, Flask, jsonify, render_template, request, send_from_directory, redirect, url_for, got_request_exception
from flask.views import MethodView

from PIL import Image, ExifTags

import rollbar
import rollbar.contrib.flask

__version__ = '0.0.2'

# Config
##################

BASE_DIR = '/home/kepek'
IMAGE_DIR = os.path.join(BASE_DIR, 'images')
THUMB_DIR = os.path.join(BASE_DIR, 'thumbnails')
CHUNKS_DIR = os.path.join(BASE_DIR, 'chunks')

THUMB_WIDTH = 250
THUMB_HEIGHT = 200

ROLLBAR_TOKEN = '9241c264a0944e18a9627303e5875cde'

app = Flask(__name__, static_url_path='')
app.config.from_object(__name__)

# Utils
##################
def make_response(status=200, content=None):
    """ Construct a response to an upload request.
    Success is indicated by a status of 200 and { "success": true }
    contained in the content.

    Also, content-type is text/plain by default since IE9 and below chokes
    on application/json. For CORS environments and IE9 and below, the
    content-type needs to be text/html.
    """
    return current_app.response_class(json.dumps(content,
        indent=None if request.is_xhr else 2), mimetype='text/plain')


def handle_upload(f, attrs, path):
    chunked = False
    dest_folder = os.path.join(app.config['IMAGE_DIR'], path)
    dest = os.path.join(dest_folder, attrs['qqfilename'])


    # Chunked
    if attrs.has_key('qqtotalparts') and int(attrs['qqtotalparts']) > 1:
        chunked = True
        dest_folder = os.path.join(app.config['CHUNKS_DIR'], attrs['qquuid'])
        dest = os.path.join(dest_folder, attrs['qqfilename'], str(attrs['qqpartindex']))

    save_upload(f, dest)

    if chunked and (int(attrs['qqtotalparts']) - 1 == int(attrs['qqpartindex'])):

        combine_chunks(attrs['qqtotalparts'],
            attrs['qqtotalfilesize'],
            source_folder=os.path.dirname(dest),
            dest=os.path.join(app.config['IMAGE_DIR'], path, attrs['qqfilename'])
            )

        shutil.rmtree(os.path.dirname(os.path.dirname(dest)))


def save_upload(f, path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'wb+') as destination:
        destination.write(f.read())


def combine_chunks(total_parts, total_size, source_folder, dest):
    if not os.path.exists(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))

    with open(dest, 'wb+') as destination:
        for i in xrange(int(total_parts)):
            part = os.path.join(source_folder, str(i))
            with open(part, 'rb') as source:
                destination.write(source.read())

def flip_horizontal(im): return im.transpose(Image.FLIP_LEFT_RIGHT)
def flip_vertical(im): return im.transpose(Image.FLIP_TOP_BOTTOM)
def rotate_180(im): return im.transpose(Image.ROTATE_180)
def rotate_90(im): return im.transpose(Image.ROTATE_90)
def rotate_270(im): return im.transpose(Image.ROTATE_270)
def transpose(im): return rotate_90(flip_horizontal(im))
def transverse(im): return rotate_90(flip_vertical(im))
orientation_funcs = [None,
                 lambda x: x,
                 flip_horizontal,
                 rotate_180,
                 flip_vertical,
                 transpose,
                 rotate_270,
                 transverse,
                 rotate_90
                ]

def apply_orientation(im):
    """
    Extract the oritentation EXIF tag from the image, which should be a PIL Image instance,
    and if there is an orientation tag that would rotate the image, apply that rotation to
    the Image instance given to do an in-place rotation.

    :param Image im: Image instance to inspect
    :return: A possibly transposed image instance
    """

    try:
        kOrientationEXIFTag = 0x0112
        if hasattr(im, '_getexif'): # only present in JPEGs
            e = im._getexif()       # returns None if no EXIF data
            if e is not None:
                #log.info('EXIF data found: %r', e)
                orientation = e[kOrientationEXIFTag]
                f = orientation_funcs[orientation]
                return f(im)
    except:
        # We'd be here with an invalid orientation value or some random error?
        #pass # log.exception("Error applying EXIF Orientation tag")
        app.logger.debug('Image orienattion processing error')
    return im


@app.before_first_request
def init_rollbar():
    """init rollbar module"""
    rollbar.init(
        app.config['ROLLBAR_TOKEN'],
        'production',
        root=os.path.dirname(os.path.realpath(__file__)),
        allow_logging_basic_config=False)

    got_request_exception.connect(rollbar.contrib.flask.report_exception, app)

# Views
##################
@app.route("/")
def index():
    return redirect(url_for('list_dir'))

@app.route('/list/', defaults={'path': ''})
@app.route('/list/<path:path>')
def list_dir(path):
    dirs = []
    files = []

    dir = os.path.join( app.config['IMAGE_DIR'], path )
    for i in os.listdir( dir ):
        if os.path.isdir( os.path.join(dir, i) ):
            dirs.append(i)
        elif os.path.isfile( os.path.join(dir, i) ):
            files.append(i)

    dirs.sort()
    files.sort()
    return render_template('list.html', dirs=dirs, basedir=path, parentdir=os.path.dirname(path.rstrip('/'))+'/', files=files)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/thumbnails/<path:path>')
def send_thumbnails(path):
    if not os.path.isfile( os.path.join(THUMB_DIR, path) ):
        app.logger.debug('No thumbnail found')
        image_path = os.path.join(IMAGE_DIR, re.sub('_thumbnail\.jpg$', '', path) )
        if os.path.isfile( image_path ):
            app.logger.debug('Generating thumbnail')
            thumbdir = os.path.dirname(os.path.join(THUMB_DIR, path))
            if not os.path.exists( thumbdir ):
                os.makedirs( thumbdir, 0777 )

            try:
                image = Image.open(image_path)
            except:
                return redirect(u'/static/document.png')

            width = app.config['THUMB_WIDTH']
            height = app.config['THUMB_HEIGHT']

            image = apply_orientation(image)

            if image.size[0] > width or image.size[1] > height:
                if image.size[0] > image.size[1]:
                    scale_with = float(width) / float(image.size[0])
                    newsize = (width, int(image.size[1] * scale_with))
                else:
                    scale_with = float(height) / float(image.size[1])
                    newsize = (int(image.size[0] * scale_with), height)

                #image = image.resize(newsize, Image.ANTIALIAS)
                image.thumbnail(newsize, Image.ANTIALIAS)

            image.save(os.path.join(THUMB_DIR, path), format='JPEG', optimize=True)
        else:
            app.logger.debug('No image found, %s', image_path)
    return send_from_directory(THUMB_DIR, path)

@app.route('/images/<path:path>')
def send_images(path):
    return send_from_directory(IMAGE_DIR, path)

@app.route('/upload/', defaults={'path': ''}, methods=['POST'])
@app.route('/upload/<path:path>', methods=['POST'])
def upload(path):
    handle_upload(request.files['qqfile'], request.form, path)
    return make_response(200, { "success": True })

@app.route('/newdir', methods=['POST'])
def newdir():
    dirname = request.form.get('dirname', type=str, default=None)
    basedir = request.form.get('basedir', type=str, default='')
    app.logger.debug( dirname )
    if dirname is not None:
        if not os.path.isdir( os.path.join( app.config['IMAGE_DIR'], basedir, dirname) ):
            app.logger.debug('Creating dir: %s%s', basedir, dirname)
            os.mkdir( os.path.join( app.config['IMAGE_DIR'], basedir, dirname), 0770)

    return redirect(u'/list/{}'.format(basedir))

@app.route('/errortest')
def errortest():
    return 1 / 0

reload(sys)
sys.setdefaultencoding('utf-8')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
else:
    application = app

