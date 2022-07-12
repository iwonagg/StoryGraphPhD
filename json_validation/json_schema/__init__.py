import json
import os

fpath = os.path.join(os.path.dirname(__file__))
schema = json.load(open(f'{fpath}/schemas/schema_updated_20220213.json', encoding="utf8"))
schema_sheaf = json.load(open(f'{fpath}/schemas/schema_sheaf_updated_20220213.json', encoding="utf8"))
