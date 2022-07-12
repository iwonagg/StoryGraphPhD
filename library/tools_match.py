import datetime
import inspect
import re
from copy import copy, deepcopy
from itertools import product
from typing import Union, Tuple, List

import ctypes

import os

from library.tools import breadcrumb_pointer, list_from_tree, find_reference_leaves, \
    eval_expression_po_rozmowie_z_Wojtkiem, action_description, sheaf_description, world_copy, \
    destinations_change_to_nodes
from library.tools_process import save_world, apply_instructions_to_world, draw_variants_graphs, \
    dict_from_variant, get_reds
from library.tools_visualisation import draw_graph


def neighbours_mismatch_removal(matches: list, ls_node_match: dict, w_node: dict, single_match: bool = True, test_mode = False) -> bool:
    """
    NEW Narrows down the potential matches lists using the property of neighbourhood
    :param matches: Production list of LS nodes
    :param ls_node_match: Particular element of the list above to compare with W element
    :param w_node: W element to compare with LS element
    :param single_match: Indicator if the compared pair is the unique match or not
    :return: True of False. More important is action taken during the function performance
    :param test_mode: indicates if some announcements will be printed
    """
    error_log = ''
    ls_node = ls_node_match['ls_node']

    # inicjowanie tabeli węzłów
    ls_nodes_with_ls_names = {}
    ls_names_count = {}
    w_nodes_with_ls_names = {}
    w_names_count = {}
    ls_id_nodes = []
    w_unused_nodes = []

    # obie porównywane lokacje mają sąsiadów i liczba sąsiadów w świecie jest większa lub równa
    if ls_node.get('Connections') and w_node.get('Connections') and len(ls_node['Connections']) <= len(w_node['Connections']):

        # tworzymy słownik sąsiedztwa LS
        for dest in ls_node['Connections']:
            current_name = dest['Destination'].get('Name')
            if current_name:
                if current_name not in ls_nodes_with_ls_names:
                    ls_nodes_with_ls_names[current_name] = [nd['Destination'] for nd in ls_node['Connections'] if nd['Destination'].get('Name') == current_name]
                    ls_names_count[current_name] = len(ls_nodes_with_ls_names[current_name])
            else:
                ls_id_nodes.append(dest['Destination'])

        # tworzymy słownik sąsiedztwa W i uściślamy dopasowania nazw do części wspólnej ze słownikami
        for dest in w_node['Connections']:
            current_name = dest['Destination'].get('Name')
            if current_name in ls_nodes_with_ls_names:
                if current_name not in w_nodes_with_ls_names:
                    w_nodes_with_ls_names[current_name] = [nd['Destination'] for nd in w_node['Connections'] if nd['Destination'].get('Name') == current_name]
                    w_names_count[current_name] = len(w_nodes_with_ls_names[current_name])

                    if ls_names_count[current_name] > w_names_count[current_name]:
                        error_log += f"Sąsiedzi węzłów {ls_node.get('Id', ls_node.get('Name'))} i " \
                              f"{w_node.get('Id', w_node.get('Name'))} nie pasują do siebie, bo w lewej stronie jest więcej" \
                              f" dzieci „{current_name}”.\n"
                        try:
                            ls_node_match['w_nodes_list'].remove(w_node)
                        except:
                            error_log += "Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata.\n"

                    elif ls_names_count[current_name] == w_names_count[current_name]:
                        for neighbour in matches:
                            if neighbour.get('Name') == current_name:
                                intersection = [nd for nd in neighbour['w_nodes_list'] if nd in w_nodes_with_ls_names[current_name]]
                                if single_match:
                                    neighbour['w_nodes_list'] = intersection
                                if len(intersection) == 0:
                                    error_log += f"Węzeł {neighbour['ls_node'].get('Id', neighbour['ls_node'].get('Name'))} " \
                                          f"nie spełnia warunku sąsiedztwa z węzłem {w_node.get('Id', w_node.get('Name'))}" \
                                          f" jako węzłem {ls_node.get('Id', ls_node.get('Name'))}."
                                    try:
                                        ls_node_match['w_nodes_list'].remove(w_node)
                                    except:
                                        error_log += "Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata."
                                    return False
                                elif len(intersection) == 1 and single_match:
                                    neighbours_mismatch_removal(matches, neighbour, neighbour['w_nodes_list'][0], single_match=True)

                    else: # jest <, czyli któryś z węzłów może posłużyć jako odpowiednik id
                        w_unused_nodes.extend(w_nodes_with_ls_names[current_name])
            else:
                w_unused_nodes.append(dest['Destination'])

        # uściślamy dopasowania nazw do części wspólnej z niedopasowanymi jednoznacznie węzłami z W
        for neighbour in matches:
            if neighbour['ls_node'] in ls_id_nodes:
                intersection = [nd for nd in neighbour['w_nodes_list'] if nd in w_unused_nodes]
                if single_match:
                    neighbour['w_nodes_list'] = intersection
                if len(intersection) == 0:
                    error_log += f"Węzeł {neighbour['ls_node'].get('Id', neighbour['ls_node'].get('Name'))} \
                          nie spełnia warunku sąsiedztwa z węzłem {w_node.get('Id', w_node.get('Name'))} \
                          jako węzłem {ls_node.get('Id', ls_node.get('Name'))}."
                    try:
                        ls_node_match['w_nodes_list'].remove(w_node)
                    except:
                        error_log += "Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata."
                        print("Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata.")
                    return False
                elif len(intersection) == 1 and single_match and len([x for x in inspect.stack(0) if x.function == 'neighbours_mismatch_removal']) < 100:
                    neighbours_mismatch_removal(matches, neighbour, neighbour['w_nodes_list'][0], single_match=True)

    # w produkcji i w świecie są sąsiedzi, ale w świecie za mało
    elif ls_node.get('Connections') and w_node.get('Connections') and len(ls_node['Connections']) > len(w_node['Connections']):
        error_log += f"Dopasowanie „{ls_node.get('Name', ls_node.get('Id')), w_node.get('Name')}” jest niemożliwe, bo w produkcji \
              mamy więcej sąsiadów niż w świecie."
        try:
            ls_node_match['w_nodes_list'].remove(w_node)
        except:
            error_log += "Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata."
            print("Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata.")
        return False

    # w produkcji są sąsiedzi, w świecie nie ma, czyli błąd
    elif 'Connections' in ls_node and ls_node['Connections']:
        error_log += f"Dopasowanie „{ls_node.get('Name',ls_node.get('Id')), w_node.get('Name')}” jest niemożliwe, bo \
        w produkcji mamy niepustą listę sąsiadów a w świecie nie."
        try:
            ls_node_match['w_nodes_list'].remove(w_node)
        except:
            error_log += "Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata."
            print("Coś poszło bardzo nie tak z usuwaniem niepasującego węzła świata.")
        return False

    # w produkcji nie ma sąsiadów, czyli funkcja niczego nie uściśli, ale niczego nie wyklucza
    return True


