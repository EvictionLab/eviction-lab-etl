# Eviction Lab Data Tool ETL

Data pipeline for [the Eviction Lab map and rankings tool](https://evictionlab.org/map/). Pulls Census and ACS data from the [US Census API](https://www.census.gov/developers/) as well as US Census geography files and combines them with data provided by the Eviction Lab research team ([see Methods for more info](https://evictionlab.org/methods/)) to create [Mapbox vector tiles](https://www.mapbox.com/vector-tiles/), CSV files for rankings, and [public data download files](https://evictionlab.org/get-the-data/).

## Setup

You'll need Node, Python 3, Pipenv, GNU Make, `wget`, [`tippecanoe`](https://github.com/mapbox/tippecanoe), and the AWS CLI installed. To install Python and Node dependencies (on Mac) run:

```bash
npm install -g mapshaper geojson-polygon-labels
pipenv install
brew install tippecanoe
```

To run any `make` commands that involve Python, first run `pipenv shell` to activate the Pipenv virtual environment in a subshell, and then run commands.

To create any individual file (described in the `Makefile`) enter `make` and its name. Otherwise, to generate the full set of files, run `make`. To see a list of all available targets with descriptions in any of the makefiles, run `make -f {FILE} help`.

## Deployment

Deployment is managed by a AWS Batch jobs. If you have an AWS account, you can use the `conf/batch_cfn.yml` CloudFormation template to create an AWS Batch job based on the Dockerfile (with the Docker image `evictionlab/eviction-lab-etl` on Docker Hub). Once this is set up, you can run `make submit_jobs` to schedule a deployment.

## Build Census Data from Source

The main `Makefile` pulls Census geography and demographic data that is pre-generated in the necessary format from the main S3 bucket. If any changes are made, you can re-create this data from source. To create the geography data, run `make -f census.mk` before generating tiles, or run `make -f demographics.mk all` to generate the demographics data.

**Note:** To create Census demographic data, you'll need to get a [Census API Key](https://www.census.gov/developers/), copy the `.env.sample` file to `.env`, add the API key in there. When you run `pipenv shell`, all variables defined in `.env` will be loaded into the shell.

## View Tiles Locally

With Docker installed, run:

`docker run -it -v $(pwd):/data -p 8080:80 klokantech/tileserver-gl GEOGRAPHY.mbtiles`

You'll be able to view a UI for tiles at `localhost:8080`

## License

This application is open source code under the [MIT License](LICENSE).
