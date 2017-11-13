# Eviction Lab Tile Data ETL

Makefile for running ETL on Eviction Lab data.

## Setup

You'll need Node, Python, GNU Make, and `wget` installed. You'll also need the Python packages `pandas`, `boto3`, `census`, and [`csvkit`](https://csvkit.readthedocs.io/en/1.0.2/index.html) (all included in `requirements.txt`) and the NPM packages [`mapshaper`](https://github.com/mbloch/mapshaper), and [`geojson-polygon-labels`](https://github.com/andrewharvey/geojson-polygon-labels) as well as [`tippecanoe`](https://github.com/mapbox/tippecanoe). To install these dependencies (on Mac) run:

```bash
npm install -g mapshaper geojson-polygon-labels
sudo pip install csvkit pandas
brew install tippecanoe
```

To create any individual file (described in the `Makefile`) enter `make` and its name. Otherwise, to generate the full set of files, run `make`.

## Deployment

Deployment is managed by an AWS Batch job. If you have an AWS account, you can use the `batch_cfn.yml` CloudFormation template to create an AWS Batch job based on the Dockerfile (with the Docker image `evictionlab/eviction-lab-etl` on Docker Hub). Once this is set up, you can run `make deploy` to schedule a job.

## Build Census Data from Source

Currently the Census GeoJSON is getting pulled from an S3 bucket where it has been pre-processed and gzipped. If you want to build this from the original Census files, run `make -f census.mk` before running `make`. It will create the initial GeoJSON files, and because Make uses file existence to determine dependencies you can then run `make` and any other steps as normal.

## Create Fixture Data

To create fixture data (used in our workflow to test load times), run `make -f fake.mk` similarly to building census data from source.

## View Tiles Locally

With Docker installed, run:

`docker run -it -v $(pwd):/data -p 8080:80 klokantech/tileserver-gl GEOGRAPHY.mbtiles`

You'll be able to view a UI for tiles at `localhost:8080`