def fit_properties(ls_element: dict, world_element: dict, test_mode: bool = False) -> bool:
    """
    NEW Check if parameters of two nodes fit: name, attributes
    :param ls_element: node from the production
    :param world_element: node from the world
    :return: True or False
    :param test_mode:
    """
    error_log = ''

    if 'Name' in ls_element and world_element.get('Name') != ls_element['Name']:
        error_log += f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match'])-1} rzędu: \
              {ls_element['Name']} i {world_element.get('Name')} nie pasują do siebie."
        return False

    if 'Attributes' in ls_element and ls_element['Attributes']:
        if 'Attributes' not in world_element:
            error_log += f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match'])-1} rzędu: \
                  {ls_element.get('Id', ls_element.get('Name'))} ma atrybuty {ls_element['Attributes']} a \
                  {world_element.get('Name')} nie ma."
            return False
        for attr, v in ls_element['Attributes'].items():
            if attr not in world_element['Attributes']:
                error_log += f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match']) - 1} \
                rzędu: {ls_element.get('Id', ls_element.get('Name'))} ma atrybut {attr} o wartości {v} a \
                {world_element.get('Name')} nie ma."
                return False
            if v is not None and v != world_element['Attributes'][attr]:
                error_log += f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match']) - 1} \
                rzędu: {ls_element.get('Id', ls_element.get('Name'))} ma atrybut \
                    {attr} o wartości {v} a {world_element.get('Name')} ma {world_element['Attributes'].get(attr)}."
                return False



    return True


def node_and_children_match(parent_ls: dict, parent_w: dict, character: Union[str, dict]=None, test_mode: bool = None) -> Tuple[bool, list]:
    """
    NEW Checks if the properties of given pair of nodes fits, match their children and recursively checks their matches
    :param parent_ls: production element of given pair
    :param parent_w: world element of given pair
    :param character: the node given as the object of the production
    :return: True or False
    """
    error_log = ''
    # sprawdzanie własności węzłów rodzicielskich
    if not fit_properties(parent_ls, parent_w):
        return False, []

    objects_indicated = []
    is_object_indicated = False
    if character:
        # wyszykuję w snopku świata bohatera, jeśli był wskazany stringiem
        if type(character) == str:
            initial_paths = breadcrumb_pointer(parent_w, name_or_id=character, layer='Characters')
            if initial_paths and len(initial_paths) == 1:
                character = initial_paths[0][-1]
            else:
                error_log =f"Wskazanie głównego bohatera „{character}” nie jest jednoznaczne!"
                return False, []
        # sprawdzam, czy w produkcji główny bohater jest jednoznacznie wskazany
        if parent_ls.get('Characters'):
            objects_indicated = [nd for nd in parent_ls.get('Characters') if nd.get('IsObject') == True]
            # if len(objects_indicated) >= 1:
            #     is_object_indicated = True
            # elif len(objects_indicated) == 0:
            #     is_object_indicated = False
        # else:
        #     print(f"Wskazanie podmiotu produkcji nie jest jednoznaczne!")
        #     return False, []

    matches = []


    for layer in ['Characters', 'Items', 'Narration']:
        if layer not in parent_ls or len(parent_ls[layer]) == 0:
            continue  # jest w porządku, lecimy do następnej warstwy
        if layer in parent_ls and len(parent_ls[layer]) > 0:
            if layer not in parent_w or len(parent_w[layer]) < len(parent_ls[layer]):
                error_log =f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match']) - 1} \
                rzędu: {parent_ls.get('Id', parent_ls.get('Name'))} ma dzieci w warstwie {layer} a \
                {parent_w.get('Name')} nie ma lub ma za mało."
                return False, []

        # inicjowanie tabeli węzłów
        ls_nodes = parent_ls[layer]
        w_nodes = parent_w[layer]
        ls_nodes_with_ls_names = {}
        ls_names_count = {}
        w_nodes_with_ls_names = {}
        w_names_count = {}

        # tworzenie słownika węzłów o identycznym name i liczenie ich
        for node in ls_nodes:
            current_name = node.get('Name')
            if current_name and current_name not in ls_nodes_with_ls_names:
                ls_nodes_with_ls_names[current_name] = [nd for nd in ls_nodes if nd.get('Name') == current_name]
                ls_names_count[current_name] = len(ls_nodes_with_ls_names[current_name])
                w_nodes_with_ls_names[current_name] = [nd for nd in w_nodes if nd.get('Name') == current_name]
                w_names_count[current_name] = len(w_nodes_with_ls_names[current_name])
                if ls_names_count[current_name] > w_names_count[current_name]:
                    error_log =f"Potomek {len([x for x in inspect.stack(0) if x.function == 'node_and_children_match']) - 1} \
                    rzędu: „{parent_ls.get('Id', parent_ls.get('Name'))}” nie pasuje do „{parent_w.get('Name')}”, \
                    bo w lewej stronie jest więcej dzieci „{current_name}”."
                    return False, []

        # dodawanie do tabeli dzieci
        for node in ls_nodes:
            data = {'ls_node': node, 'w_nodes_list': []}
            # dopasowanie gracza do podmiotu produkcji
            if node.get('IsObject') and len(objects_indicated) == 1:
                data['w_nodes_list'] = [character]
                is_object_indicated = True
            # dopasowanie węzłów po znanych nazwach
            elif 'Name' in node:
                data['w_nodes_list'].extend(w_nodes_with_ls_names[node['Name']])
                # ponieważ główny bohater może być przypisany arbitralnie, to usuwamy go z listy potencjalnych dopasowań
                # innych lokacji o tej samej nazwie
                if character and is_object_indicated and node['Name'] == character.get('Name'):
                    data['w_nodes_list'].remove(character)
            matches.append(data)

        # wykluczanie z listy nieużywanych lokacji tych, które muszą być użyte, ponieważ produkcja wykorzystuje
        # wszystkie wystąpienia danej nazwy w snopku świata
        all_unused_nodes = copy(w_nodes)
        if character and len(objects_indicated) == 1:
            try:
                all_unused_nodes.remove(character)
            except:
                pass
        for examined_name in ls_nodes_with_ls_names:
            if ls_names_count[examined_name] == w_names_count[examined_name]:
                for node in w_nodes_with_ls_names[examined_name]:
                    try:
                        all_unused_nodes.remove(node)  # było: node['w_nodes_list'][0])
                    except:
                        pass


        # uzupełnianie listy alternatyw dla węzłow, których nie dało się niczym ograniczyć
        for node in matches:
            if 'w_nodes_list' not in node or node['w_nodes_list'] == []:
                node['w_nodes_list'] = copy(all_unused_nodes)


    # tworzenie listy list (dla każdego dziecka) list (wariantów dopasowań jego dzieci) tupli dopasowań
    current_matches = []
    if len(matches) == 0:
        # return False, []  # TODO: przetestować
        pass

    for node in matches:
        if 'w_nodes_list' in node and len(node['w_nodes_list']) > 0:
            extended_children_list = []
            error_list = []
            for possible_node in node['w_nodes_list']:
                fitting, fitting_result = node_and_children_match(node['ls_node'], possible_node, character=character)  # fitting_nodes będzie listą list tupli
                if fitting:
                    if fitting_result:
                        for package in fitting_result:
                            if len(package) == len(list_from_tree(node['ls_node']))-1: # trzeba przetestować ten dodatkowy warunek
                                extended_children_list.append([(node['ls_node'], possible_node)] + package)
                    else:
                        if len(list_from_tree(node['ls_node'])) == 1:
                            extended_children_list.append([(node['ls_node'], possible_node)])
                else:
                    error_list.append(possible_node)  # dodane, przetestować
            for e in error_list:  # dodane, przetestować
                node['w_nodes_list'].remove(e) # dodane, przetestować
            if not node['w_nodes_list']:
                error_log += f"Węzeł {node['ls_node'].get('Id', node['ls_node'].get('Name'))} nie ma żadnych dopasowań \
                w snopku świata."
                return False, []

            if not extended_children_list:
                error_log += f"Węzeł {node['ls_node'].get('Id', node['ls_node'].get('Name'))} nie ma żadnych dopasowań \
                w snopku świata."
                return False, []


            else:
                current_matches.append(extended_children_list)
        else:
            error_log += f"Węzeł {node['ls_node'].get('Id', node['ls_node'].get('Name'))} nie ma żadnych dopasowań \
                  w snopku świata."
            return False, []


    cartesian_product = product(*current_matches)
    list_from_cartesian_product = []
    list_from_cartesian_product_no_duplicates = []
    for result in cartesian_product:
        # list_from_cartesian_product.append(list(result))
        list_from_tuple = []
        for f in result:
            list_from_tuple.extend(f)
        list_from_cartesian_product.append(list_from_tuple)


    # usuwanie wariantów odwołujących się do wielokrotnie do tego samego węzła świata
    # i niespełniających wymogu dopasowana głównego bohatera
    for package in list_from_cartesian_product:
        w_nodes = []
        w_objects = []
        ls_nodes = []
        for element in package:
            # ls_nodes_set.append(id(element[0]))
            w_nodes.append(id(element[1]))
            if element[0].get("IsObject"):
                w_objects.append(id(element[1]))
        if len(set(w_nodes)) == len(w_nodes):
            if character and  len(objects_indicated) >= 1:
                if id(character) in w_objects:
                    list_from_cartesian_product_no_duplicates.append(package)
            else:
                list_from_cartesian_product_no_duplicates.append(package)


    if len(list_from_cartesian_product_no_duplicates) == []:
        error_log =f"Po usunięciu wariantów odwołujących się do wielokrotnie do tego samego węzła świata i niespełniających \
              wymogu dopasowana głównego bohatera nie został ani jeden wariant."
        return False, []




    # absolutnie roboczo:
    if list_from_cartesian_product_no_duplicates == [[]]:
        list_from_cartesian_product_no_duplicates == []
        # return False, []
    if list_from_cartesian_product_no_duplicates == [[[]]]:
        list_from_cartesian_product_no_duplicates == []
        # return False, []




    return True, list_from_cartesian_product_no_duplicates


