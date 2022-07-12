
import datetime
import logging
import sys
from copy import deepcopy
import os

from config.config import path_root
from library.tools import *

from library.tools_process import cut_unnecessary_world_elements, save_world, add_node, \
    find_node_from_input, add_attributes_from_input, remove_node, find_layer_from_input
from library.tools_visualisation import draw_graph
from library.tools_validation import name_in_allowed_names, get_jsons_storygraph_validated


logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s', stream=sys.stdout)

dir_name = '' #
json_path = f'{path_root}/{dir_name}'
script_root_path = os.getcwd().rsplit("/", 1)[0]


# jsons_OK, jsons_schema_OK, errors = import_jsons(dir_name, schema_name, '*.json', only_schema= True)
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path)

######################################
# Tutaj ustalamy parametry wejściowe #
######################################
# Definiowanie świata
world_name = 'world_DragonStory'  # 'world_RumcajsStory'
world_source = jsons_schema_OK[get_quest_nr(world_name, jsons_schema_OK)]
world = world_source['json'][0]["LSide"]["Locations"]
if not destinations_change_to_nodes(world, world=True):
    exit(1)

modification_date = datetime.now()
date_folder = str(modification_date.strftime("%Y%m%d%H%M%S"))

mandatory_attr = {'Characters': {"HP": 100, "Money": 10}, 'Items': {"Value": 5}}

# gv = GraphVisualizer()
comments = None
decision_nr = 0
decision_list = []

