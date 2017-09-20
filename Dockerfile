FROM laneolson/tippecanoe

# Update repos and install dependencies
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y install build-essential libssl-dev \
    python-pip git gzip curl wget

# Install Python packages
RUN pip install pandas csvkit awscli
# Symlink NodeJS and install NPM packages
RUN curl -sL https://deb.nodesource.com/setup_7.x | bash - && \
    ln -s /usr/bin/nodejs /usr/bin/node && \
    apt-get -y install nodejs && \
    npm install -g mapshaper geojson-polygon-labels

WORKDIR /
RUN git clone https://github.com/EvictionLab/eviction-lab-etl.git
WORKDIR /eviction-lab-etl/
ENTRYPOINT git pull origin master && make deploy