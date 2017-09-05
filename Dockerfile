FROM alpine:3.6

COPY ./pycbox /pycbox/pycbox
COPY ./docker-entrypoint.sh /pycbox/
WORKDIR /pycbox

ARG runtime_deps="dumb-init python3 zlib jpeg yaml highlight su-exec"
ARG build_deps="gcc musl-dev python3-dev zlib-dev jpeg-dev yaml-dev ca-certificates"

RUN apk update && \
    apk add -u $build_deps $runtime_deps && \
    pip3 install incremental && \
    pip3 install twisted && \
    pip3 install docopt flask pillow pyyaml && \
    apk del $build_deps && \
    rm -rf /var/cache/apk/*

# USER pycbox  # is set in entrypoint
VOLUME /pycbox/cache
VOLUME /pycbox/files
EXPOSE 5000

ENV PYCBOX_UID 9001
ENV PYCBOX_CONFIG "config.yml"
ENV PYTHONPATH "."

ENTRYPOINT ["/usr/bin/dumb-init", "--", "./docker-entrypoint.sh"]
CMD ["twistd", "--nodaemon", "--logfile=-", "web", "--port=tcp:5000", "--wsgi=pycbox.app"]
