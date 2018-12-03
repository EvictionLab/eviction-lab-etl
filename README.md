# Eviction Lab Data Tool ETL

Data pipeline for [the Eviction Lab map and rankings tool](https://evictionlab.org/map/). Pulls Census and ACS data from the [US Census API](https://www.census.gov/developers/) as well as US Census geography files and combines them with data provided by the Eviction Lab research team ([see Methods for more info](https://evictionlab.org/methods/)) to create [Mapbox vector tiles](https://www.mapbox.com/vector-tiles/), CSV files for rankings, and [public data download files](https://evictionlab.org/get-the-data/).

## Getting Started

To run the ETL pipeline, first clone the repository and perform the steps below.

### 1. Setup Environment Variables

Create a `.env` file that contains the required configuration to run the pipeline.

```bash
$: cp .env.staging .env
```
Open the `.env` file and set the `CENSUS_KEY` variable. You can request for a [Census API Key](https://www.census.gov/developers/) if you do not have one. 

If you want to run any of the deploy tasks to push that data to S3, you will need to set the S3 variables in the `.env` file.  AWS access ID and secret key need to be provided to you by the AWS resource administrator. 

### 2. Pull the Docker Container

Use Docker to fetch a container containing the necessary tools for running the ETL pipeline:

```bash
$: docker pull evictionlab/eviction-lab-etl
```

All tasks will be run within the docker container.  You can run the docker container with your envionment variable configuration with the following command:

```bash
$: docker run --env-file .env -it -v ${PWD}:/App \
    --entrypoint /App/run-task.sh evictionlab/eviction-lab-etl
```

You are now ready to run any of the tasks in the pipeline, all of the valid task names are provided below:

## Data Pipeline Tasks

### 1. Fetch 2010 Census Geography (`fetch_census_geography.mk`)
For example, to build the geojson for states:

```bash
$: docker run --env-file .env evictionlab/eviction-lab-etl census/states.geojson
```

### 2. Fetch Demographics Data (`fetch_raw_census_api.mk`)

These tasks fetch all demogaphics data from the Census API.  The valid targets include:

  - `data/demographics/raw/states-00.csv`
  - `data/demographics/raw/states-10.csv`
  - `data/demographics/raw/counties-00.csv`
  - `data/demographics/raw/counties-10.csv`
  - `data/demographics/raw/cities-00.csv`
  - `data/demographics/raw/cities-10.csv`
  - `data/demographics/raw/tracts-00.csv`
  - `data/demographics/raw/tracts-10.csv`
  - `data/demographics/raw/block-groups-00.csv`
  - `data/demographics/raw/block-groups-10.csv`
  
For example, to fetch all block group demographics for the years 2000-2009:

```bash
$: docker run --env-file .env evictionlab/eviction-lab-etl data/demographics/raw/block-groups-00.csv
```

### 3. Crosswalk 2000 Demographics Data to 2010 Census Geography (`process_demographics.mk`)

These tasks take the raw demographics from the previous step, perform required crosswalks to fit into the census 2010 geography, and combine data into one file for each geography level.  The valid targets include:

  - `data/demographics/states.csv`
  - `data/demographics/counties.csv`
  - `data/demographics/cities.csv`
  - `data/demographics/tracts.csv`
  - `data/demographics/block-groups.csv`

For example, to fetch all of the tract level demographics data for 2000-2016, with 2000-2009 data crosswalked to fit census 2010 geography:

```bash
$: docker run --env-file .env evictionlab/eviction-lab-etl data/demographics/tracts.csv
```

### 4. Merge Eviction Lab Data with Crosswalked Demographics (`create_eviction_data.mk`)

These tasks merge the crosswalked demographics files with the Eviction Lab data.  The valid targets include:

  - `data/states.csv`
  - `data/counties.csv`
  - `data/cities.csv`
  - `data/tracts.csv`
  - `data/block-groups.csv`

#### 4a. Deploy Map and Rankings Data

Running the `deploy_app_data` task will deploy data used for the map data panel and city rankings to S3.

#### 4b. Deploy Public Data Exports

Running the `deploy_public_data` task will create the data exports and deploy them to S3.

### 5. Create Eviction Lab Tilesets (`create_eviction_tilesets.mk`)

These tasks take the Eviction Lab data and demographics from step 4 and create tilesets that have all of the data associated with them.

  - `tiles/states-00.mbtiles`
  - `tiles/states-10.mbtiles`
  - `tiles/counties-00.mbtiles`
  - `tiles/counties-10.mbtiles`
  - `tiles/cities-00.mbtiles`
  - `tiles/cities-10.mbtiles`
  - `tiles/tracts-00.mbtiles`
  - `tiles/tracts-10.mbtiles`
  - `tiles/block-groups-00.mbtiles`
  - `tiles/block-groups-10.mbtiles`

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