# zaczynamy
print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════════
║ M O D Y F I K A C J A    S T R U K T U R Y    Ś W I A T A
║
║ Modyfikacja świata pobranego z pliku: {world_name}
║ Wizualizacje kolejnych możliwości wyboru i wykonanych produkcji znajdują się w katalogu: 
║ {json_path}. 
║ Tam też zostanie zapisany końcowy plik JSON i odpowiadający m PNG.
║ Pliki pomocnicze (wizualizacje każdej zmiany) znajdują się w katalogu:
║ tamże w podkatalogu: {world_name}_{date_folder}.
║ 
║ UWAGA1: Nazwy postaci i lokacji zdefiniowane są w katalogu:
║ {script_root_path}/json_validation/allowed_names.
║ Nazwy atrybutów wymagane są w formacie PascalCase, ale sprawdza to dopiero walidator. 
║ UWAGA2: Działa bardzo wolno, bo generuje mnóstwo obrazków pomocniczych.
╚═══════════════════════════════════════════════════════════════════════════════════════════
""")

print(f"### Co może zrobić projektant ze światem: {world_name}")
print(f'00. Usuń niepotrzebne węzły')
print(f'01. Dodaj węzeł')
print(f'02. Usuń węzeł')
print(f'03. Przenieś węzeł')
print(f'04. Zmień nazwę węzła')
print(f'05. Zmień atrybuty węzła')
print(f'06. Dodaj połączenie między lokacjami')
print(f'07. Usuń połączenie między lokacjami')
print(f'08. Dodaj obiekty z misji (jeszcze nie działa)')
# print(f'08. Uzupełnij wymagane atrybuty domyślnymi wartościami ({mandatory_attr}')
print(f'save – zapisz świat')
print(f'end – zakończ')

# print(f"Wizualizacje zmian znajdują się w katalogu: ../{json_path}/{world_name}_{date_folder}. Widok końcowy będzie "
#       f"w katalogu ../{json_path}.")

d_title = world_name
d_desc = f'Stan świata w dniu {modification_date.strftime("%d.%m.%Y godz. %H:%M:%S")}'
d_file = f'{world_name}_{decision_nr:03d}_original'
d_dir = f'{json_path}/{world_name}_{date_folder}'
draw_graph(world, d_title, d_desc, d_file, d_dir)



while True:  # dopóki nie zakończymy, będziemy aplikować kolejne działania
    decision_nr += 1
    chosen_action = ''

    while True:  # pozyskujemy od użytkownika informację o wyborze działania
        print('\n0 – usuń wiele, 1 – dodaj, 2 – usuń, 3 – przenieś, 4 – zmień nazwę, 5 – zmień atrybuty')
        print('6 – dodaj połączenie, 7 – usuń połączenie, 8 – dodaj obiekty z misji, 9 – uzupełnij wymagane atrybuty, save, end')
        decision = (input(f'Które działanie wybierasz: '))
        if  decision.lower() == 'end':
            exit(0)
        if  decision.lower() == 'save':
            print('\nZapisywanie pliku świata.')
            save_date = datetime.now()
            name_comment = input(f'\nNazwa pliku: {world_name}_ + {save_date.strftime("%Y%m%d%H%M%S")} lub końcówka (enter, jeśli pusta): ')
            full_name = f'{world_name}_{name_comment or save_date.strftime("%Y%m%d%H%M%S")}.json'
            save_world(world_source, f'{json_path}', full_name)
            print(f"Zapisano świat w katalogu: {json_path}.")

            d_title = 'Świat gry'
            d_desc  = f'Stan świata w dniu {save_date.strftime("%d.%m.%Y godz. %H:%M:%S")}'
            d_file  = f'{world_name}_{name_comment or save_date.strftime("%Y%m%d%H%M%S")}'
            d_dir   = f'{json_path}'
            draw_graph(world, d_title, d_desc, d_file, d_dir)

        try:
            chosen_action = int(decision)
        except:
            continue
        if chosen_action in range(10):
            break

    if chosen_action == 0:  # Usuń niepotrzebne węzły
        red_nodes = cut_unnecessary_world_elements(world)

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po hurtowym usunięciu węzłów.'
        d_file  = f'{world_name}_{decision_nr:03d}_cut_unnecessary'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)


    elif chosen_action == 1:  # Dodaj węzeł
        target_paths = []
        target_layer = find_layer_from_input("Podaj warstwę docelową („Locations”, „Characters”, „Items”, „Narration”): ")
        if not target_layer:
            continue
        if not target_layer == 'Locations':
            filename = f'{world_name}_{decision_nr:03d}_'
            directory = f'{json_path}/{world_name}_{date_folder}'
            target_paths = find_node_from_input(world, "Podaj multireferencję do rodzica: ", choose_one=True, f=filename, d=directory)
            if not target_paths:
                continue

        node_name = input("Podaj nazwę węzła (z dozwolonego zakresu): ")
        if not name_in_allowed_names(node_name, target_layer):
            print("Nazwa węzła spoza dozwolonego zakresu.")
            continue
        node = {"Name": node_name, "Attributes": {}}
        new_attr, stop_flag = add_attributes_from_input()
        node['Attributes'] = new_attr
        if target_layer == 'Locations':
            world.append(node)
            red_nodes = [id(node)]
        else:
            red_nodes = add_node(node, target_paths[0][-1], target_layer)

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po dodaniu węzła {node.get("Name")}'
        d_file  = f'{world_name}_{decision_nr:03d}_add_node'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)


    elif chosen_action == 2:  # Usuń węzeł
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        node_to_remove_paths = find_node_from_input(world, "Podaj multireferencję do węzła do usunięcia: ", choose_one=True, f=filename, d=directory)
        if not node_to_remove_paths:
            continue
        if len(node_to_remove_paths[0]) == 1:
            for location in world:
                if 'Connections' in location:
                    for nr, dest in enumerate(location['Connections']):
                        if dest['Destination'] is node_to_remove_paths[0][-1]:  # zm
                            del location['Connections'][nr]
                            break
            world.remove(node_to_remove_paths[0][-1])
        else:
            remove_node(node_to_remove_paths[0][-1], node_to_remove_paths[0][-2])

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po usunięciu węzła {node_to_remove_paths[0][-1].get("Name")}'
        d_file  = f'{world_name}_{decision_nr:03d}_remove_node'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir)


    elif chosen_action == 3:  # Przenieś węzeł
        red_nodes = []
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        node_to_move_paths = find_node_from_input(world, "Podaj multireferencję do węzła do przesunięcia: ", choose_one=True, f=filename, d=directory)
        if not node_to_move_paths:
            continue
        if len(node_to_move_paths[0]) == 1:
            print("Nie można przesunąć lokacji.")
            continue
        target_layer = find_node_layer_name(node_to_move_paths[0][-2], node_to_move_paths[0][-1])
        target_paths = find_node_from_input(world, "Podaj multireferencję do węzła docelowego: ", choose_one=True, f=filename, d=directory)
        if not target_paths:
            continue

        if node_to_move_paths[0][-1] in target_paths[0]:
            print("Nie można przenieść węzła do samego siebie ani do jego dzieci.")
            continue

        if remove_node(node_to_move_paths[0][-1], node_to_move_paths[0][-2]):
            red_nodes = add_node(node_to_move_paths[0][-1], target_paths[0][-1], target_layer)

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po przesunięciu węzła {node_to_move_paths[0][-1].get("Name")}'
        d_file  = f'{world_name}_{decision_nr:03d}_move_node'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)


    elif chosen_action == 4:  # zmień nazwę węzła
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        node_to_change_paths = find_node_from_input(world, "Podaj multireferencję do węzła: ", choose_one=True, f=filename, d=directory)
        if not node_to_change_paths:
            continue
        if len(node_to_change_paths[0]) == 1:
            target_layer = 'Locations'
        else:
            target_layer = find_node_layer_name(node_to_change_paths[0][-2], node_to_change_paths[0][-1])
        node_name = input("Podaj nazwę węzła (z dozwolonego zakresu): ")
        if not name_in_allowed_names(node_name, target_layer):
            print("Nazwa węzła spoza dozwolonego zakresu.")
            continue
        node_to_change_paths[0][-1]['Name'] = node_name
        red_nodes = [id(node_to_change_paths[0][-1])]

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po zmianie nazwy węzła {node_to_change_paths[0][-1].get("Name")}'
        d_file  = f'{world_name}_{decision_nr:03d}_change_name'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)


    elif chosen_action == 5:  # Zmień atrybuty węzła
        red_nodes = []
        attrs_to_change_paths = []
        # TODO dodać sprawdzanie poprawności nazwy atrybutu (pascal case)
        print("Zmiana atrybutów węzłów wskazanych przez multireferencję lub nazwę atrybutu.")
        param = input("Podaj multireferencję do węzła lub nazwę szukanego atrybutu: ")
        node_to_change_paths = find_reference_leaves_single_graph(world, param)
        if not node_to_change_paths:
            attrs_to_change_paths = breadcrumb_pointer(world, attr={param: None})

        if node_to_change_paths:
            how_many = len(node_to_change_paths)

            if how_many > 1:
                print(f'Znaleziono {how_many} węzłów. Będą pokazywane po kolei.')
                print(f"Rysunek z ponumerowanymi węzłami jest w katalogu: ../{json_path}/{world_name}_{date_folder}.")
                comments = {'color': 'red'}
                for nr, path in enumerate(node_to_change_paths):
                    print(f'{nr:03d}. {node_description(world, path)}')
                    comments[id(path[-1])] = nr

                d_title = f'Stan świata pomocniczy'
                d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                          f'ze wskazaniem niejednoznacznego wyboru.'
                d_file  = f'{world_name}_{decision_nr:03d}_{node_to_change_paths[0][-1].get("Name")}_nodes_to_choose'
                d_dir   = f'{json_path}/{world_name}_{date_folder}'
                draw_graph(world, d_title, d_desc, d_file, d_dir, comments)
                comments = {}


            print()
            print(f"Wszystkie węzły o podanej nazwie/ścieżce/atrybucie będą po kolei wyświetlane.")
            print(f"Wpisz enter{', aby przejść do następnego węzła, ' if how_many > 1 else ''} lub „end”, aby przerwać.")
            print()
            print(f"Aby zmienić/dodać/usunąć atrybut podaj jego nazwę i wartość. Nazwa atrybutu w PascalCase.")
            print(f"Wartość jako liczba (jeśli zmiennoprzecinkowa, to z kropką), tekst, true/false lub „unset”, aby usunąć atrybut.")

            print()
            for nr, path in enumerate(node_to_change_paths):
                node = path[-1]
                many_nodes_comment = f"{nr:03d}. " if how_many > 1 else ''
                print(f'{many_nodes_comment}{node_description(world, path)}')
                # if node.get('Attributes'):
                #     # print(f'     Obecne atrybuty węzła {node.get("Name")} to:')
                #     print(f'     Atrybuty: {node["Attributes"]}')
                # else:
                #     print(f'     Obecnie węzeł {node.get("Name")} nie ma atrybutów.')
                new_attr, stop_flag = add_attributes_from_input()
                if 'Attributes' not in node:
                    node['Attributes'] = new_attr
                else:
                    for k, v in new_attr.items():
                        if v == "unset":
                            try:
                                del(node['Attributes'][k])
                            except:
                                pass
                        else:
                            node['Attributes'][k] = v
                if new_attr:
                    red_nodes.append(id(node))
                if stop_flag:
                    break
        elif attrs_to_change_paths:
            how_many = len(attrs_to_change_paths)
            if how_many > 1:
                print(f'Znaleziono {how_many} węzłów. Będą pokazywane po kolei.')
                print(f"Rysunek z ponumerowanymi węzłami jest w katalogu: ../{json_path}/{world_name}_{date_folder}.")
                comments = {'color': 'red'}
                for nr, path in enumerate(attrs_to_change_paths):
                    print(f'{nr:03d}. {node_description(world, path)}')
                    comments[id(path[-1])] = nr

                d_title = 'Stan świata pomocniczy'
                d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                          f'ze wskazaniem niejednoznacznego wyboru.'
                d_file  = f'{world_name}_{decision_nr:03d}_{param}_nodes_to_choose'
                d_dir   = f'{json_path}/{world_name}_{date_folder}'
                draw_graph(world, d_title, d_desc, d_file, d_dir, comments)
                comments = {}

            print(f"Podaj nową wartość atrybutu węzła albo wpisz enter{', aby przejść do następnego węzła, ' if how_many > 1 else ''} lub „end”, aby przerwać.")
            print(f"Wartość jako liczba (jeśli zmiennoprzecinkowa, to z kropką), tekst, true/false lub „unset”, aby usunąć atrybut.")
            print()
            for nr, path in enumerate(attrs_to_change_paths):
                node = path[-1]
                many_nodes_comment = f"{nr:03d}. " if how_many > 1 else ''
                print(f'{many_nodes_comment}{node_description(world, path)}')
                attr_value = None
                new_attr = input(f"Nowa wartość atrybutu {param} = ")
                if new_attr.lower() == 'end':
                    break
                if new_attr.lower() == '':
                    continue
                elif new_attr.lower() == 'true':
                    node["Attributes"][param] = True
                elif new_attr.lower() == 'false':
                    node["Attributes"][param] = False
                elif new_attr.lower() == 'unset':
                    del (node['Attributes'][param])
                else:
                    try:
                        attr_value = int(new_attr)
                    except:
                        try:
                            attr_value = float(new_attr)
                        except:
                            pass
                    if attr_value is None:
                        attr_value = new_attr
                    node["Attributes"][param] = attr_value

                red_nodes.append(id(node))

        else:
            print(f"Nie ma ani węzła ani atrybutu o nazwie „{param}”.")
            continue

        # print(f'Po zmianie atrybuty węzła {node.get("Name")} to:')
        # print(f'{node["Attributes"]}')
        desc = ''
        if node_to_change_paths:
            if len(red_nodes) > 1:
                desc = f'atrybutów {len(red_nodes)} węzłów {node_to_change_paths[0][-1].get("Name")}'
            else:
                desc = f'atrybutów węzła {node_to_change_paths[0][-1].get("Name")}'
        elif attrs_to_change_paths:
            if len(red_nodes) > 1:
                desc = f'atrybutu {param} w {len(red_nodes)} węzłach'
            else:
                desc = f'atrybutu {param} w {len(red_nodes)} węźle'

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po zmianie {desc}'
        d_file  = f'{world_name}_{decision_nr:03d}_change_attr'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)


    elif chosen_action == 6:  # Dodaj połączenie między lokacjami
        red_nodes = []
        red_edges = []
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        source_paths = find_node_from_input(world, "Podaj multireferencję do lokacji źródłowej: ", choose_one=True, f=filename, d=directory)
        if not source_paths:
            print("Nie znaleziono takiej lokacji.")
            continue
        if len(source_paths[0]) > 1:
            print("Źródłowy węzeł nie jest lokacją.")
            continue
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        target_paths = find_node_from_input(world, "Podaj multireferencję do lokacji docelowej: ", choose_one=True, f=filename, d=directory)
        if not target_paths:
            print("Nie znaleziono takiej lokacji.")
            continue
        if len(target_paths[0]) > 1:
            print("Docelowy węzeł nie jest lokacją.")
            continue
        if source_paths[0][-1] is target_paths[0][-1]:
            print("Nie można połączyć lokacji samej ze sobą.")
            continue

        if len(target_paths[0]) == 1:
            nonexistent = True
            if 'Connections' in source_paths[0][-1]:
                for dest in source_paths[0][-1]['Connections']:
                    if dest['Destination'] == target_paths[0][-1]:
                        nonexistent = False
            if nonexistent:
                if 'Connections' not in source_paths[0][-1]:
                    source_paths[0][-1]['Connections'] = []
                source_paths[0][-1]['Connections'].append({'Destination': target_paths[0][-1]})
                red_nodes = [id(source_paths[0][-1]), id(target_paths[0][-1])]
                red_edges = [(id(source_paths[0][-1]), id(target_paths[0][-1]))]
            else:
                print("Takie połączenie już istnieje.")
                red_edges = []
                red_nodes = []

        d_title = world_name
        d_desc  = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                  f'po dodaniu połączenia między {source_paths[0][-1].get("Name")} a {target_paths[0][-1].get("Name")}'
        d_file  = f'{world_name}_{decision_nr:03d}_add_conn'
        d_dir   = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges)


    elif chosen_action == 7:  # Usuń połączenie między lokacjami
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        source_paths = find_node_from_input(world, "Podaj multireferencję do lokacji źródłowej: ", choose_one=True, f=filename, d=directory)
        if not source_paths[0]:
            continue
        if len(source_paths[0]) > 1:
            print("Źródłowy węzeł nie jest lokacją.")
            continue
        filename = f'{world_name}_{decision_nr:03d}_'
        directory = f'{json_path}/{world_name}_{date_folder}'
        target_paths = find_node_from_input(world, "Podaj multireferencję do lokacji docelowej: ", choose_one=True, f=filename, d=directory)
        if not target_paths:
            continue
        if len(target_paths[0]) > 1:
            print("Docelowy węzeł nie jest lokacją.")
            continue
        if len(target_paths[0]) == 1:
            for nr, dest in enumerate(source_paths[0][-1]['Connections']):
                if dest['Destination'] is target_paths[0][-1]:  # zm
                    del source_paths[0][-1]['Connections'][nr]
                    break

        d_title = world_name
        d_desc = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
                 f'po usunięciu połączenia między węzłami {source_paths[0][-1].get("Name")} i {target_paths[0][-1].get("Name")}'
        d_file = f'{world_name}_{decision_nr:03d}_remove_conn'
        d_dir  = f'{json_path}/{world_name}_{date_folder}'
        draw_graph(world, d_title, d_desc, d_file, d_dir)


    # elif chosen_action == 9:  # Uzupełnij wymagane atrybuty domyślnymi wartościami
    #     continue
    #     world_nodes = nodes_list_from_tree(world, "Locations")
    #     print("Domyślne wartości obowiązkowych atrybutów:")
    #     print(mandatory_attr)
    #
    #     red_nodes = add_mandatory_attributes(world_nodes, mandatory_attr)
    #
    #     d_title = world_name
    #     d_desc = f'Stan świata w dniu {datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ' \
    #              f'po dodaniu domyślnych wartości obowiązkowych atrybutów.'
    #     d_file = f'{world_name}_{decision_nr:03d}_add_mandatory'
    #     d_dir = f'{json_path}/{world_name}_{date_folder}'
    #     draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes)
    #
    # elif chosen_action == 8:  # Uzupełnij świat obiektami wymaganymi w misji
    #
    #     json_schema_path = f'{path_root}/schema/schema_updated_20220213.json'
    #     dict_schema_path = f'{path_root}/schema/schema_sheaf_updated_20220213.json'
    #     dir_name = 'productions'  # przykłady do testowania dopasowań
    #     json_path = f'{path_root}/{dir_name}'
    #     jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path, json_schema_path,
    #                                                                                  dict_schema_path)
    #
    #     while True:  # pozyskujemy od użytkownika informację o wyborze misji
    #         quest_name = input(f'Podaj nazwę misji: ')
    #         quest_json = jsons_schema_OK[get_quest_nr(quest_name, jsons_schema_OK)]['json']
    #         if quest_json:
    #             break
    #
    #     while True:  # pozyskujemy od użytkownika informację o wyborze misji
    #         character_name = input(f'Podaj nazwę głównego bohatera: ')
    #         character_paths =  breadcrumb_pointer(world, name_or_id=character_name)
    #         if len(character_path) == 1:
    #             break
    #     main_location = character_paths[0][-2]
    #     character = character_paths[0][-1]
    #
    #
    #     for production in quest_json:
    #         nodes_list = nodes_list_from_tree(production["LSide"])
    #         param_instr_from_nodes_list(nodes_list, "sheaf")
    #
    #
    #         print(production["Title"])
    #         prod_name = production["LSide"][0].get("Name")
    #         if prod_name != main_location.get("Name")
    #
    #
    #         if remove_node(node_to_move_paths[0][-1], node_to_move_paths[0][-2]):
    #             red_nodes = add_node(node_to_move_paths[0][-1], target_paths[0][-1], target_layer)
    #
    #
    #
    #     # productions_matched, todos = what_to_do(world, main_location, productions_to_match, character=character)
    #

