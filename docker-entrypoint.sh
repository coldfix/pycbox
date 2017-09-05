#! /bin/sh
adduser -D -H -h    /pycbox -u $PYCBOX_UID pycbox && \
mkdir -p            /pycbox /pycbox/cache /pycbox/hilite
chown pycbox:pycbox /pycbox /pycbox/cache /pycbox/hilite
exec /sbin/su-exec pycbox:pycbox "$@"
