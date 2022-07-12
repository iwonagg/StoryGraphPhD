import mimetypes
import os
import traceback
from random import randint

import azure.functions as func

def prefix_path(path):
    func_dir = os.path.dirname(__file__)
    return os.path.join(func_dir, path)


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        worlds = os.listdir(prefix_path('worlds'))

        world = worlds[randint(0, len(worlds))]

        world_json_path = prefix_path(f'worlds/{world}')

        with open(world_json_path, 'rb') as f:
            mimetype = mimetypes.guess_type(world_json_path)
            return func.HttpResponse(f.read(), mimetype=mimetype[0], status_code=200)
    except:
        return func.HttpResponse(traceback.format_exc(), status_code=400)
