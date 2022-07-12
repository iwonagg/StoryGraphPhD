import datetime
import logging
import sys

from config.config import path_root
from library.tools import *


# wgrywanie jsonów do testów

#################################################################
from library.tools_match import what_to_do
from library.tools_validation import get_jsons_storygraph_validated
from library.tools_visualisation import draw_graph, GraphVisualizer

json_path = f'{path_root}/'
# json_schema_path = f'../json_validation/schema_updated_20220213.json'
# dict_schema_path = f'../json_validation/schema_sheaf_updated_20220213.json'
mask = '*.json'
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s', stream=sys.stdout)
#################################################################

# wczytywanie jsonów
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path, mask)



show_missions_list = True
if show_missions_list:
    if jsons_OK:
        print(f'Poprawne jsony w katalogu "{json_path}" wśród plików "{mask}":')
        for json_ok, nr in zip(jsons_OK, range(len(jsons_OK))):
            print(f"     {nr}. {json_ok['file_path']}")
    if jsons_schema_OK:
        print(f'Zgodne ze schematem jsony w katalogu "{json_path}" wśród plików "{mask}":')
        for schema_ok, nr in zip(jsons_schema_OK, range(len(jsons_schema_OK))):
            print(f"     {nr}. {schema_ok['file_path']}")
    else:
        print(f"W katalogu {json_path} wśród plików {mask} nie ma poprawnych plików!")


# Definiowanie świata
world_name ='world_DragonStory' #
world_source = jsons_schema_OK[get_quest_nr(world_name, jsons_schema_OK)]
world = world_source['json'][0]["LSide"]["Locations"]
destinations_change_to_nodes(world)

# Definiowanie produkcji
productions_to_match = jsons_schema_OK[get_quest_nr('quest_DragonStory',jsons_schema_OK)]['json'] + jsons_schema_OK[get_quest_nr('produkcje_generyczne',jsons_schema_OK)]['json']  # generyczne i produkcja DragonStory

for production in productions_to_match:
    destinations_change_to_nodes(production["LSide"]["Locations"])

# Dopasowanie
print("#"*30)
print("Co może zrobić Main hero:")

character_name = 'Main_hero'
character_paths = breadcrumb_pointer(world, name_or_id=character_name)
character = character_paths[0][-1]
main_location = character_paths[0][-2]
productions_matched, todos = what_to_do(world, main_location, productions_to_match, character=character)

print("#########################")
print("Co może zrobić Main hero:")
if not productions_matched:
    print(f"Nie udało się dopasować produkcji do postaci {character} w świecie.")
else:
    print(f"Z {len(productions_to_match)} produkcji udało się dopasować {len(todos)}. Wizualizacje znajdują się w "
      f"katalogu: ../production_match/out/")

# generowanie podsumowania znalezionych dopasowań
offset = 0
for nr in range(len(productions_to_match)):  #[14:]
    if len(todos) > nr - offset and productions_to_match[nr]['Title'] == todos[nr - offset]['Title']:
        print(f"{nr:02d}/{nr - offset:02d}. {productions_to_match[nr]['Title'].split(' / ')[0]}")
        print(f"       {len(todos[nr - offset]['Matches'])} wariantów: ", end="")
        used_nodes = {}
        for node in todos[nr - offset]['Matches'][0]:
            used_nodes[node[0].get('Id',node[0].get('Name'))] = set()
        for variant in todos[nr - offset]['Matches']:
            for node in variant:
                used_nodes[node[0].get('Id', node[0].get('Name'))].add(id(node[1]))
        for node_name in used_nodes:
            print(f"{node_name} – {len(used_nodes[node_name])}", end=", ")
        print()
    else:
        print(f"{nr:02d}/--. {productions_to_match[nr]['Title'].split(' / ')[0]}")
        print("       nie pasuje")
        offset += 1


# generowanie obrazków dopasowania ls do świata. Wszystkie warianty w podkatalogu o kolejnym nr + nazwie produkcji
if True:
    gv = GraphVisualizer()
    date_folder = str(datetime.now().strftime("%Y%m%d%H%M%S"))

    for production, nr in zip(todos, range(len(todos))):
        for match_list, nr2 in zip(production['Matches'], range(len(production['Matches']))):
            red_nodes = []
            red_edges = []
            comments = {'color':'red'}
            for node in match_list:
                red_nodes.append(id(node[1]))
                if 'Connections' in node[0]:
                    for dest in node[0]['Connections']:
                        for any_node in match_list:
                            if any_node[0] is dest['Destination']:  # zm
                                red_edges.append((id(node[1]), id(any_node[1])))
                id_to_comment = node[0].get('Id')
                if id_to_comment:
                    comments[id(node[1])] = id_to_comment

            d_title = production["Title"]
            d_desc = f"Dopasowanie produkcji w świecie, wariant {nr2:03d}"
            d_file = f'match_{nr2:03d}'
            d_dir = f'../production_match/out/find_productions_to_perform_{date_folder}/{nr:03d}_{production["Title"].split(" / ")[0].replace("’", "")}'

            draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)

