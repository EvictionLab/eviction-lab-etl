# Eviction Lab Tile Data ETL

Makefile for running ETL on Eviction Lab data.

## Setup

You'll need Node, GNU Make, `curl`, and `wget` installed. You'll also need the NPM packages [`csvtojson`](https://github.com/Keyang/node-csvtojson), [`mapshaper`](https://github.com/mbloch/mapshaper), and [`geojson-polygon-labels`](https://github.com/andrewharvey/geojson-polygon-labels) as well as [`tippecanoe`](https://github.com/mapbox/tippecanoe). To install these dependencies (on Mac) run:

```bash
npm install -g csvtojson mapshaper geojson-polygon-labels
brew install tippecanoe
```

To create any individual file (described in the `Makefile`) enter `make` and its name. Otherwise, to generate the full set of files, run `make all`.

## View Tiles Locally

With Docker installed, run:

`docker run -it -v $(pwd):/data -p 8080:80 klokantech/tileserver-gl GEOGRAPHY.mbtiles`

You'll be able to view a UI for tiles at `localhost:8080`