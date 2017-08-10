FROM alpine:3.6

COPY . /pycbox
WORKDIR /pycbox

ARG runtime_deps="dumb-init python3 zlib jpeg highlight"
ARG build_deps="gcc musl-dev python3-dev zlib-dev jpeg-dev"

RUN apk update && \
    apk add -u $build_deps $runtime_deps && \
    pip3 install incremental && \
    pip3 install twisted && \
    pip3 install flask pillow && \
    python3 setup.py develop && \
    apk del $build_deps && \
    rm -rf /var/cache/apk/* && \
    adduser -D -H -h /pycbox -u 9001 pycbox && \
    mkdir -p            /pycbox /pycbox/hilite /pycbox/thumbs && \
    chown pycbox:pycbox /pycbox /pycbox/hilite /pycbox/thumbs

ENV PYCBOX_CONFIG "config.yml"
VOLUME /pycbox/files
EXPOSE 5000

USER pycbox

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["twistd", "--nodaemon", "--logfile=-", "web", "--port=tcp:5000", "--wsgi=pycbox.app"]
