# Changelog
All notable changes to this project will be documented in this file.

## 2018-11-10
### Added
  - changelog
### Changed
  - Save raw files fetched from census API
  - Fetch census data for block group using tract GEOID instead of county GEOID.  The tract number is needed in the heirarchy for the Census API: https://api.census.gov/data/2010/sf1/geography.html