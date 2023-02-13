FROM mariadb:latest
LABEL maintainer="antarcticrainforest" \
      repository="https://github.com:antarcticrainforest/baby-measure"\
      description="Track babie's growth and health"
ENV MYSQL_ROOT_HOST=localhost \
    MYSQL_DATABASE=baby_measure \
    MYSQL_USER=baby \
    MYSQL_PORT=3306 \
    MYSQL_PASSWORD=m3sAurE48 \
    MYSQL_ROOT_PASSWORD=m3sAurE48 \
    CONFIG_DIR=/var/volume

RUN apt -y update && apt -y install git python3 python3-pip \
    && python3 -m pip install -U pip && \
    python -3 m pip install git+https://github.com/antarcticrainforest/baby-measure.git@init
VOLUME /var/volume
EXPOSE 5080
WORKDIR /var/volume