def find_matches_in_world(world: Union[list, dict], world_main_location:dict, prod: dict, test_mode=False, character=None):
    """

    :param world:
    :param world_main_location:
    :param character:
    :param prod:
    :param test_mode:
    :return:
    """
    error_log = ''
    error_log =f"### {prod['Title'].split(' / ')[0]} ###"
    # inicjowanie tabeli lokacji dla produkcji
    ls_locations = prod['LSide']['Locations']
    ls_main_location = ls_locations[0]
    ls_nodes_with_ls_names = {}
    ls_names_count = {}
    w_nodes_with_ls_names = {}
    w_names_count = {}

    matches = []

    # dodawanie do tabeli lokacji tej lokacji, w której znajduje się postać-sprawca
    data = {}
    if 'Name' not in ls_main_location or ls_main_location['Name'] == world_main_location.get('Name'):
        data['w_nodes_list'] = [world_main_location]
        data['ls_node'] = ls_main_location
        matches.append(data)
    else:  # name jest, ale się nie zgadza
        error_log =f"Produkcja „{prod['Title'].split(' / ')[0]}” nie może zostać zastosowana, bo lokacja główna jest \
              podana explicite: „{ls_main_location['Name']}” i nie jest to: „{world_main_location.get('Name')}”."
        return False, []

    # liczenie lokacji
    production_impossible = False
    for location in ls_locations:
        current_name = location.get('Name')
        if current_name and current_name not in ls_nodes_with_ls_names:
            ls_nodes_with_ls_names[current_name] = [loc for loc in ls_locations if loc.get('Name') == current_name]
            ls_names_count[current_name] = len(ls_nodes_with_ls_names[current_name])
            w_nodes_with_ls_names[current_name] = [loc for loc in world if loc.get('Name') == current_name]
            w_names_count[current_name] = len(w_nodes_with_ls_names[current_name])
            if ls_names_count[current_name] > w_names_count[current_name]:
                error_log =f"Produkcja „{prod['Title'].split(' / ')[0]}” nie może zostać zastosowana, bo jest w niej \
                      więcej lokacji „{current_name}” niż w świecie."
                production_impossible = True
                break

    if production_impossible:
        return False, []

    # dodawanie do tabeli lokacji pozostałych lokacji
    for location in ls_locations[1:]:
        data = {'ls_node': location, 'w_nodes_list': []}
        # dopasowanie węzłów po znanych nazwach
        if 'Name' in location:
            data['w_nodes_list'].extend(w_nodes_with_ls_names[location['Name']])
            # ponieważ główna lokacja jest przypisana arbitralnie, to usuwamy ją z listy potencjalnych dopasowań
            # innych lokacji o tej samej nazwie
            if location['Name'] == world_main_location.get('Name'):  # przetestować! było: location['Name'] == ls_main_location
                try:
                    data['w_nodes_list'].remove(world_main_location) # przetestować! było: .remove(ls_main_location)
                except:
                    pass
        matches.append(data)

    # wykluczanie z listy nieużywanych lokacji tych, które muszą być użyte, ponieważ produkcja wykorzystuje
    # wszystkie wystąpienia danej nazwy w świecie
    all_unused_locations = copy(world)
    try:
        all_unused_locations.remove(matches[0]['w_nodes_list'][0])
    except:
        print(f"Nie udało się usunąć węzła{matches[0]['w_nodes_list'][0] if len(matches) else ' z pustej tablicy matches'}.")
    for examined_name in ls_nodes_with_ls_names:
        if ls_names_count[examined_name] == w_names_count[examined_name]:
            # try:
            #     all_unused_locations.remove(location['w_nodes_list'][0]) # to chyba bzdura
            # except:
            #     pass
            for node in w_nodes_with_ls_names[examined_name]:
                try:
                    all_unused_locations.remove(node)  # było: node['w_nodes_list'][0])
                except:
                    pass

    # wykluczanie z listy nieużywanych lokacji tych, które są już dopasowane jednoznacznie
    # UWAGA: TO CHYBA NIE JEST POTRZEBNE, PONIEWAŻ NA RAZIE NIE ROZWIĄZALIŚMY ŻADNEJ LOKACJI POZA TYMI,
    # KTÓRE SĄ POJEDYNCZE W ŚWIECIE I PRODUKCJI
    # for location in matches:
    #     if 'w_nodes_list' in location and len(location['w_nodes_list']) == 1:
    #         try:
    #             all_unused_locations.remove(location['w_nodes_list'][0])
    #         except:
    #             pass

    # uzupełnianie listy alternatyw dla lokacji, których nie dało się niczym ograniczyć
    for location in matches:
        if 'w_nodes_list' not in location or location['w_nodes_list'] == []:
            location['w_nodes_list'] = copy(all_unused_locations)

    # uściślanie dopasowań na podstawie sąsiadów lokacji znanych (wariant A)
    for location in matches:
        if 'w_nodes_list' in location and len(location['w_nodes_list']) == 1:
            neighbours_mismatch_removal(matches, location, location['w_nodes_list'][0])

    # usuwanie potencjalnych dopasowań, których sąsiedztwo nie zawiera sąsiedztwa wymaganego w produkcji (wariant B)
    for location in matches:
        if 'w_nodes_list' in location and len(location['w_nodes_list']) > 1:
            for possible_node in location['w_nodes_list']:
                neighbours_mismatch_removal(matches, location, possible_node, single_match=False)
                # przykład, na którym sprawdzałam:
                # 'Lokacja_A', [{'Destination': 'Lokacja_B'}]
                # "Inn" [{'Destination': 'Road'}, {'Destination': 'Pasture'}]
                # 'Lokacja_B', [{'Destination': 'Lokacja_A'}]
                # "Pasture" [{'Destination': 'Road'}, {'Destination': 'Village'}]
                # "Road" [{'Destination': 'Forest'}, {'Destination': 'Inn'}, {'Destination': 'Pasture'}, {'Destination': 'Village'}, {'Destination': 'Wizards_hut'}]

    # usuwanie węzłów, których atrybuty, liczba dzieci etc nie pasują.
    current_matches = []
    for location in matches:
        if 'w_nodes_list' in location:
            extended_children_list = []
            error_list = []
            for possible_node in location['w_nodes_list']:
                #
                fitting, fitting_result = node_and_children_match(location['ls_node'], possible_node,
                                                                  character=character)  # fitting_nodes będzie listą list tupli
                if fitting:
                    if fitting_result:
                        for package in fitting_result:
                            if len(package) == len(list_from_tree(location['ls_node'])) - 1:  # trzeba przetestować ten dodatkowy warunek
                                extended_children_list.append([(location['ls_node'], possible_node)] + package)

                    else:
                        if len(list_from_tree(location['ls_node'])) == 1:  # trzeba przetestować ten dodatkowy warunek
                            extended_children_list.append([(location['ls_node'], possible_node)])
                else:
                    error_list.append(possible_node) # dodane, przetestować
            for e in error_list: # dodane, przetestować
                location['w_nodes_list'].remove(e)
            if not location['w_nodes_list']: # dodane, przetestować
                error_log += f"Produkcja „{prod['Title'].split(' / ')[0]}” nie może zostać zastosowana, bo właśnie \
                                    usuwamy ostatnie dopasowanie lokacji „{location['ls_node'].get('Id', location['ls_node'].get('Name'))}”."
                production_impossible = True
                break
            if not extended_children_list:

                if len(location['w_nodes_list']) == 1:  # TODO: trzeba sprawdzić, czy ten if jest potrzebny
                    error_log += f"Produkcja „{prod['Title'].split(' / ')[0]}” nie może zostać zastosowana, bo właśnie \
                    usuwamy ostatnie dopasowanie lokacji „{location['ls_node'].get('Id', location['ls_node'].get('Name'))}”."
                    production_impossible = True
                    break
                else:
                    error_log += f" Co prawda usuwamy dopasowanie lokacji \
                    {location['ls_node'].get('Id', location['ls_node'].get('Name'))}, ale jakieś chyba jeszcze mamy."

            else:
                current_matches.append(extended_children_list)
    if production_impossible:
        return False, []

    cartesian_product = product(*current_matches)
    list_from_cartesian_product = []
    # for result in cartesian_product:
    #     list_from_cartesian_product.append(list(result))

    for result in cartesian_product:
        # list_from_cartesian_product.append(list(result))
        list_from_tuple = []
        for f in result:
            list_from_tuple.extend(f)
        list_from_cartesian_product.append(list_from_tuple)

    list_from_cartesian_product_no_duplicates = []
    for package, nr in zip(list_from_cartesian_product, range(len(list_from_cartesian_product))):
        w_nodes_ids = []
        # ls_nodes_ids = []
        for element in package:
            # ls_nodes_ids.append(id(element[0]))
            # print(f"{element[0].get('Id',element[0].get('Name'))}={str(id(element[1]))[-3:]}, ", end="")
            w_nodes_ids.append(id(element[1]))
        # print(f"\n{nr:02d}: {len(set(w_nodes_ids)):02d}, {len(w_nodes_ids):02d}, {len(ls_nodes_ids)}, {len(set(ls_nodes_ids))}")
        if len(set(w_nodes_ids)) == len(w_nodes_ids):
            list_from_cartesian_product_no_duplicates.append(package)


    # robocze wypisywanie dopasowań
    if test_mode:
        print(prod['Title'].split("/")[0])
        for m in matches:
            print('     ', end='')
            if 'Id' in m['ls_node']:
                print('id =', m['ls_node']['Id'], end=', ')
            else:
                print('brak id', end=', ')
            if 'Name' in m['ls_node']:
                print('name =', m['ls_node']['Name'], end=', ')
            else:
                print('brak name', end=', ')
            if 'w_nodes_list' in m:
                print('names = ', end='')
                for n in m['w_nodes_list']:
                    print(n['Name'], end=', ')
        print()


    return True, list_from_cartesian_product_no_duplicates


