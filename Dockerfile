# Start from ubuntu
FROM ubuntu:17.04

# Update repos and install dependencies
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y install git build-essential \
    libsqlite3-dev zlib1g-dev libssl-dev \
    python3-dev python3-pip gzip curl wget \
    libspatialindex-dev

# Create a directory and copy in all files
RUN mkdir -p /tmp/tippecanoe-src
RUN git clone https://github.com/mapbox/tippecanoe.git /tmp/tippecanoe-src
WORKDIR /tmp/tippecanoe-src

# Build tippecanoe
RUN make \
  && make install

# Remove the temp directory
WORKDIR /
RUN rm -rf /tmp/tippecanoe-src

# Link Python path, install Python packages
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install pandas csvkit awscli geopandas rtree boto3

# Symlink NodeJS and install NPM packages
RUN curl -sL https://deb.nodesource.com/setup_7.x | bash - && \
    ln -s /usr/bin/nodejs /usr/bin/node && \
    apt-get -y install nodejs && \
    npm install -g mapshaper geojson-polygon-labels

WORKDIR /
RUN git clone https://github.com/EvictionLab/eviction-lab-etl.git
WORKDIR /eviction-lab-etl/
ENTRYPOINT ["/eviction-lab-etl/docker-entrypoint.sh"]