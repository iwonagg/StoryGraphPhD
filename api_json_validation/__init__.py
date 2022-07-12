import io
import json
import os
import tempfile
import uuid
import azure.functions as func
from contextlib import redirect_stdout
from library.tools_validation import get_jsons_storygraph_validated, get_generic_productions_from_file, \
    print_errors_warnings


def prefix_path(path):
    func_dir = os.path.dirname(__file__)
    return os.path.join(func_dir, path)


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        session_path = f'{tempfile.gettempdir()}/{uuid.uuid4()}'
        os.mkdir(session_path)

        input_json_filepath = f'{session_path}/input.json'

        with open(input_json_filepath, 'w', encoding='utf8') as input_json_fp:
            json.dump(req.get_json(), input_json_fp)

        f = io.StringIO()
        with redirect_stdout(f):
            # json_schema_path = prefix_path('../json_validation/json_schema/schemas/schema_updated_20220213.json')
            # dict_schema_path = prefix_path('../json_validation/json_schema/schemas/schema_sheaf_updated_20220213.json')

            g, e = get_generic_productions_from_file(prefix_path(f'../json_validation/allowed_names/produkcje_generyczne.json'))

            allowed_locations = json.load(open(prefix_path('../json_validation/allowed_names/locations.json'), encoding="utf8"))
            allowed_locations += json.load(open(prefix_path('../json_validation/allowed_names/locations_Wojtek.json'), encoding="utf8"))
            allowed_characters = json.load(open(prefix_path('../json_validation/allowed_names/characters.json'), encoding="utf8"))
            allowed_characters += json.load(open(prefix_path('../json_validation/allowed_names/characters_Wojtek.json'), encoding="utf8"))
            allowed_items = json.load(open(prefix_path('../json_validation/allowed_names/items.json'), encoding="utf8"))
            allowed_items += json.load(open(prefix_path('../json_validation/allowed_names/items_Wojtek.json'), encoding="utf8"))
            allowed_names = {"Locations": allowed_locations, "Characters": allowed_characters, "Items": allowed_items}

            jsons_sg_validated, jsons_schema_validated, errors, warnings = get_jsons_storygraph_validated(session_path, production_titles_dict=g, allowed_names=allowed_names)
            print_errors_warnings(jsons_schema_validated, errors, warnings)

            status_code = 400 if errors else 200

        return func.HttpResponse(f.getvalue(), status_code=status_code)
    except ValueError as e:
        return func.HttpResponse(str(e), status_code=400)