def verify_matches_with_preconditions(prod, matches_to_verify_preconditions: list, test_mode=False):

    # inicjowanie tabeli lokacji dla produkcji
    ls_locations = prod['LSide']['Locations']
    ls_preconditions = prod.get('Preconditions')
    expressions_split = []
    matches_verified_with_preconditions =[]


    for package in matches_to_verify_preconditions:
        verification = True
        for element in ls_preconditions:
            if 'Cond' in element:
                if not eval_expression_po_rozmowie_z_Wojtkiem(element['Cond'], package):
                    verification = False
                    break
            elif 'Count' in element:
                lower_limit = element.get('Min')
                upper_limit = element.get('Max')
                counted_nodes = find_reference_leaves(ls_locations, package, element['Count'])
                if lower_limit is not None and len(counted_nodes) < lower_limit:
                    verification = False
                    break
                if upper_limit is not None and len(counted_nodes) > upper_limit:
                    verification = False
                    break
            else:
                print("Nierozpoznane wyrażenie.")
        if verification:
            matches_verified_with_preconditions.append(package)

    if matches_verified_with_preconditions:
        return True, matches_verified_with_preconditions
    else:
        return False, []


def what_to_do(world: Union[list, dict], main_location: dict, production_list: list, character=None,
               test_mode=False, prod_vis_mode = False) -> (bool,list):
    """
    Match productions to the world given to find the set of applicable productions.
    :param world: The graph of the actual world state
    :param character: The character to be the object of the action (most often the main hero), given as name or node pointer
    :param production_list: The list of productions to match
    :param test_mode: The indicator of error status printing
    :return: True or False to indicate if production matching was possible and list of matched productions.
    """

    # # sprawdzanie wstępnych warunków rozpoczęcia dopasowań i inicjacja
    # if type(character) == str:
    #     initial_paths = breadcrumb_pointer(world, name_or_id=character, layer='Characters')
    #     if len(initial_paths) == 1:
    #         world_main_location = initial_paths[0][-2]
    #         character = initial_paths[0][-1]
    #     else:
    #         print(f"Wskazanie głównego bohatera „{character}” w świecie nie jest jednoznaczne!")
    #         return False, []
    # else:
    #     initial_paths = breadcrumb_pointer(world, pointer=character, layer='Characters')
    #     if len(initial_paths) == 1:
    #         world_main_location = initial_paths[0][-2]
    #     else:
    #         print(f"Wskazanie głównego bohatera „{character['Name']}” w świecie nie jest jednoznaczne!")
    #         return False, []
    if character:
        initial_paths = breadcrumb_pointer(world, pointer=character, layer='Characters')
        if len(initial_paths) == 1:
            world_main_location = initial_paths[0][-2]
        else:
            print(f"Wskazanie głównego bohatera „{character.get('Name')}” w świecie nie jest jednoznaczne!")
            return False, []
        if world_main_location is not main_location:
            print(f"Wskazanie głównego bohatera „{character.get('Name')}” w świecie nie jest jednoznaczne!")
            return False, []
    else:
        world_main_location = main_location


    all_matches = []

    for prod in production_list:

        # robocze usuwanie produkcji schematowych
        if 'Comment' in prod and "Użyto „?”" in prod['Comment'] and not prod_vis_mode:
            continue

        # szukanie dopasowań lewej strony produkcji do świata
        matches_OK, matches_to_verify_preconditions = find_matches_in_world(world, world_main_location, prod, test_mode, character=character)
        if not matches_OK:
            continue
        # testowe
        for variant in matches_to_verify_preconditions:
            ls_len = len(list_from_tree(prod['LSide']))
            variant_len = len(variant)
            if ls_len != variant_len:
                print(f'Coś poszło nie tak: dopasowano {variant_len} węzłów do {ls_len} węzłów do produkcji {prod["Title"].split(" / ")[0]}.')

        # sprawdzanie predykatów stosowalności
        if not prod_vis_mode:
            if prod.get('Preconditions'):
                matches_OK, matches_verified_with_preconditions = verify_matches_with_preconditions(prod, matches_to_verify_preconditions)
            else:
                matches_verified_with_preconditions = matches_to_verify_preconditions
        else:
            # if prod.get('Preconditions'):
            #     pass
            #     compare_preconditions(prod, matches_to_verify_preconditions)
            #     matches_verified_with_preconditions = matches_to_verify_preconditions
            #     # sprawdzić, czy preconditions pasują i instrukcje pasują
            # else:
            #     # sprawdzić, czy instrukcje pasują
            matches_verified_with_preconditions = matches_to_verify_preconditions
        if not matches_OK:
            continue

        matched_prod = prod.copy()
        matched_prod['Matches'] = matches_verified_with_preconditions

        all_matches.append(matched_prod)

    return True, all_matches


