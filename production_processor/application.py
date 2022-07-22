
import datetime
import logging
import os
import sys

from copy import copy, deepcopy

from config.config import path_root
from library.tools import *

from library.tools_match import character_turn, world_turn, get_production_tree_new
from library.tools_process import game_init, looking_for_main_character, game_over, save_world_game, \
    ids_list_update, get_quest_description
from library.tools_validation import get_jsons_storygraph_validated


logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s', stream=sys.stdout)


# wgrywanie jsonów
dir_name = ''  #
json_path = f'{path_root}/{dir_name}'
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path)


# ######################################################
# definicje
# definiowanie świata
world_name = 'world_DragonStory'   #'world_RumcajsStory'
# definiowanie misji
quest_names = ['quest_DragonStory'] #'quest_RumcajsStory_close'
quest_automatic_names = []  #
# definiowanie głównego bohatera
character_name = 'Main_hero'  # 'Rumcajs'
# ######################################################



# świat z naszego katalogu
world_source = jsons_schema_OK[get_quest_nr(world_name, jsons_schema_OK)]

# świat z innego źródła
# gp = json.load(open(f'../production_match/out/process-20220202100653/quest00_Dragon_story_World_PWK2021_base_20220202100653_IGG.json', encoding="utf8"))
# world_source = {'file_path': 'Światy/World_PWK2021_base.json', 'json': gp["WorldSource"]}

world = world_source['json'][0]["LSide"]["Locations"]
world_nodes_list = nodes_list_from_tree(world, "Locations")
world_nodes_ids_list = [str(id(x['node'])) for x in world_nodes_list]
world_nodes_ids_pairs_list = [(str(id(x['node'])), x['node']) for x in world_nodes_list]
world_nodes_dict = {}

for node in world_nodes_list:
    world_nodes_dict[id(node)] = node
world_locations_ids = []
for l in world:
    world_locations_ids.append(id(l))
destinations_change_to_nodes(world, world=True)

quest_description = get_quest_description(quest_names[0] or '')



# pobieranie produkcji zserializowanych
prod_chars_turn_names = ['produkcje_generyczne', *quest_names]
prod_world_turn_names = [*quest_automatic_names, 'produkcje_automatyczne', 'produkcje_automatyczne_wygrywania']



prod_chars_turn_jsons = [deepcopy(jsons_schema_OK[get_quest_nr(x,jsons_schema_OK)]['json']) for x in prod_chars_turn_names]
prod_world_turn_jsons = [deepcopy(jsons_schema_OK[get_quest_nr(x,jsons_schema_OK)]['json']) for x in prod_world_turn_names]

# scalanie i rozwijanie destynacji w produkcjach
productions_chars_turn_to_match = []
productions_world_turn_to_match = []
for prods in prod_chars_turn_jsons:
    for prod in prods:
        productions_chars_turn_to_match.append(prod)
        if not destinations_change_to_nodes(prod["LSide"]["Locations"]):
            exit(1)
for prods in prod_world_turn_jsons:
    for prod in prods:
        productions_world_turn_to_match.append(prod)
        if not destinations_change_to_nodes(prod["LSide"]["Locations"]):
            exit(1)


# definiowanie struktur pomocniczych
decision_nr = 0
date_folder = str(datetime.now().strftime("%Y%m%d%H%M%S"))
script_root_path = os.getcwd().rsplit(os.sep, 1)[0]
gp_folder = 'gameplays'
result_file_path = f'{script_root_path}/{gp_folder}/gp-{date_folder}'

