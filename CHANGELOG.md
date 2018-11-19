# Changelog
All notable changes to this project will be documented in this file.

## 2018-11-18
### Added
- Logging for the fetch process and reporting merge statistics
- Creates a `CensusDataStore` class to handle all calls to the Census API.  All calls are logged at the debug level so progress can be seen.  All data fetches will retry again in two minutes (up to 10 times) if there are any issues with the connection of availability of the Census API.
- Deploys a log file to S3 after demographics are built for a geography

### Changed
- `create_00_weights.py` has been adjusted so appropriate weights are calculated for counts and rates

## 2018-11-10
### Added
  - changelog
### Changed
  - Save raw files fetched from census API
  - Fetch census data for block group using tract GEOID instead of county GEOID.  The tract number is needed in the heirarchy for the Census API: https://api.census.gov/data/2010/sf1/geography.html