
import datetime
import logging
import os
import sys

from copy import copy, deepcopy

from config.config import path_root
from library.tools import *

from library.tools_match import character_turn, world_turn
from library.tools_process import game_init, looking_for_main_character, game_over, save_world_game, \
    ids_list_update
from library.tools_validation import get_jsons_storygraph_validated


logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s', stream=sys.stdout)


# wgrywanie jsonów
dir_name = 'productions'  #    przykłady do testowania dopasowań
json_path = f'{path_root}/{dir_name}'
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path)


# ######################################################
# definicje
# definiowanie świata
world_name = 'World_PWK2021_base_grupa10'  # '05_swiat_prison''World_PWK2021_base_grupa10v1''World_PWK2020_base_q2020-12''World_PWK2020_q13''World_PWK2021_q17_v2_w_trakcie_3''20220317215747_World_PWK2021_base_q17_v2_w_trakcie' 'World_PWK2020_q07'
# definiowanie misji
quest_names = ['misja_10', 'misja_10_generyczne'] # '05_Wszystkie_Produkcje_q05', '05_Produkcje_Generyczne_q05','quest12_2' 'produkcje_generyczne_q09''quest2020-13_Help_in_the_field''quest_17''quest07_Hacking_in_Inn, 'quest07_automatic', 'produkcje_automatyczne_quest_18'
quest_automatic_names = []  # '05_Produkcje_Automatyczne_q05'
# definiowanie głównego bohatera
character_name = 'Main_hero'  # 'Rumcajs'
# ###########################################