# zaczynamy
print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════════
║ S Y M U L A T O R    P R O C E S U    D E C Y Z Y J N E G O    G R A C Z A    R P G
║
║ Proces decyzyjny fabuły zdefiniowanej w świecie: {world_name}
║ poprzez produkcje generyczne i misję: {quest_names[0]}
║ dla bohatera: {character_name}.
║ Wizualizacje kolejnych możliwości wyboru i wykonanych produkcji znajdują się w katalogu: 
║ {result_file_path}
║
║ UWAGA1: Aplikacja działa w trybie testera, czyli można wykonywać produkcje przesłonięte 
║ parametrem Override mimo ich oznaczenia: BLOKADA1, BLOKADA2.
║ UWAGA2: Działa dość wolno, bo generuje mnóstwo obrazków pomocniczych.
╚═══════════════════════════════════════════════════════════════════════════════════════════
""")



gameplay = {
    "Player": input("Podaj nazwę gracza: "),
    "MainCharacter": character_name,
    "WorldName": world_name,
    "WorldSource": save_world_game(world_source),  # stan świata z id lokacji będących stringiem z adresu pamięci
    "QuestName": quest_names[0],
    "QuestSource": [{x: jsons_schema_OK[get_quest_nr(x,jsons_schema_OK)]['json']} for x in prod_chars_turn_names],
    "WorldResponseSource": [{x: jsons_schema_OK[get_quest_nr(x,jsons_schema_OK)]['json']} for x in prod_world_turn_names],
    # "WorldResponseSource": [{x: y} for x, y in zip(prod_world_turn_names, prod_world_turn_jsons)],
    "DateTimeStart": datetime.now().strftime("%Y%m%d%H%M%S"),
    # "AllNodes": world_nodes_ids_list,
    "Moves": [],
    "FilePath": result_file_path,

}

game_init(gameplay)

# sprawdzamy, gdzie jest główny bohater
character_paths = looking_for_main_character(gameplay, world, name=character_name, failure_text="Kończymy zanim zaczęliśmy, przy inicjacji.")
character = character_paths[0][-1]

line_limit = 81
print(f'     ┌──────────────────────────────────────────────────────────────────────────────────────')
print_lines(quest_description, line_limit, prefix = '     │ ')
print(f'     └──────────────────────────────────────────────────────────────────────────────────────')

prod_hierarchy, g, m = get_production_tree_new(*[jsons_schema_OK[get_quest_nr(x,jsons_schema_OK)] for x in prod_chars_turn_names + prod_world_turn_names])
gameplay["ProductionHierarchy"] = prod_hierarchy

while True:  # dopóki nie zakończymy, będziemy aplikować kolejne produkcje

    # sprawdzamy, gdzie jest główny bohater
    character_paths = looking_for_main_character(gameplay, world, pointer=character, zero_text="Zniknął główny bohater po ruchu NPC-a. Pewno zginął.")
    main_location = character_paths[0][0]
    skip = False
    sheaf_description(main_location)

    # wykonujemy ruch gracza
    if len(character_paths[0]) == 2:
        effect_main = character_turn(gameplay, world, world_source, main_location, productions_chars_turn_to_match, decision_nr, character=character)
    else:
        print(f"Bohater jest podporządkowany innej postaci lub uwięziony({str([x.get('Name') for x in character_paths[0]]).replace(', ','->')}). Odzyska samostanowienie, gdy stanie na własnych nogach w lokacji.")
        effect_main = ""
    if effect_main == "end":
        game_over(gameplay, "Decyzja użytkownika")
    elif effect_main == "":
        pass
    else:
        decision_nr += 1
        ids_list_update(world_nodes_ids_list, world_nodes_ids_pairs_list, effect_main)
        effect_world, decs_world = world_turn(gameplay, effect_main, world, world_locations_ids, productions_world_turn_to_match, decision_nr)
        decision_nr = decs_world
        ids_list_update(world_nodes_ids_list, world_nodes_ids_pairs_list, effect_world)

        # sprawdzamy, gdzie jest główny bohater
        character_paths = looking_for_main_character(gameplay, world, pointer=character, zero_text="Zniknął główny bohater po swoim ruchu. Pewno umarł.")
        main_location = character_paths[0][-2]


    # wykonujemy ruchy NPC-ów
    char_nr = sum([len(loc["Characters"]) if "Characters" in loc else 0 for loc in world])
    print("\n########## UWAGA: teraz można wybrać działania wszystkich NPC-ów w świecie. ################")
    print("########## Strasznie upierdliwe, ale niekiedy niezbędne. ###################################")
    print("0 – nie wykonuj żadnych akcji postaci niezależnych,")
    print("1 – przegląd postaci po kolei poczynając od bieżącej lokacji (można przerwać w trakcie),")
    print("2 – wskazanie konkretnych postaci.")
    while True:
        decision = input("Co wybierasz? ")
        if decision == "0":
            skip = True
            print("########## NIE BĘDZIEMY ODWALAĆ PRACY ZA NPC-e #############################################")
            print("############################################################################################")
            break
        elif decision == "1":
            break
        if decision == "2":
            print("Przykro mi, jeszcze nie działa.")

    if skip:
        continue

    loc_list = copy(world)
    try:
        loc_list.remove(main_location)
    except:
        pass
    loc_list = [main_location] + loc_list
    loc_index = 0
    for loc in loc_list:
        if loc.get('Characters'):
            loc_index += 1
            chars_list = copy(loc["Characters"])
            if character in chars_list:
                try:
                    chars_list.remove(character)
                except:
                    pass

            char_index = 1 if len(chars_list) != 1 else None
            skip = False
            if len(chars_list) == 0:
                print(f'W lokacji {main_location.get("Name")} nie ma żadnej postaci poza głównym bohaterem.')
                continue

            sheaf_description(loc)

            for char in chars_list:
                   # mógł go ktoś zabić          # nie jest głównym bohaterem
                if char in loc["Characters"] and char is not character:
                    effect_npc = character_turn(gameplay, world, world_source, loc, productions_chars_turn_to_match, decision_nr, character=char, char_index=char_index, loc_index =loc_index, npc=True )
                    if char_index is not None:
                        char_index += 1
                    if effect_npc == "end":
                        skip = True
                        break
                    elif effect_npc == "":
                        print("Nic.")
                        continue
                    else:
                        decision_nr += 1
                        ids_list_update(world_nodes_ids_list, world_nodes_ids_pairs_list, effect_npc)
                        effect_world, decs_world = world_turn(gameplay, effect_npc, world, world_locations_ids, productions_world_turn_to_match, decision_nr)
                        decision_nr = decs_world
                        ids_list_update(world_nodes_ids_list, world_nodes_ids_pairs_list, effect_world)
            if skip:
                break
    print("########## KONIEC ODWALANIA PRACY ZA NPC-e #################################################")
    print("############################################################################################")
    print()



