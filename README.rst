pycbox
======

Simple web interface showing a directory-listing or thumbnail-gallery of the
files or images in the ``files/`` subdirectory. Users can upload files if the
folder has write-permissions for all.

An example can be seen at pix.coldfix.eu_.

This repo is a python rewrite of the picbox_ php app.

.. _pix.coldfix.eu: https://pix.coldfix.eu
.. _picbox: https://github.com/coldfix/picbox


Usage
-----

You can quickly install the latest release and locally serve files from your
``~/Pictures`` directory as follows:

.. code-block:: bash

    pip install pycbox --user
    pycbox -w ~/Pictures

In order to allow network access on all network interfaces you also need to
add the ``--host 0.0.0.0`` option, e.g.:

.. code-block:: bash

    pycbox -w ~/Pictures -h 0.0.0.0

Alternatively, you can run pycbox without installation from the git checkout.
Though in this case, you still need to install the dependencies as follows:

.. code-block:: bash

    pip install -r requirements.txt --user
    ./bin/pycbox -w ~/Pictures

However, running the pycbox from the command line like this is not recommended
for deployment! From the `flask documentation`_:

    While lightweight and easy to use, Flask’s built-in server is not suitable
    for production as it doesn’t scale well and by default serves only one
    request at a time. Some of the options available for properly running
    Flask in production are documented here.

.. _flask documentation: http://flask.pocoo.org/docs/latest/deploying/

A more sophisticated server can e.g. be run using twisted:

.. code-block:: bash

    twistd --nodaemon --logfile=- web --port=tcp:5000 --wsgi=pycbox.app

In fact, the recommended method is using docker, see Deployment_.


Config
------

If it exists, ``config.yml`` will be loaded from the active directory. The
config file may become mandatory, so you should always copy and adjust the
shipped example config:

.. code-block:: bash

    cp config.example.yml config.yml

An alternate config file name or path can be specified via the
``PYCBOX_CONFIG`` environment variable, i.e. like this:

.. code-block:: bash

   PYCBOX_CONFIG=/path/to/alt_config.yml python pycbox.py 
   PYCBOX_CONFIG=/path/to/alt_config.yml twistd web --wsgi=pycbox.app


Deployment
----------

The recommended method is to run pycbox is via docker. The image can be built
and run as follows:

.. code-block:: bash

    docker build . -t pycbox
    docker run --cap-drop=all \
        -v `pwd`/files:/pycbox/files \
        -p 5000:5000 \
        --name=pycbox pycbox

or simply:

.. code-block:: bash

    docker-compose up

Add ``-d`` to either command line to run in the background.


Proxy
-----

In order to run the application on a subdomain, you will need to setup a proxy
forward. Example ``nginx`` configuration to show the site on ``pix``
subdomain:

.. code-block:: nginx

    server {
        listen      80;
        listen [::]:80;
        server_name pix.example.com pix.example.org;
        return 301 https://$host$request_uri;
    }

    server {
        listen      443 ssl;
        listen [::]:443 ssl;
        server_name pix.example.com pix.example.org;
        access_log /var/log/nginx/access_pics.log;
        location / {
            proxy_pass                          http://localhost:5000;
            proxy_set_header X-Real-IP          $remote_addr;
            proxy_set_header Host               $host;
            proxy_set_header X-Forwarded-For    $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade            $http_upgrade;
            proxy_set_header Connection         upgrade;
        }
    }


Upload
------

To enable uploading to a particular subfolder, make it writable by all:

.. code-block:: bash

    mkdir -p files/public
    chmod 777 files/public


Debug mode
----------

**DO NOT DO THIS IN PRODUCTION** since it allows the client to execute
arbitrary code.

To run the application in debug mode on port 5000, type either:

.. code-block:: bash

    python pycbox.py --debug

or (recommended):

.. code-block:: bash

    FLASK_APP=pycbox.py FLASK_DEBUG=1 flask run

The second command takes care of reloading the server when the python module
is changed and is therefore recommended for development.


Big TODOs
---------

- use redis for caching thumbs and highlighted files
- use asciidoc for markdown
- use pygments for highlighting
- configure via YAML file: auth, quota, uploads, deny globs
