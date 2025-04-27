FROM fluent/fluentd:v1.16-1

USER root
RUN apk update && \
    apk add --no-cache build-base ruby-dev && \
    gem install fluent-plugin-kafka && \
    apk del build-base ruby-dev

USER fluent
