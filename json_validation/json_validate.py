import os
import tempfile

from config.config import path_root
from library.tools import nodes_list_from_tree, destinations_change_to_nodes
from library.tools_process import apply_instructions_to_world

from library.tools_validation import get_jsons_storygraph_validated, get_generic_productions_from_file, \
    print_errors_warnings
from library.tools_visualisation import draw_graph, merge_images

# json_schema_path = f'../json_validation/schema_updated_20220213.json'
# dict_schema_path = f'../json_validation/schema_sheaf_updated_20220213.json'
json_path = f'{path_root}'


# gdyby w sprawdzanych katalogach nie było pliku z produkcjami generycznymi, trzeba byłoby dodać ich listę jako argument
# production_titles_dict, użylibyśmy do tego g z poniższego wywołania:
# g, e = get_generic_productions_from_file(f'{path_root}/productions/generics/produkcje_generyczne.json')


# walidowanie plików json i wypisywanie błędów
jsons_sg_validated, jsons_schema_validated, errors, warnings = get_jsons_storygraph_validated(json_path)
print_errors_warnings(jsons_schema_validated, errors, warnings)

# generowanie obrazków z prawymi i lewymi stronami produkcji
for mission in jsons_sg_validated:
    for production in mission["json"]:

        # przygotowuję produkcję do wykonania
        destinations_change_to_nodes(production["LSide"]["Locations"])
        nodes_list = nodes_list_from_tree(production["LSide"]["Locations"], "Locations")
        variant = []
        for node in nodes_list:
            variant.append((node["node"], node["node"]))

        # rysowanie wizualizacji
        if production.get('Instructions'):  # Nie świat
            # generuję obrazek lewej strony
            d_title = f'{production["Title"].split(" / ")[0]}'
            d_desc = f'{production["Description"]}'
            d_w = False
            draw_id = True
            d_dir = f'{tempfile.gettempdir()}'
            d_file = f'left'
            draw_graph(production["LSide"], d_title, d_desc, d_file, d_dir, w=d_w, draw_id=draw_id)

            # wykonuję instrukcje
            apply_instructions_to_world(production, variant, production["LSide"], prod_vis_mode=True)

            # generuję obrazek prawej strony
            d_title = f''
            d_desc = f''
            d_file = f'right'
            draw_graph(production["LSide"], d_title, d_desc, d_file, d_dir, w=d_w, draw_id=draw_id)

            # łączę obrazki i zapisuję w plik
            images = [f'{tempfile.gettempdir()}/left.png', f'{tempfile.gettempdir()}/right.png']
            image_save_dir = f'{mission["file_path"].rsplit(os.sep, 1)[0]}/production_vis/'
            image_save_filename = f'{production["Title"].split(" / ")[0]}.png'
            merge_images(images, image_save_dir, image_save_filename)

        else:  # świat
            # generuję obrazek lewej strony
            d_title = f'{production["Title"].split(" / ")[0]}'
            d_desc = f'{production["Description"]}'
            d_w = True
            draw_id = False
            d_dir = f'{mission["file_path"].rsplit(os.sep, 1)[0]}/production_vis/'
            d_file = f'{production["Title"].split(" / ")[0]}'
            draw_graph(production["LSide"], d_title, d_desc, d_file, d_dir, w=d_w, draw_id=draw_id)





