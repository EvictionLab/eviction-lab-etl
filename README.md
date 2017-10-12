# Eviction Lab Tile Data ETL

Makefile for running ETL on Eviction Lab data.

## Setup

You'll need Node, Python, GNU Make, and `wget` installed. You'll also need the Python packages `pandas` and [`csvkit`](https://csvkit.readthedocs.io/en/1.0.2/index.html) and the NPM packages [`mapshaper`](https://github.com/mbloch/mapshaper) and [`geojson-polygon-labels`](https://github.com/andrewharvey/geojson-polygon-labels) as well as [`tippecanoe`](https://github.com/mapbox/tippecanoe). To install these dependencies (on Mac) run:

```bash
npm install -g mapshaper geojson-polygon-labels
sudo pip install csvkit pandas
brew install tippecanoe
```

To create any individual file (described in the `Makefile`) enter `make` and its name. Otherwise, to generate the full set of files, run `make all`.

## Deployment

Deployment is managed by an AWS Batch job. If you have an AWS account and a Batch job set up based on the Dockerfile, you can  run `make deploy` to schedule a job.

## Build Census Data from Source

Currently the Census GeoJSON is getting pulled from an S3 bucket where it has been pre-processed and gzipped. If you want to build this from the original Census files, run `make -f census.mk all` before running `make all`. It will create the initial GeoJSON files, and because Make uses file existence to determine dependencies you can then run `make all` and any other steps as normal.

## View Tiles Locally

With Docker installed, run:

`docker run -it -v $(pwd):/data -p 8080:80 klokantech/tileserver-gl GEOGRAPHY.mbtiles`

You'll be able to view a UI for tiles at `localhost:8080`