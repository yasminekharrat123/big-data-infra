FROM fluent/fluentd:v1.16-1

USER root

# Install Ruby development tools and dependencies
RUN apk add --no-cache ruby-dev build-base && \
    gem install fluent-plugin-kafka && \
    apk del build-base # Optional: Clean up build dependencies to reduce image size

# Copy custom Fluentd configuration
COPY fluent.conf /fluentd/etc/fluent.conf

# Ensure proper permissions
RUN chown -R fluent:fluent /fluentd

USER fluent

ENTRYPOINT ["tini", "--", "fluentd"]
CMD ["-c", "/fluentd/etc/fluent.conf"]