def make_automatic_moves(gameplay, world, loc, productions_to_match, decision_nr, visualise = True):
    test_mode = False
    red_nodes = []

    # znajdowanie dopasowań LS
    productions_matched, todos = what_to_do(world, loc, productions_to_match)
    if not productions_matched:
        print(f'Nie udało się dopasować produkcji automatycznych w lokacji {loc.get("Name")}.')
        return []
    else:
        if len(todos) == 0:
            return []
        # else:
        #     print(f'Z {len(productions_to_match)} produkcji udało się dopasować {len(todos)} w lokacji {loc.get("Name")}.')

    # generowanie podsumowania znalezionych dopasowań
    offset = 0
    for nr in range(1):  # wykonujemy tylko pierwszą, kiedyś usunę tę pętlę, było: range(len(productions_to_match)[0])
        if len(todos) > nr - offset and productions_to_match[nr]['Title'] == todos[nr - offset]['Title']:
            warning_text = ''
            all_prod_number_text = f"{nr:02d}/" if test_mode else ''

            # if len(prod_dict[productions_to_match[nr]['Title']]['children']) > 1:
            #     for child in prod_dict[productions_to_match[nr]['Title']]['children']:
            #         if prod_dict[child].get('Override') == 1:
            #             warning_text = 'PRZYKRYTA '
            #             break

            print(f"{all_prod_number_text}{nr - offset:02d}. {warning_text}{productions_to_match[nr]['Title'].split(' / ')[0]} – ", end="")
            print(f"{len(todos[nr - offset]['Matches'])} wariantów", end="")
            if test_mode:
                print('(', end='')
                used_nodes = {}
                for node in todos[nr - offset]['Matches'][0]:
                    used_nodes[node[0].get('Id', node[0].get('Name'))] = set()
                for variant in todos[nr - offset]['Matches']:
                    for node in variant:
                        used_nodes[node[0].get('Id', node[0].get('Name'))].add(id(node[1]))
                for node_name in used_nodes:
                    print(f"{node_name}: {len(used_nodes[node_name])}", end=", ")
                print(")")
            else:
                print()
        else:
            if test_mode:
                print(f"{nr:02d}/--. {productions_to_match[nr]['Title'].split(' / ')[0]} – ", end="")
                print("nie pasuje")
            offset += 1


    # nie wybieramy produkcji, bierzemy pierwszą
    nr = 0
    prod = todos[nr]

    # generowanie podsumowania znalezionych wariantów wybranej produkcji
    if len(todos[nr]['Matches']) > 1:
        print(f"Produkcja „{todos[nr]['Title'].split(' / ')[0]}” ma {len(todos[nr]['Matches'])} wariantów.\n", end='')

        if test_mode:
            used_nodes = {}
            for node in todos[nr]['Matches'][0]:
                used_nodes[node[0].get('Id', node[0].get('Name'))] = set()
            for variant in todos[nr]['Matches']:
                for node in variant:
                    used_nodes[node[0].get('Id', node[0].get('Name'))].add(id(node[1]))
            for node_name in used_nodes:
                print(f"{node_name} – {len(used_nodes[node_name])}", end=", ")
            print(' ')

        for variant, variant_nr in zip(prod['Matches'], range(len(prod['Matches']))):
            print(f"{variant_nr:02d}. ", end="")
            for pair in variant:
                print(f'{pair[0].get("Id", pair[0].get("Name"))} = {pair[1].get("Id", pair[1].get("Name"))}, ', end='')
            # if variant_nr < len(prod['Matches'])-1:
            #     print('\n ', end='')
            # else:
                print()
        print("Wybieramy pierwszy wariant.")

    chosen_variant = 0
    variant = todos[nr]['Matches'][chosen_variant]

    # generowanie stanu świata przed zastosowaniem produkcji.
    if visualise:
        red_nodes, red_edges, comments = get_reds(variant)

        d_title = prod["Title"]
        d_desc = f'Dopasowanie produkcji automatycznej w świecie, wariant {chosen_variant:03d}'
        d_file = f'{decision_nr:03d}a_world_before_{prod["Title"].split(" / ")[0].replace("’", "")}'
        d_dir = f'{gameplay["FilePath"]}{os.sep}world_states{os.sep}'

        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)

    # world_before = world_copy(world, deepcopy(world))

    # stosowanie produkcji
    red_nodes_new = apply_instructions_to_world(prod, variant, world)

    if red_nodes_new:
        action_description(prod, variant)
    else:
        print(f'Nie dało się zastosować produkcji {prod["Title"].split(" / ")[0]} do świata. '
              f'Żaden węzeł nie został zmodyfikowany.')
        return False

    # generowanie stanu świata po zastosowaniu produkcji
    if visualise:
        red_nodes.extend(red_nodes_new)
        d_desc = f'Stan świata po zastosowaniu produkcji w wariancie {chosen_variant:03d}'
        d_file = f'{decision_nr:03d}b_world_after_{prod["Title"].split(" / ")[0].replace("’", "")}'

        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)

        d_title = f'Świat w oczekiwaniu na ruch gracza'
        d_desc = f'Pomiędzy kolejnymi produkcjami'
        d_file = f'{decision_nr:03d}c_world_between_moves'

        draw_graph(world, d_title, d_desc, d_file, d_dir)

    world_after = world_copy(world, deepcopy(world))

    gameplay['Moves'].append({
        "ProductionTitle": prod["Title"],
        "Object": "Action automatically performed",
        "LSMatching": dict_from_variant(variant),
        "MatchedProductionListLength": len(todos),
        "MatchedProductionIndex": nr,
        "MatchedVariantListLength": len(todos[nr]['Matches']),
        "MatchedVariantIndex": chosen_variant,
        "ModifiedNodes": red_nodes_new,
        "ModifiedNodesNames": [ctypes.cast(x, ctypes.py_object).value.get("Name") for x in red_nodes_new],
        # "WorldBefore": world_before,
        "WorldAfter": world_after,
        "DateTimeMove": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
    } )

    return red_nodes


