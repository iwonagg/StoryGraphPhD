import json
import mimetypes
import os
import tempfile
import traceback
import uuid

import azure.functions as func

from library.tools import draw_production_tree
from library.tools_match import get_production_tree_new
from library.tools_validation import get_generic_productions_from_file, get_jsons_storygraph_validated


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

        # json_schema_path = prefix_path('../json_validation/json_schema/schemas/schema_updated_20220213.json')
        # dict_schema_path = prefix_path('../json_validation/json_schema/schemas/schema_sheaf_updated_20220213.json')

        g, e = get_generic_productions_from_file(
            prefix_path(f'../json_validation/allowed_names/produkcje_generyczne.json'))

        allowed_locations = json.load(open(prefix_path('../json_validation/allowed_names/locations.json'), encoding="utf8"))
        allowed_locations += json.load(open(prefix_path('../json_validation/allowed_names/locations_Wojtek.json'), encoding="utf8"))
        allowed_characters = json.load(open(prefix_path('../json_validation/allowed_names/characters.json'), encoding="utf8"))
        allowed_characters += json.load(open(prefix_path('../json_validation/allowed_names/characters_Wojtek.json'), encoding="utf8"))
        allowed_items = json.load(open(prefix_path('../json_validation/allowed_names/items.json'), encoding="utf8"))
        allowed_items += json.load(open(prefix_path('../json_validation/allowed_names/items_Wojtek.json'), encoding="utf8"))
        allowed_names = {"Locations": allowed_locations, "Characters": allowed_characters, "Items": allowed_items}

        jsons_sg_validated, jsons_schema_validated, errors, warnings = get_jsons_storygraph_validated(session_path, production_titles_dict=g, allowed_names=allowed_names)

        for data in jsons_schema_validated:
            json_generic_productions_file_path = prefix_path(f'../json_validation/allowed_names/produkcje_generyczne.json')
            json_generic_productions = {
                'json': json.load(open(json_generic_productions_file_path, encoding="utf8")),
                'file_path': json_generic_productions_file_path,
            }
            prod_hierarchy, g, m = get_production_tree_new(json_generic_productions, data)
            if prod_hierarchy:
                draw_production_tree(prod_hierarchy, missing=m, mission_name='out', directory_path=session_path)

        image_full_path = f'{session_path}/out.png'
        with open(image_full_path, 'rb') as f:
            mimetype = mimetypes.guess_type(image_full_path)
            return func.HttpResponse(f.read(), mimetype=mimetype[0], status_code=200)
    except:
        return func.HttpResponse(traceback.format_exc(), status_code=400)
