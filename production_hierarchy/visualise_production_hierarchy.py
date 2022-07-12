import logging
import sys


from config.config import path_root



# wgrywanie jsonów do testów

#################################################################
from library.tools import get_quest_nr, draw_production_tree
from library.tools_match import check_hierarchy, get_production_tree_new

from library.tools_validation import get_jsons_storygraph_validated

mask = '*.json'
# mask = 'World_pptx_base.json'
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s', stream=sys.stdout)
#################################################################

# jsons_OK, jsons_schema_OK, errors = get_files_validated(json_path, json_schema_path, mask)
# json_schema_path = f'../json_validation/schema_updated_20220213.json'
# dict_schema_path = f'../json_validation/schema_sheaf_updated_20220213.json'
dir_name = ''
json_path = f'{path_root}/{dir_name}'
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path)



########################################################################################################################
# Testy generowania drzewa produkcji ###################################################################################
production_hierarchy_tests = True
if production_hierarchy_tests:
    # get_production_tree('prod_generyczne_nowe_Dragon_story',
    #                     jsons_schema_OK[get_quest_nr('produkcje_generyczne',jsons_schema_OK)]['json'],
    #                     jsons_schema_OK[get_quest_nr('produkcje_automatyczne',jsons_schema_OK)]['json'],
    #                     jsons_schema_OK[get_quest_nr('quest00_Dragon_story',jsons_schema_OK)]['json'])

    jsons_list = []
    for quest_json in jsons_schema_OK:
        # get_production_tree(f'hierarchia_produkcji_{json["file_path"].split("/")[-1].rsplit(".",1)[0]}',
        #                     jsons_schema_OK[get_quest_nr('produkcje_generyczne', jsons_schema_OK)]['json'],
        #                     json['json'])

        prod_hierarchy, g, m = get_production_tree_new(jsons_schema_OK[get_quest_nr('produkcje_generyczne', jsons_schema_OK)], quest_json)

        # print(f'### {quest_json["file_path"]}')
        # print(f'Wszystkie produkcje: {len(prod_hierarchy)}')
        # print(f'Produkcje mające rodzica: {len([x for x in prod_hierarchy if prod_hierarchy[x].get("parent") in prod_hierarchy])}.')
        # print(
        #     f'Produkcje najwyższego poziomu: {len([x for x in prod_hierarchy if prod_hierarchy[x].get("parent") == "root"])}.')

        # for p, v in prod_hierarchy.items():
        #     if v["parent"] in prod_hierarchy:
        #         check_hierarchy(prod_hierarchy[v["parent"]]["prod"], v["prod"])


        if prod_hierarchy:
            draw_production_tree(prod_hierarchy, missing=m, mission_name=f'hierarchia_produkcji_{quest_json["file_path"].split("/")[-1].rsplit(".",1)[0]}')


    # # jedno wielkie drzewo
    # prod_hierarchy, g, m = get_production_tree_new(*jsons_schema_OK)
    # if prod_hierarchy:
    #         draw_production_tree(prod_hierarchy, missing=m, mission_name=f'hierarchia_produkcji_all')


        # jsons_list.extend(json['json'])

    # get_production_tree('prod_generyczne_nowe_wszystkie', jsons_list)