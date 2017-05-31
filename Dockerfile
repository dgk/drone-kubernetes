# kubernetes deploy plugin
#
#     docker build --rm=true -t dgksu/drone-kubernetes .

FROM python:3-alpine
MAINTAINER Dmitry Kuksinsky <dgk@dgk.su>

# kubectl installation based on https://github.com/lachie83/k8s-kubectl/

ARG VCS_REF
ARG BUILD_DATE

# Metadata
LABEL org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url="https://github.com/dgk/drone-kubernetes" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.docker.dockerfile="/Dockerfile"

ENV KUBE_LATEST_VERSION="v1.6.4"

RUN apk add --update ca-certificates \
 && apk add --update -t deps curl \
 && curl -L https://storage.googleapis.com/kubernetes-release/release/${KUBE_LATEST_VERSION}/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
 && chmod +x /usr/local/bin/kubectl \
 && apk del --purge deps \
 && rm /var/cache/apk/*

RUN mkdir -p /opt/drone
COPY requirements.txt /opt/drone/
WORKDIR /opt/drone
RUN pip3 install -r requirements.txt
COPY plugin.py /opt/drone/

ENTRYPOINT ["python3", "/opt/drone/plugin.py"]