def world_turn(gameplay, effect, world, world_ids, productions_automatic_to_match, decision_nr):

    if effect:
        red_nodes = []
        print(f'\n#### Co musi wydarzyć się w świecie po ruchu postaci:')
        for n in effect:
            if n in world_ids: # tylko dla lokacji, które zostały zmienione w poprzednim ruchu
                while True:
                    red_nodes_new = make_automatic_moves(gameplay, world, ctypes.cast(n, ctypes.py_object).value,
                                         productions_automatic_to_match, decision_nr)
                    if red_nodes_new:
                        red_nodes.extend(red_nodes_new)
                        decision_nr += 1
                    else:  # po to dodawaliśmy węzeł rodzica do delete, żeby móc to sprawdzać
                        break
                if red_nodes:
                    sheaf_description(ctypes.cast(n, ctypes.py_object).value)
                else:
                    print(f'Nic w lokacji {ctypes.cast(n, ctypes.py_object).value.get("Name")}.')

    return red_nodes, decision_nr


def character_turn(gameplay, world, world_source, main_location, productions_to_match, decision_nr, character=None, visualise = True, char_index = None, loc_index = None, npc = False):
    test_mode = False
    if npc:
        if loc_index is None:
            loc_text =''
        elif loc_index == 1:
            loc_text = 'bieżącej'
        elif type(loc_index) == int:
            loc_text = f'{loc_index}.'
        else:
            loc_text = ''
        if char_index is not None:
            char_text = f'{char_index}. postać w {loc_text} lokacji – '
        else:
            char_text = f'postać w {loc_text} lokacji – '
    else:
        char_text = ''

    print(f"\n#### Co może zrobić {char_text}{character.get('Name') if type(character) == dict else 'dowolna postać'}:")

    # znajdowanie dopasowań LS
    productions_matched, todos = what_to_do(world, main_location, productions_to_match, character=character)
    if not productions_matched:
        print(f"Nie udało się dopasować produkcji do postaci {character} w świecie.")
        return []
    else:
        print(f"Z {len(productions_to_match)} produkcji udało się dopasować {len(todos)}. ")


    todos_names = [x["Title"] for x in todos]

    # generowanie podsumowania znalezionych dopasowań
    offset = 0
    for nr in range(len(productions_to_match)):  # [14:]
        if len(todos) > nr - offset and productions_to_match[nr]['Title'] == todos[nr - offset]['Title']:
            warning_text = ''  # TODO kiedyś będziemy ostrzegać, czy produkcja nie jest zablokowana przez szczegółową
            all_prod_number_text = f"{nr:02d}/" if test_mode else ''
            cover = ''
            blockades2 = gameplay["ProductionHierarchy"][productions_to_match[nr]['Title']].get("children")
            for ch in blockades2:
                if ch in todos_names and gameplay["ProductionHierarchy"][ch]['prod']['Override'] == 2:
                    cover = 'BLOKADA2 '
            blockades1 = gameplay["ProductionHierarchy"][productions_to_match[nr]['Title']].get("blockades")


            if productions_to_match[nr]['Title'] == "Teleportation / Teleportacja": # ta produkcja blokowana jest zawsze, więc nie musimy sprawdzać
                cover = 'BLOKADA1 '
            elif blockades1:
                for b in blockades1:
                    for v in todos[nr - offset]['Matches']:
                        vb = 0
                        for e1 in b:
                            m = 0
                            for e2 in v:
                                if e1[0] == e2[0]:
                                    if e1[1].get("Name"):
                                        if e1[1].get("Name") == e2[1].get("Name"):
                                            m += 1
                                    if e1[1].get("Attributes") and e2[1].get("Attributes"):
                                        if e1[1]["Attributes"].items() in e2[1]["Attributes"].items():
                                            m += 1
                            if m == len(b):
                                v.append("BLOKADA1 ")
                                vb += 1
                    if vb == len(todos[nr - offset]['Matches']):
                        cover = 'BLOKADA1 '
                    elif vb:
                        cover = 'CZĘŚCIOWA BLOKADA1 '
            elif todos[nr - offset].get('TitleGeneric') and todos[todos_names.index(todos[nr - offset]['TitleGeneric'])]['Matches'][0][-1] == "BLOKADA1 " and todos[nr - offset].get('Override') == 2:
                cover = 'BLOKADA1 '


            print(f"{all_prod_number_text}{nr - offset:02d}. {cover}{warning_text}{productions_to_match[nr]['Title'].split(' / ')[0]} – ", end="")
            print(f"{len(todos[nr - offset]['Matches'])} wariantów", end="")
            if test_mode:
                print('(', end='')
                used_nodes = {}
                for node in todos[nr - offset]['Matches'][0]:
                    used_nodes[node[0].get('Id', node[0].get('Name'))] = set()
                for variant in todos[nr - offset]['Matches']:
                    for node in variant:
                        used_nodes[node[0].get('Id', node[0].get('Name'))].add(id(node[1]))
                for node_name in used_nodes:
                    print(f"{node_name}: {len(used_nodes[node_name])}", end=", ")
                print(")")
            else:
                print()
        else:
            if test_mode:
                print(f"{nr:02d}/--. {productions_to_match[nr]['Title'].split(' / ')[0]} – ", end="")
                print("nie pasuje")
            offset += 1

    # wybór produkcji
    print(f'\n0–{len(todos) - 1} – wybór produkcji, '
          f'enter – opuszczenie kolejki, '
          f'„end” – {"przerwij" if npc else "koniec symulacji"}, '
          f'„save” – zapis świata')
    while True:  # pozyskujemy od użytkownika informację o wyborze produkcji
        decision = input(f'Co robi {char_text}{character.get("Name") or ""}? ')

        if decision.lower() == 'end':
            return "end"
        if decision.lower() == '':
            return ""
        if decision.lower() == 'save':
            save_world(world_source, f'{gameplay["FilePath"]}{os.sep}jsons')
            print(f'Zapisano świat w katalogu: {gameplay["FilePath"]}{os.sep}jsons.')
        if len(decision.split(",")) > 1:
            decision_list = decision.split(",")
            decision = decision_list.pop(0)
        try:
            chosen_production = int(decision)
        except:
            continue
        if chosen_production in range(len(todos)):
            break

    nr = chosen_production
    production = todos[nr]

    # generowanie podsumowania znalezionych wariantów wybranej produkcji
    print(f"\n#### Produkcja „{todos[nr]['Title'].split(' / ')[0]}” ma {len(todos[nr]['Matches'])} wariantów.\n", end='')
    print(f'#### Jeżeli chcesz poznać szczegóły wariantów, wygeneruj wizualizacje (katalog podany u góry).')

    if test_mode:
        used_nodes = {}
        for node in todos[nr]['Matches'][0]:
            used_nodes[node[0].get('Id', node[0].get('Name'))] = set()
        for variant in todos[nr]['Matches']:
            for node in variant:
                used_nodes[node[0].get('Id', node[0].get('Name'))].add(id(node[1]))
        for node_name in used_nodes:
            print(f"{node_name} – {len(used_nodes[node_name])}", end=", ")
        print(' ')

    for variant, variant_nr in zip(production['Matches'], range(len(production['Matches']))):
        print(f"{variant_nr:02d}. {variant[-1] if variant[-1] == 'BLOKADA1 ' else ''}", end="")
        for pair in variant:
            if type(pair) is not str:
                print(f'{pair[0].get("Id", pair[0].get("Name"))} = {pair[1].get("Id", pair[1].get("Name"))}, ', end='')
        # if variant_nr < len(production['Matches'])-1:
        #     print('\n ', end='')
        # else:
        print()

    d_title = production["Title"]
    d_dir   = f'{gameplay["FilePath"]}/{decision_nr:03d}_{production["Title"].split(" / ")[0].replace("’", "")}'


    # potwierdzenie wyboru jedynej produkcji
    if len(todos[nr]["Matches"]) == 1:
        while True:
            print(f't – wykonanie produkcji, enter – opuszczenie kolejki, d – wizualizacja wariantów')
            confirmation = input("Czy chcesz ją wykonać? ")
            if confirmation.lower() in ['n', '']:
                return ''
            elif confirmation.lower() == 'd':
                print("Może trochę potrwać...")
                draw_variants_graphs(todos[nr]['Matches'], world, d_title, d_dir)
            elif confirmation.lower() in ['t', '0']:
                chosen_variant = 0
                variant = todos[nr]['Matches'][chosen_variant]
                break
    else:
        # wybór wariantu produkcji
        # back = False
        print(f'\n0–{len(todos[nr]["Matches"]) - 1} – wybór wariantu, '
              f'enter – opuszczenie kolejki, '
              f'd – wizualizacja wariantów')
        while True:  # pozyskujemy od użytkownika informację o wyborze wariantu produkcji
            decision = input(f'Co konkretnie robi {character.get("Name", "")} w produkcji? ')
            if decision.lower() == '':
                return ''
            if decision.lower() == 'd':
                print("Może trochę potrwać...")
                draw_variants_graphs(todos[nr]['Matches'], world, d_title, d_dir)
            try:
                chosen_variant = int(decision)
            except:
                continue
            if chosen_variant in range(len(todos[nr]["Matches"])):
                break
        # if back:
        #     pass

        variant = todos[nr]['Matches'][chosen_variant]


    # generowanie stanu świata przed zastosowaniem produkcji.
    if visualise:
        red_nodes, red_edges, comments = get_reds(variant)
        d_title = production["Title"]
        for_whom = f" dla {character.get('Name')}" if character else ""
        d_desc = f'Dopasowanie produkcji{for_whom} w świecie, wariant {chosen_variant:03d}'
        d_file = f'{decision_nr:03d}a_world_before_{production["Title"].split(" / ")[0].replace("’", "")}'
        d_dir = f'{gameplay["FilePath"]}/world_states/'

        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)

    # world_before = world_copy(world, deepcopy(world))

    # stosowanie produkcji
    red_nodes_new = apply_instructions_to_world(production, variant, world)
    if red_nodes_new:
        action_description(production, variant)
    else:
        print(f'Nie dało się zastosować produkcji „{production["Title"].split(" / ")[0]}” do świata. '
              f'Żaden węzeł nie został zmodyfikowany.')
        # return []

    # generowanie stanu świata po zastosowaniu produkcji
    if visualise:
        red_nodes.extend(red_nodes_new)
        d_desc = f'Stan świata po zastosowaniu produkcji w wariancie {chosen_variant:03d}'
        d_file = f'{decision_nr:03d}b_world_after_{production["Title"].split(" / ")[0].replace("’", "")}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)

        d_title = f'Świat w oczekiwaniu na ruch gracza'
        d_desc = f'Pomiędzy kolejnymi produkcjami'
        d_file = f'{decision_nr:03d}c_world_between_moves'
        draw_graph(world, d_title, d_desc, d_file, d_dir)

    world_after = world_copy(world, deepcopy(world))
    gameplay['Moves'].append({
        "ProductionTitle": production["Title"],
        "Object": character.get("Name"),
        "LSMatching": dict_from_variant(variant),
        "MatchedProductionListLength": len(todos),
        "MatchedProductionIndex": nr,
        "MatchedVariantListLength": len(todos[nr]['Matches']),
        "MatchedVariantIndex": chosen_variant,
        "ModifiedNodes": red_nodes_new,
        "ModifiedNodesNames": [ctypes.cast(x, ctypes.py_object).value.get("Name") for x in red_nodes_new],
        # "WorldBefore": world_before,
        "WorldAfter": world_after,
        "DateTimeMove": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
    } )

    return red_nodes


