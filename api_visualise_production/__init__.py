import mimetypes
import os
import tempfile
import traceback
import uuid

import azure.functions as func
import requests

from library.tools import destinations_change_to_nodes, nodes_list_from_tree
from library.tools_process import apply_instructions_to_world
from library.tools_visualisation import merge_images, draw_graph


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_json = req.get_json()

        session_path = f'{tempfile.gettempdir()}/{uuid.uuid4()}'
        os.mkdir(session_path)

        resp_validation = requests.post('https://story-graph.azurewebsites.net/api/api_json_validation', json=[req_json])
        if resp_validation.status_code != 200:
            return func.HttpResponse(resp_validation.text, status_code=400)

        destinations_change_to_nodes(req_json["LSide"]["Locations"])
        nodes_list = nodes_list_from_tree(req_json["LSide"]["Locations"], "Locations")
        variant = []
        for node in nodes_list:
            variant.append((node["node"], node["node"]))

        d_title = f'{req_json["Title"].split(" / ")[0]}'

        d_desc = f'{req_json["Description"]}'
        d_file = f'left'
        d_dir = f'{tempfile.gettempdir()}'

        draw_graph(req_json["LSide"], d_title, d_desc, d_file, d_dir, w=False)

        apply_instructions_to_world(req_json, variant, req_json["LSide"], prod_vis_mode=True)

        d_title = f''
        d_desc = f''
        d_file = f'right'

        draw_graph(req_json["LSide"], d_title, d_desc, d_file, d_dir, w=False)

        images = [f'{tempfile.gettempdir()}/left.png', f'{tempfile.gettempdir()}/right.png']
        image_save_filename = f'merged.png'
        image_full_path = f'{session_path}/{image_save_filename}'
        merge_images(images, session_path, image_save_filename)

        with open(image_full_path, 'rb') as f:
            mimetype = mimetypes.guess_type(image_full_path)
            return func.HttpResponse(f.read(), mimetype=mimetype[0], status_code=200)
    except:
        return func.HttpResponse(traceback.format_exc(), status_code=400)
