FROM klokantech/tippecanoe

# Update repos and install dependencies
RUN apt-get update \
  && apt-get -y upgrade \
  && apt-get -y install build-essential libssl-dev \
    python3-dev python3-pip git gzip curl wget

# Link Python path, install Python packages
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    pip3 install pandas csvkit awscli
# Symlink NodeJS and install NPM packages
RUN curl -sL https://deb.nodesource.com/setup_7.x | bash - && \
    ln -s /usr/bin/nodejs /usr/bin/node && \
    apt-get -y install nodejs && \
    npm install -g mapshaper geojson-polygon-labels csvtojson

WORKDIR /
RUN git clone https://github.com/EvictionLab/eviction-lab-etl.git
WORKDIR /eviction-lab-etl/
ENTRYPOINT git pull origin master && make deploy