def compare_preconditions(parent, child, variant: List[Tuple[dict, dict]]):

    def tulpe_first_order(t: tuple) -> int:
            return len(t[0].get("Id",t[0].get("Name")))

    if "Preconditions" in parent and "Preconditions" in child:
        # precs_p = parent["Preconditions"]

        variant.sort(key=tulpe_first_order)
        for p in parent["Preconditions"]:
            for k in p:
                print(f'Zamiana tupli {k}: {p[k]}')
                for t in variant:
                    p[k].replace(t[0],t[1])
                print(f'Zamiana tupli {k}: {p[k]}')
        c = True
        return c
    elif "Preconditions" in parent and not "Preconditions" in child:
        return False
    else:
        return True


def compare_instructions(parent, child, variant: List[Tuple[dict, dict]]) -> bool:

    def tulpe_first_order(t: tuple) -> int:
            return len(t[0].get("Id",t[0].get("Name")))

    if "Instructions" in parent and "Instructions" in child:

        if len(parent["Instructions"]) > len(child["Instructions"]):
            return False
        variant = copy(variant)
        variant.sort(reverse=True, key=lambda t: len(t[0].get("Id",t[0].get("Name"))))
        for instr_p in parent["Instructions"]:
            instr_p = deepcopy(instr_p)

            # print(f'Zamiana tupli przed: {instr_p}')
            for k, v in instr_p.items():
                if k in["Nodes", "Attribute", "To", "In"]:
                    for t in variant:
                        instr_p[k] = instr_p[k].replace(t[0].get("Id",t[0].get("Name")),t[1].get("Id",t[1].get("Name")))

            # print(f'Zamiana tupli po:    {instr_p}')
            if "?" not in str(instr_p) and instr_p not in child["Instructions"]:
                # print("ni ma!")
                return False
            # elif "?" in str(instr_p):
            #
            #     joint_instr = "".join(f'{child["Instructions"]}')
            #     print(joint_instr)
            #     for s in f'{instr_p}'.split("?"):
            #         print(s)
            #         if s not in joint_instr:
            #             print("ni ma!?")
            #             return False
            #


                # instr_seek = False
                # for instr_ch in child["Instructions"]:
                #     qm_seek = True
                #     for s in str(instr_p).split("?"):
                #         if s not in str(instr_ch):
                #             qm_seek = False
                #     if qm_seek:
                #         instr_seek = True
                # if not instr_seek:
                #     print("ni ma?!")
                #     return False




                #     for k, v in instr_p.items():
                #         if k not in instr_ch:
                #             break
                #         elif k == "Nodes" and v != "?" and v != instr_ch[k]:
                #             break
                #         elif k == "Attribute" and v[-2:] != ".?" and v != instr_ch[k]:
                #             break
                #         elif k == "Attribute" and v[-2:] == ".?" and v[0,-3] != instr_ch[k][0:-3]:
                #             break
                #         else:
                #             seek_ch = True
                #     if seek_ch:
                #         break
                # if not seek_ch:
                #     print("ni ma!")
                #     return False



            # for instr_ch in parent["Instructions"]:
            #     if print(f'Porównanie tupli do: {instr_ch}')
        return True
    elif "Instructions" in parent and not "Instructions" in child:
        return False
    else:
        return True


