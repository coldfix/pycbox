pycbox
======

Simple web interface showing a directory-listing or thumbnail-gallery of the
files or images in the ``files/`` subdirectory. Users can upload files if the
folder has write-permissions for all.

An example can be seen at pix.coldfix.eu_.

This repo is a python rewrite of the picbox_ php app.

.. _pix.coldfix.eu: https://pix.coldfix.eu
.. _picbox: https://github.com/coldfix/picbox

Config
------

If it exists, ``config.yml`` will be loaded from the active directory. The
config file may become mandatory, so you should always copy and adjust the
shipped example config:

.. code-block:: bash

    cp config.example.yml config.yml

An alternate config file name and path can be specified via the
``PYCBOX_CONFIG`` environment variable.

Deployment
----------

The recommended method will be to run the application via docker. A suitable
dockerfile will soon be added.

Debug mode
----------

**DO NOT DO THIS IN PRODUCTION** since it allows the client to execute
arbitrary code.

To run the application in debug mode on port 5000:

.. code-block:: bash

    python setup.py develop
    FLASK_APP=pycbox.py FLASK_DEBUG=1 flask run

Proxy
-----

In order to run the application on a subdomain, you will need to setup a proxy
forward. Example ``nginx`` configuration to show the site on ``pix``
subdomain:

.. code-block:: nginx

    server {
        listen      80;
        listen [::]:80;
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


Big TODOs
~~~~~~~~~

- dockerfile
- use redis for caching thumbs and highlighted files
- configure via YAML file: auth, quota, uploads, path
