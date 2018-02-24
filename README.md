# Eviction Lab Data ETL

Data pipeline for Eviction Lab.

## Setup

You'll need Node, Python 3, GNU Make, and `wget` installed. You'll also need the Python packages `pandas`, `boto3`, `census`, and [`csvkit`](https://csvkit.readthedocs.io/en/1.0.2/index.html) (all included in `scripts/requirements.txt`) and the NPM packages [`mapshaper`](https://github.com/mbloch/mapshaper), and [`geojson-polygon-labels`](https://github.com/andrewharvey/geojson-polygon-labels) as well as [`tippecanoe`](https://github.com/mapbox/tippecanoe). To install these dependencies (on Mac) run:

```bash
npm install -g mapshaper geojson-polygon-labels
sudo pip install csvkit pandas
brew install tippecanoe
```

To create any individual file (described in the `Makefile`) enter `make` and its name. Otherwise, to generate the full set of files, run `make`. To see a list of all available targets with descriptions in any of the makefiles, run `make -f {FILE} help`.

## Deployment

Deployment is managed by a AWS Batch jobs. If you have an AWS account, you can use the `conf/batch_cfn.yml` CloudFormation template to create an AWS Batch job based on the Dockerfile (with the Docker image `evictionlab/eviction-lab-etl` on Docker Hub). Once this is set up, you can run `make submit_jobs` to schedule a deployment.

## Build Census Data from Source

The main `Makefile` pulls Census geography and demographic data that is pre-generated in the necessary format from the main S3 bucket. If any changes are made, you can re-create this data from source. To create the geography data, run `make -f census.mk` before generating tiles, or run `make -f demographics.mk all` to generate the demographics data.

**Note:** To create Census demographic data, you'll need to get a [Census API Key](https://www.census.gov/developers/), copy the `.env.sample` file to `.env`, add the API key in there, and run `source .env`.

## View Tiles Locally

With Docker installed, run:

`docker run -it -v $(pwd):/data -p 8080:80 klokantech/tileserver-gl GEOGRAPHY.mbtiles`

You'll be able to view a UI for tiles at `localhost:8080`