def check_hierarchy(parent, child, character = None) -> Tuple[str, list]:

    # przygotowuję produkcję do wykonania
    destinations_change_to_nodes(parent["LSide"]["Locations"])
    destinations_change_to_nodes(child["LSide"]["Locations"])
    world = deepcopy(child["LSide"]["Locations"])

    if character:
        # wyszykuję w snopku świata bohatera, jeśli był wskazany stringiem
        if type(character) == str:
            initial_paths = breadcrumb_pointer(world, name_or_id=character, layer='Characters')
            if initial_paths and len(initial_paths) == 1:
                character = initial_paths[0][-1]
            else:
                error_log = f"Wskazanie głównego bohatera „{character}” nie jest jednoznaczne!"
                return 'compare failed', []

    # Trzeba ogarnąć, czy musimy dziedziczyć IsObject, por. Aresztowanie bohatera.
    # dopiero wtedy możemy odkomentować ewentualnie poniższą linijkę
    # character_paths = breadcrumb_pointer(world, is_object=True)
    # if character_paths:
    LS_OK = False
    instr_OK = False
                # character_paths or jeśli zdecydujemy, ze trzeba uwzględniać IsObject
    for path in [[world[0], None]]:
        character = path[-1]
        main_location = path[-2]
        productions_matched, todos = what_to_do(world, main_location, [parent], character=character,
                                                prod_vis_mode=True)

        # print(f"{parent['Title'].split(' / ')[0]} -> {child['Title'].split(' / ')[0]}")
        if not productions_matched:
            ch = character.get("Id", character.get("Name", ""))             # f'postaci {ch}' if character_paths else
            # print(f"Nie udało się dopasować produkcji do { 'żadnej postaci'} w świecie.")
            return 'compare failed', []
        else:
            pass
            # print(                                 # len(character_paths) if character_paths else
            #     f"Z {len([parent])} produkcji dla {'wszystkich'} postaci udało się dopasować {len(todos)}. ")
            for element in todos:
                for e in element["Matches"]:
                    for f in e:
                        pass
                        # print(f'{f[0].get("Id", f[0].get("Name"))}, {f[1].get("Id", f[1].get("Name"))}')
                        # # print(f'aaaa   {str(f)[0:100]}')

            if len(todos):
                LS_OK = True


            for n, elem in reversed(list(enumerate(todos))):
                for nr, e in reversed(list(enumerate(elem["Matches"]))):
                    if compare_instructions(parent, child, e):
                        instr_OK = True
    blockades = []
    if todos:
        for variant in todos[0]["Matches"]:
            blocking_variant = []
            for elem in variant:
                blocking_keys ={}
                if elem[0].get("Id") and elem[1].get("Name"):
                    blocking_keys["Name"] = elem[1].get("Name")
                if elem[1].get("Attributes") and not elem[1].get("Attributes"):
                    blocking_keys["Attributes"] = elem[1].get("Attributes")
                elif  elem[1].get("Attributes") and elem[1].get("Attributes"):
                    blocking_keys["Attributes"] = {}
                    for attr in elem[1].get("Attributes"):
                        if not elem[0]["Attributes"].get(attr) or elem[1]["Attributes"].get(attr) != elem[0]["Attributes"].get(attr):
                            blocking_keys["Attributes"][attr] = elem[1]["Attributes"].get(attr)
                if blocking_keys:
                    blocking_variant.append((elem[0],blocking_keys))
            if blocking_variant:
                blockades.append(blocking_variant)


    if instr_OK:
        return 'OK', blockades
    elif LS_OK:
        return 'Instr mismatch', blockades
    else:
        return "LS mismatch", blockades


    # return 'OK' if instr_OK else LS_OK else 'No LS matches'


def get_production_tree_new(*json_sources):
    parents_set = set()
    root_missing = []
    root_generics = []
    production_dict = {}

    # tworzenie wstępnej listy produkcji bez powiązań
    for json_given in json_sources:
        # wykluczamy światy
        if len(json_given["json"]) == 1 and not json_given["json"][0].get("Instructions"):
            return {}, [], []

        for production in json_given["json"]:
            if production["Title"] in production_dict:
                if production == production_dict[production["Title"]]["prod"]:
                    # print(f"Dwie identyczne (więc nic groźnego) produkcje o tej samej nazwie: „{production['Title']}” "
                    #     f"w plikach „{production_dict[production['Title']]['file_path']}” i „{json_given['file_path']}”.")
                    pass
                else:
                    print(f"Dwie różne produkcje o tej samej nazwie: „{production['Title']}” "
                        f"w plikach „{production_dict[production['Title']]['file_path']}” i „{json_given['file_path']}”.")
                    return False
            else:
                production_dict[production['Title']] = {"prod": production, "file_path": json_given['file_path'], "children": []}
                if production['TitleGeneric']:
                    parents_set.add(production['TitleGeneric'])
                else:
                    root_generics.append(production['Title'])

    # generowanie listy braków
    for g in parents_set:
        if g not in production_dict:
            root_missing.append(g)

    # uzupełnianie powiązań
    for p, v in production_dict.items():
        if v["prod"]["TitleGeneric"] in root_missing:
            v["parent"] = 'missing'
        elif v["prod"]["Title"] in root_generics:
            v["parent"] = 'root'
        else:
            v["parent"] = v["prod"]["TitleGeneric"]
            production_dict[v["parent"]]["children"].append(v["prod"]["Title"])
            # print(f'### {v["file_path"]}')
            hierarchy_res, blockades = check_hierarchy(production_dict[v["parent"]]["prod"], v["prod"])
            # v["blockades"] = blockades
            if not production_dict[v["parent"]].get("blockades"):
                production_dict[v["parent"]]["blockades"] = []
            production_dict[v["parent"]]["blockades"].extend(blockades)
            if hierarchy_res != 'OK':
                v["hierarchy_mismatch"] = hierarchy_res


    return production_dict, root_generics, root_missing