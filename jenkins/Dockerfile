FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update \
    && COMPOSE_PKG="$(if apt-cache show docker-compose-plugin >/dev/null 2>&1; then echo docker-compose-plugin; elif apt-cache show docker-compose-v2 >/dev/null 2>&1; then echo docker-compose-v2; else echo docker-compose; fi)" \
    && apt-get install -y --no-install-recommends docker.io "${COMPOSE_PKG}" ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

USER jenkins
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt
COPY init.groovy.d /usr/share/jenkins/ref/init.groovy.d
