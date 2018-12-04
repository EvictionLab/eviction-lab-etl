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
$: docker run --env-file .env -it -v ${PWD}:/App -w="/App" \
    --entrypoint /bin/bash evictionlab/eviction-lab-etl
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
$: docker run --env-file .env -it -v ${PWD}:/App -w="/App" \
    --entrypoint ./run-task.sh evictionlab/eviction-lab-etl \
    data/demographics/tracts.csv
```

### 4. Merge Eviction Lab Data with Crosswalked Demographics (`create_eviction_data.mk`)

> **Note:** Eviction data must be uploaded to the S3_SOURCE_DATA_BUCKET inside a folder corresponding to the BUILD_ID for this build step.

These tasks merge the crosswalked demographics files with the Eviction Lab data.  The valid targets include:

  - `data/states.csv`
  - `data/counties.csv`
  - `data/cities.csv`
  - `data/tracts.csv`
  - `data/block-groups.csv`

For example, get the merged Eviction Lab data with crosswalked demographics for states with:

```bash
$: docker run --env-file .env -it -v ${PWD}:/App -w="/App" \
    --entrypoint ./run-task.sh evictionlab/eviction-lab-etl \
    data/states.csv
```

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

  After generating these files you can preview tiles at http://localhost:8080/ with:

  ```
  $: docker run -it -v $(pwd):/data -p 8080:80 \
        klokantech/tileserver-gl tiles/GEOGRAPHY.mbtiles
  ```

## Building and Deploying with AWS Batch

Deployment is managed by a AWS Batch jobs. If you have an AWS account, you can use the `conf/batch_cfn.yml` CloudFormation template to create an AWS Batch job based on the Dockerfile (with the Docker image `evictionlab/eviction-lab-etl` on Docker Hub). 

Once this is set up, you can run any of the following make commands to have the pipeline step run on AWS batch.

```
# Step 1: Get census demographics
$: make census_geographies

# Step 2: Get census demographics
$: make census_demographics

# Step 3: Crosswalk 2000-2009 data to 2010 census geography
$: make crosswalked_demographics

# Step 4: Merge eviction and demographics data
$: make eviction_lab_data

# Step 5: Build tilesets and deploy
$: make tiles

# Deploy Tasks
$: make deploy_app_data
$: make deploy_public_data
```

## License

This application is open source code under the [MIT License](LICENSE).
