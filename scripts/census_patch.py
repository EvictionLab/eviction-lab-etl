from census import Census
from census.core import SF1Client


# FIXME: Remove this once the issue is fixed in the upstream repo
class SF1ClientPatch(SF1Client):
    def _switch_endpoints(self, year):
        if year > 2000:
            self.endpoint_url = 'https://api.census.gov/data/%s/dec/%s'
            self.definitions_url = 'https://api.census.gov/data/%s/dec/%s/variables.json'
            self.definition_url = 'https://api.census.gov/data/%s/dec/%s/variables/%s.json'
        else:
            self.endpoint_url = super(SF1ClientPatch, self).endpoint_url
            self.definitions_url = super(SF1ClientPatch, self).definitions_url
            self.definition_url = super(SF1ClientPatch, self).definition_url

    def get(self, *args, **kwargs):
        self._switch_endpoints(kwargs.get('year', self.default_year))
        return super(SF1ClientPatch, self).get(*args, **kwargs)


class CensusPatch(Census):
    def __init__(self, key, year=None, session=None):
        super(CensusPatch, self).__init__(key, year, session)
        self.sf1 = SF1ClientPatch(key, year, session)
