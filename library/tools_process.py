from copy import deepcopy
import datetime
from typing import Union, List, Tuple

import re

import json

import os

import ctypes

from library.tools import find_reference_leaves, ls_to_world, breadcrumb_pointer, find_node_layer_name, \
    nodes_list_from_tree, find_reference_leaves_single_graph, node_description, eval_expression_po_rozmowie_z_Wojtkiem, \
    world_copy, destinations_change_to_nodes
from library.tools_visualisation import draw_graph, GraphVisualizer, draw_narration_line


def get_op_source_paths_list(ls: list, variant: List[Tuple], path_single: str, path_multiple: str) -> List[List[dict]]:
    """
    Converts instruction parameters to the list of paths to source nodes needed to make operation in the world.
    :param ls: the graph in which the initial name or id is searched
    :param variant: the matched pairs of nodes from LS and world.
    :param path_single: instruction parameters NODE-REF type
    :param path_multiple: instruction parameters NODE-MULTIREF type
    :return: list of paths to leaf nodes from the world (paths from world location to the world leaf)
    """
    if not path_single and not path_multiple:
        print(f'Brakuje wskazania węzła źródłowego potrzebnego do wykonania operacji.')
        return []

    nodes = find_reference_leaves(ls, variant, path_single or path_multiple)

    if not nodes:
        if "/" not in (path_single or path_multiple):
            print(f'Nie znaleziono węzła: {path_single or path_multiple} potrzebnego do wykonania operacji.')
        return []
    elif len(nodes) > 1 and path_single:
        print(f'Niejednoznaczne wskazanie węzła {path_single} potrzebnego do wykonania operacji.')
        return []

    return nodes


def get_op_target_node(ls: list, variant: List[Tuple], to: str) -> (dict, str):
    """
    Converts instruction parameter to the set of values needed to make operation in the world.
    :param ls: left side of the production (context of target reference)
    :param variant: the matched pairs of nodes from LS and world
    :param to: instruction parameters ARRAY-REF type
    :return: node from the world hashed out as target node and his layer type
    """
    if to:
        to_split = to.split('/')
        if len(to_split) != 2 or to_split[-1] not in ['Locations', 'Characters', 'Items', 'Narration']:
            print(f'Błąd składni wskazania miejsca docelowego w operacji.')
            return {}, ''
        target_array = to_split[-1]
        ls_target_node_paths = breadcrumb_pointer(ls, name_or_id=to_split[0])

        if not ls_target_node_paths or len(ls_target_node_paths) > 1:
            print(f'Błąd wskazania miejsca docelowego w operacji.')
            return {}, ''
    else:
        print(f'Brakuje wskazania miejsca docelowego w operacji.')
        return {}, ''

    w_target_node = ls_to_world(ls_target_node_paths[0][-1], variant)

    return w_target_node, target_array


def add_node(node_to_add: dict, target_node: dict, target_layer: str) -> List[int]:
    """
    Adds the given node to the target layer of the target node.
    :param node_to_add: given node to add
    :param target_node: node to places the node_to_add into the children list
    :param target_layer: name of the specific children layer of the target_node
    :return: list of added nodes. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    if not node_to_add:
        print(f'Brakuje wskazania węzła źródłowego potrzebnego do wykonania operacji.')
        return []
    if not target_node:
        print(f'Brakuje wskazania miejsca docelowego potrzebnego do wykonania operacji.')
        return []
    if not target_layer or target_layer not in ['Locations', 'Characters', 'Items', 'Narration']:
        print(f'Brakuje (lub błąd składni) wskazania warstwy docelowej w operacji.')
        return []

    # dodajemy węzeł docelowy
    if target_layer not in target_node:
        target_node[target_layer] = []
    target_node[target_layer].append(node_to_add)
    modified_nodes_ids.append(id(node_to_add))

    return modified_nodes_ids


def remove_node(node_to_remove: dict, parent_node: dict = None, world: Union[list, dict] = None) -> List[int]:
    """
    Removes the given node from the list of children of parent node (parent in the world).
    :param node_to_remove: given node to remove
    :param parent_node: the parent node of the removed one, if not given the world argument is used to calculate
    :param world: graph from which the node is removed. used to calculate the parent node, if not given directly
    :return: id of the parent of deleted node
    """
    if not node_to_remove:
        print(f'Brakuje wskazania węzła źródłowego potrzebnego do wykonania operacji.')
        return []
    if not parent_node and not world:
        print(f'Nie można wykonać operacji bez podania rodzica węzła źródłowego lub świata, w którym poszukamy rodzica.')
        return []

    # usuwamy węzeł źródłowy
    if not parent_node:
        parent_path = breadcrumb_pointer(world, pointer=node_to_remove)
        if parent_path and len(parent_path) and len(parent_path[0]) > 1:
            parent_node = parent_path[0][-2]
        else:
            print(f'Błąd operacji, bo nie da się znaleźć rodzica węzła {node_to_remove.get("Name")}. '
                  f'Przypuszczalnie usiłujemy przenieść lub usunąć lokację, co jest zabronione.')
            return []
    source_layer = find_node_layer_name(parent_node, node_to_remove)
    try:
        parent_node[source_layer].remove(node_to_remove)
    except:
        print(f'Błąd operacji, bo nie da się usunąć węzła {node_to_remove.get("Name")} ze świata.')
        return []

    return [id(parent_node)]


def operation_move(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    """
    Moves nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right from the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []

    to = instruction.get('To')
    path_single = instruction.get('Node')
    path_multiple = instruction.get('Nodes')
    limit = instruction.get('Limit')

    # wyciągamy ścieżki od wszystkich liści (ścieżki od lokacji do liścia, zawierają one multireferencję)
    nodes_paths = get_op_source_paths_list(ls, variant, path_single, path_multiple)

    target_node, target_layer = get_op_target_node(ls, variant, to)
    if not target_node:
        print(f'Błąd operacji move, bo nie da się znaleźć węzła docelowego {to}. ')
        return modified_nodes_ids

    limit = min(len(nodes_paths), limit or len(nodes_paths))

    # operacja move dla każdego ze znalezionych węzłów źródłowych
    for path in nodes_paths[0:limit]:

        # ustalamy węzeł do usunięcia
        node_to_move = path[-1]
        # ustalamy rodzica
        if len(path) > 1:
            parent_node = path[-2]  # korzystam ze znalezionego wcześniej rodzica
        else:
            print(f'Błąd operacji move, bo nie da się znaleźć rodzica węzła {node_to_move.get("Name")}. '
                  f'Przypuszczalnie usiłujemy przenieść lokację, co jest zabronione.')
            continue

        if remove_node(node_to_move, parent_node):
            modified_nodes_ids.extend(add_node(node_to_move, target_node, target_layer))
        else:
            continue

    return modified_nodes_ids


def operation_copy(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    """
    Copies nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    if instruction: # wartości węzłów zdefiniowane w treści instrukcji
        to = instruction.get('To')
        path_single = instruction.get('Node')
        path_multiple = instruction.get('Nodes')
        limit = instruction.get('Limit')

        # wyciągamy ścieżki od wszystkich liścia. (ścieżki od lokacji do liścia, zawierają one multireferencję)
        nodes_paths = get_op_source_paths_list(ls, variant, path_single, path_multiple)

        target_node, target_layer = get_op_target_node(ls, variant, to)
        limit = min(len(nodes_paths), limit or len(nodes_paths))

        # dodawanie do pozycji docelowej
        for path in nodes_paths[0:limit]:
            node_to_copy = path[-1]
            modified_nodes_ids.extend(add_node(deepcopy(node_to_copy), target_node, target_layer))

    return modified_nodes_ids


def operation_create(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    """
    Creates nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    to = instruction.get('In')
    node_to_create = instruction.get('Sheaf')
    limit = instruction.get('Limit') or 1

    target_node, target_layer = get_op_target_node(ls, variant, to)

    for nr in range(limit):
        new_node = deepcopy(node_to_create)
        modified_nodes_ids.extend(add_node(new_node, target_node, target_layer))

    return modified_nodes_ids


def operation_winning(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    character = ls_to_world(ls[0]["Characters"][0], variant)
    if not character.get("Attributes"):
        character['Attributes'] = {}
    if not character['Attributes'].get("IsWinner"):  # TODO działa tylko dla pojedynczej misji, trzeba poprawić
        print("""
                                   (
        *                           )   *
                      )     *      (
            )        (                   (
           (          )     (             )
            )    *           )        )  (
           (                (        (      *
            )          H     )        )
                      [ ]            (
               (  *   |-|       *     )    (
         *      )     |_|        .          )
               (      | |    .  
         )           /   \     .    ' .        *
        (           |_____|  '  .    .  
         )          | ___ |  \~~~/  ' .   (
                *   | \ / |   \_/  \~~~/   )
                    | _Y_ |    |    \_/   (
        *           |-----|  __|__   |      *
                    `-----`        __|__
        
        """)

    character['Attributes']["IsWinner"] = True

    return []


def operation_delete(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    """
    Deletes nodes from the world (from its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of parents of deleted nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    path_single = instruction.get('Node')
    path_multiple = instruction.get('Nodes')
    limit = instruction.get('Limit')
    constr_children = instruction.get('Children')
    # Zakładam, że „bliższa koszula ciału”, tzn. wystąpienie szczegółowego parametru zastępuje ogólniejszy
    constr_characters = instruction.get('Characters') or constr_children
    constr_items = instruction.get('Items') or constr_children
    constr_narration = instruction.get('Narration') or constr_children

    # wyciągamy ścieżki od wszystkich liścia. (ścieżki od lokacji do liścia, zawierają one multireferencję)
    nodes_paths = get_op_source_paths_list(ls, variant, path_single, path_multiple)

    limit = min(len(nodes_paths), limit or len(nodes_paths))

    for path in nodes_paths: # nie mogę tu ograniczać do limitu, bo któryś węzeł może być prohibited
        if limit:
            node_to_delete = path[-1]
            # ustalam rodzica
            if len(path) > 1:
                parent_node = path[-2]  # korzystam ze znalezionego wcześniej rodzica
            else:
                print(f'Błąd operacji move, bo nie da się znaleźć rodzica węzła {node_to_delete.get("Name")}. '
                      f'Przypuszczalnie usiłujemy usunąć lokację, co jest zabronione.')
                return []

            # obsługa parametrów: children, character, items, narration
            # TODO Kompletnie nieprzetestowane
            if constr_characters == 'move':
                if node_to_delete.get('Characters'):
                    for ch in node_to_delete['Characters']:
                        if remove_node(ch, node_to_delete, parent_node):
                            modified_nodes_ids.extend(add_node(ch, node_to_delete, 'Characters'))
            elif constr_characters == 'prohibit':
                    if node_to_delete.get('Characters') and len(node_to_delete['Characters']) > 0:
                        continue
            if constr_items == 'move':
                if node_to_delete.get('Items'):
                    for ch in node_to_delete['Items']:
                        if remove_node(ch, node_to_delete, parent_node):
                            modified_nodes_ids.extend(add_node(ch, node_to_delete, 'Items'))
            elif constr_items == 'prohibit':
                    if node_to_delete.get('Items') and len(node_to_delete['Items']) > 0:
                        continue
            if constr_narration == 'move':
                if node_to_delete.get('Narration'):
                    for ch in node_to_delete['Narration']:
                        if remove_node(ch, node_to_delete, parent_node):
                            modified_nodes_ids.extend(add_node(ch, node_to_delete, 'Narration'))
            elif constr_narration == 'prohibit':
                    if node_to_delete.get('Narration') and len(node_to_delete['Narration']) > 0:
                        continue

            # usuwamy węzeł źródłowy
            try:
                modified_nodes_ids.extend(remove_node(node_to_delete, parent_node))
            except:
                print(f'Błąd operacji delete, bo nie da się usunąć węzła {node_to_delete.get("Name")} ze świata.')
                continue
            limit -= 1

        else:
            break

    return modified_nodes_ids


def operation_set(ls: list, variant: List[tuple], instruction: dict, prod_vis_mode = False) -> List[int]:
    """
    Sets the attributes of the nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    attribute = instruction.get('Attribute')
    if instruction.get('Value') is not None:
        value = instruction.get('Value')
    elif instruction.get('Expr') is not None:
        if prod_vis_mode:
            value = instruction.get('Expr')
        else:
            value = eval_expression_po_rozmowie_z_Wojtkiem(instruction.get('Expr'), variant)
    else:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    node_paths = find_reference_leaves(ls, variant, attribute.split(".")[0])
    if not node_paths or len(node_paths) > 1:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []
    node_to_change = node_paths[0][-1]

    attribute_name = attribute.split(".")[1]
    if not attribute_name:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    if 'Attributes' not in node_to_change:
        node_to_change['Attributes'] = {}

    node_to_change['Attributes'][attribute_name] = value
    modified_nodes_ids.append(id(node_to_change))

    return modified_nodes_ids

def operation_add(ls: list, variant: List[tuple], instruction: dict, prod_vis_mode = False) -> List[int]:
    """
    Sets the attributes of the nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    attribute = instruction.get('Attribute')
    if instruction.get('Value') is not None:
        value = instruction.get('Value')
    elif instruction.get('Expr') is not None:
        if prod_vis_mode:
            value = instruction.get('Expr')
        else:
            value = eval_expression_po_rozmowie_z_Wojtkiem(instruction.get('Expr'), variant)
    else:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    node_paths = find_reference_leaves(ls, variant, attribute.split(".")[0])
    if not node_paths or len(node_paths) > 1:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []
    node_to_change = node_paths[0][-1]

    attribute_name = attribute.split(".")[1]
    if not attribute_name:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    if 'Attributes' not in node_to_change:
        if prod_vis_mode:
            node_to_change['Attributes'] = {attribute_name: ''}
        else:
            node_to_change['Attributes'] = {attribute_name: 0}

    if attribute_name not in node_to_change['Attributes']:
        if prod_vis_mode:
            node_to_change['Attributes'][attribute_name] = ''
        else:
            node_to_change['Attributes'][attribute_name] = 0

    if prod_vis_mode:
        if node_to_change['Attributes'][attribute_name]:
            node_to_change['Attributes'][attribute_name] = f"{node_to_change['Attributes'][attribute_name]} + {value}"
        else:
            node_to_change['Attributes'][attribute_name] = f"{attribute_name} + {value}"
    else:
        try:
            node_to_change['Attributes'][attribute_name] += value
        except:
            print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')

    modified_nodes_ids.append(id(node_to_change))

    return modified_nodes_ids

def operation_mul(ls: list, variant: List[tuple], instruction: dict, prod_vis_mode = False) -> List[int]:
    """
    Sets the attributes of the nodes in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    attribute = instruction.get('Attribute')
    if instruction.get('Value') is not None:
        value = instruction.get('Value')
    elif instruction.get('Expr') is not None:
        if prod_vis_mode:
            value = instruction.get('Expr')
        else:
            value = eval_expression_po_rozmowie_z_Wojtkiem(instruction.get('Expr'), variant)
    else:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    node_paths = find_reference_leaves(ls, variant, attribute.split(".")[0])
    if not node_paths or len(node_paths) > 1:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []
    node_to_change = node_paths[0][-1]

    attribute_name = attribute.split(".")[1]
    if not attribute_name:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    if 'Attributes' not in node_to_change:
        if prod_vis_mode:
            node_to_change['Attributes'] = {attribute_name: ''}
        else:
            node_to_change['Attributes'] = {attribute_name: 1}

    if attribute_name not in node_to_change['Attributes']:
        if prod_vis_mode:
            node_to_change['Attributes'][attribute_name] = ''
        else:
            node_to_change['Attributes'][attribute_name] = 1

    if prod_vis_mode:
        if node_to_change['Attributes'][attribute_name]:
            node_to_change['Attributes'][attribute_name] = f"{node_to_change['Attributes'][attribute_name]} * {value}"
        else:
            node_to_change['Attributes'][attribute_name] = f"{attribute_name} * {value}"
    else:
        try:
            node_to_change['Attributes'][attribute_name] *= value
        except:
            print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')

    modified_nodes_ids.append(id(node_to_change))

    return modified_nodes_ids


def operation_unset(ls: list, variant: List[tuple], instruction: dict) -> List[int]:
    """
    Unets the given attribute of the node in the world (in its part represented by the variant tuples right sides).
    :param ls: left side of the production
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param instruction: dict of the parameters taken from the operation “Instructions” list
    :return: list of modified nodes ids. If empty, it means the instruction application has failed
    """
    modified_nodes_ids = []
    attribute = instruction.get('Attribute')

    node_paths = find_reference_leaves(ls, variant, attribute.split(".")[0])
    if not node_paths or len(node_paths) > 1:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []
    node_to_change = node_paths[0][-1]

    attribute_name = attribute.split(".")[1]
    if not attribute_name:
        print(f'Błąd operacji {instruction["Op"]} dla atrybutu: {attribute}.')
        return []

    if 'Attributes' not in node_to_change or attribute_name not in node_to_change['Attributes']:
        print(f'Nie da się usunąć nieistniejącego atrybutu węzła {node_to_change.get("Name","")}')
        return []
    try:
        del(node_to_change['Attributes'][attribute_name])
    except:
        print(f'Nie udało się usunąć  atrybutu {attribute_name} węzła {node_to_change.get("Name", "")}')
        return []
    modified_nodes_ids.append(id(node_to_change))

    return modified_nodes_ids


def apply_instructions_to_world(production: dict, variant: list, world: Union[list, dict], prod_vis_mode = False):
    """
    Applies instructions given in the production to the world (currently to its part represented by the variant tuples right sides).
    :param production: production chosen to apply
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :param world: Currently not used, prepared for the instructions using nodes from beyond the variant list
    :return: nothing
    """
    instructions = production['Instructions']
    ls = production['LSide']['Locations']
    modified_nodes = []

    for instruction_number, instruction in enumerate(instructions):

        if instruction['Op'] == 'move':
            modified_nodes.extend(operation_move(ls, variant, instruction))

        elif instruction['Op'] == 'delete':
            modified_nodes.extend(operation_delete(ls, variant, instruction))

        elif instruction['Op'] == 'create':
            modified_nodes.extend(operation_create(ls, variant, instruction))

        elif instruction['Op'] == 'copy':
            modified_nodes.extend(operation_copy(ls, variant, instruction))

        elif instruction['Op'] == 'set':
            modified_nodes.extend(operation_set(ls, variant, instruction, prod_vis_mode))

        elif instruction['Op'] == 'add':
            modified_nodes.extend(operation_add(ls, variant, instruction, prod_vis_mode))

        elif instruction['Op'] == 'mul':
            modified_nodes.extend(operation_mul(ls, variant, instruction, prod_vis_mode))

        elif instruction['Op'] == 'unset':
            modified_nodes.extend(operation_unset(ls, variant, instruction))

        # operacje testowe
        elif instruction['Op'] == 'winning':
            modified_nodes.extend(operation_winning(ls, variant, instruction))


        # instrukcje modyfikujące cały świat
        else:
            print(f"Nierozpoznana instrukcja {instruction['Op']}.")




    return modified_nodes


def cut_unnecessary_world_elements(world: list):
    world_nodes_list = nodes_list_from_tree(world, "Locations")
    modified_nodes_ids = []
    removed_children = 0
    removed_parents = 0
    print('Usuwanie obiektów znajdujących się bezpośrednio w lokacjach. Komenda „end” przerywa.')
    print('Możesz usunąć: 1) węzeł z dziećmi; 2) węzeł, dzieci do lokacji; 3) same dzieci; 4) nic.')
    for location in world:

        for layer in ["Characters", "Items", "Narration"]:
            nodes_to_remove_ids = []
            if location.get(layer):
                characters_list = location.get(layer)
                for index, node in enumerate(characters_list):
                    node_children = nodes_list_from_tree(node, layer)[1:]
                    print(f"W lokacji {location.get('Name')} jest {node.get('Name')}, który/a ma: {[x['node'].get('Name') for x in node_children]}")
                    while True:
                        decision = input("Wybierz (1–4, „end”): ")
                        if decision.lower() in ["1", "2", "3", "4", "end"]:
                            break
                    if decision == "1":
                        nodes_to_remove_ids.append(index)
                        removed_children += len(node_children)
                        removed_parents += 1
                    elif decision == "2":
                        check = True
                        if len(node_children):
                            for child in node_children:
                                if remove_node(child["node"], node):
                                    modified_nodes_ids.extend(add_node(child["node"], location, child["layer"]))
                                else:
                                    check = False
                        if not check:
                            print("Nie udało się przenieść wszystkich dzieci, ale i tak usuwam węzeł.")
                        nodes_to_remove_ids.append(index)
                        removed_parents += 1
                    elif decision == "3":
                        if len(node_children):
                            for child in node_children:
                                remove_node(child["node"], node)
                                removed_children += 1
                    # elif decision == "4":
                    #     break
                    elif decision == "end":
                        break

                nodes_to_remove_ids.sort(reverse=True)
                for index in nodes_to_remove_ids:
                    characters_list.pop(index)
                if decision == "end":
                    break
        if decision == "end":
            break
    print(f'Usunięto {removed_parents + removed_children} węzłów, w tym {removed_children} dzieci. '
          f'Przeniesiono {len(modified_nodes_ids)} dzieci.')
    return modified_nodes_ids


def save_stats(world_structure: dict, world: list, folder:str, file_name: str = None, moves: list = None):
    # world_target = deepcopy(world_structure)
    # if not file_name:
    #     file_name = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) + '_' + world_target['file_path'].split('/')[-1]
    #
    # folder_path = folder.rstrip('/') + '/' + file_name.split('.')[0] + '_stats/'
    # os.makedirs(os.path.dirname(folder_path), exist_ok=True)
    #
    # for location in world:
    #
    #
    #
    #
    # with open(file_path, 'w', encoding="utf8") as outfile:
    #     # json.dump(json_string, outfile)
    #     json.dump(world_target['json'], outfile, indent=4, ensure_ascii=False)

    return


def save_world(world_structure: dict, folder:str = None, file_name: str = None):
    world_target = deepcopy(world_structure)
    if folder:
        if not file_name:
            file_name = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) + '_' + world_target['file_path'].split('/')[-1]
    for location in world_target['json'][0]["LSide"]["Locations"]:
        if 'Connections' in location:
            for dest in location['Connections']:
                dest['Destination']['Id'] = str(id(dest['Destination']))
                dest['Destination'] = str(id(dest['Destination']))

    for location in world_target['json'][0]["LSide"]["Locations"]:
        if 'Attributes' in location:
            temp_attributes = location['Attributes']
            del(location['Attributes'])
        else:
            temp_attributes = None
        if 'Characters' in location:
            temp_characters = location['Characters']
            del(location['Characters'])
        else:
            temp_characters = None
        if 'Items' in location:
            temp_items = location['Items']
            del (location['Items'])
        else:
            temp_items = None
        if 'Narration' in location:
            temp_narration = location['Narration']
            del (location['Narration'])
        else:
            temp_narration = None
        if 'Connections' in location:
            temp_connections = location['Connections']
            del (location['Connections'])
        else:
            temp_connections = None
        if 'Name' in location:
            temp_name = location['Name']
            del (location['Name'])
        else:
            temp_name = None
        if 'Id' in location:
            temp_id = location['Id']
            del (location['Id'])
        else:
            temp_id = None

        if temp_id:
            location['Id'] = temp_id
        if temp_name:
            location['Name'] = temp_name
        if temp_attributes:
            location['Attributes'] = temp_attributes
        if temp_characters:
            location['Characters'] = temp_characters
        if temp_items:
            location['Items'] = temp_items
        if temp_narration:
            location['Narration'] = temp_narration
        if temp_connections:
            location['Connections'] = temp_connections


    if folder:
        file_path = folder.rstrip(os.sep) + os.sep + file_name
        # Directly from dictionary
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding="utf8") as outfile:
            # json.dump(json_string, outfile)
            json.dump(world_target['json'], outfile, indent=4, ensure_ascii=False)

    return world_target['json']


def save_world_game(world_structure: dict, folder:str = None, file_name: str = None):
    world_target = deepcopy(world_structure)
    world_copy(world_structure['json'][0]["LSide"]["Locations"], world_target['json'][0]["LSide"]["Locations"], False)
    if folder:
        if not file_name:
            file_name = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S")) + '_' + world_target['file_path'].split('/')[-1]
    # for location in world_target['json'][0]["LSide"]["Locations"]:
    #     if 'Connections' in location:
    #         for dest in location['Connections']:
    #             dest['Destination'] = str(dest['Destination']['Id'])
    #             # dest['Destination'] = str(id(dest['Destination']))

    # for location in world_target['json'][0]["LSide"]["Locations"]:
    #     if 'Attributes' in location:
    #         temp_attributes = location['Attributes']
    #         del(location['Attributes'])
    #     else:
    #         temp_attributes = None
    #     if 'Characters' in location:
    #         temp_characters = location['Characters']
    #         del(location['Characters'])
    #     else:
    #         temp_characters = None
    #     if 'Items' in location:
    #         temp_items = location['Items']
    #         del (location['Items'])
    #     else:
    #         temp_items = None
    #     if 'Narration' in location:
    #         temp_narration = location['Narration']
    #         del (location['Narration'])
    #     else:
    #         temp_narration = None
    #     if 'Connections' in location:
    #         temp_connections = location['Connections']
    #         del (location['Connections'])
    #     else:
    #         temp_connections = None
    #     if 'Name' in location:
    #         temp_name = location['Name']
    #         del (location['Name'])
    #     else:
    #         temp_name = None
    #     if 'Id' in location:
    #         temp_id = location['Id']
    #         del (location['Id'])
    #     else:
    #         temp_id = None
    #
    #     if temp_id:
    #         location['Id'] = temp_id
    #     if temp_name:
    #         location['Name'] = temp_name
    #     if temp_attributes:
    #         location['Attributes'] = temp_attributes
    #     if temp_characters:
    #         location['Characters'] = temp_characters
    #     if temp_items:
    #         location['Items'] = temp_items
    #     if temp_narration:
    #         location['Narration'] = temp_narration
    #     if temp_connections:
    #         location['Connections'] = temp_connections


    if folder:
        file_path = folder.rstrip('/') + '/' + file_name
        # Directly from dictionary
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding="utf8") as outfile:
            # json.dump(json_string, outfile)
            json.dump(world_target['json'], outfile, indent=4, ensure_ascii=False)

    return world_target['json']


def find_node_from_input(graph, prompt, only_one: bool = False, choose_one: bool = False, d = None, f = None) -> list:
    gv = GraphVisualizer()
    target_node_paths = find_reference_leaves_single_graph(graph, input(prompt))
    if not target_node_paths:
        print("Nie znaleziono takiego węzła.")
        return
    elif choose_one and len(target_node_paths) > 1:
        print(f'Węzeł {target_node_paths[0][-1].get("Name")} jest wskazany niejednoznaczne.')
        print(f"Rysunek z ponumerowanymi węzłami jest w katalogu: ../{d}.")

        # if only_one:
        #     prompt_all = ''
        # else:
        #     prompt_all = ' („all” aby wybrać wszystkie)'
        comments = {'color': 'red'}
        for nr, path in enumerate(target_node_paths):
            print(f'    {nr:03d}. {node_description(graph, path)}')
            comments[id(path[-1])] = nr

        d_title = "Stan świata pomocniczy"
        d_desc  = f'Stan świata w dniu {datetime.datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ze wskazaniem niejednoznacznego wyboru.'
        d_file  = f'{f}{target_node_paths[0][-1].get("Name")}_nodes_to_choose'
        d_dir   = f'{d}'
        draw_graph(graph, d_title, d_desc, d_file, d_dir, c = comments)
        # gv.visualise({'Locations': graph}, title="Stan świata pomocniczy",
        #     description=f'Stan świata w dniu {datetime.datetime.now().strftime("%d.%m.%Y godz. %H:%M:%S")} ze wskazaniem niejednoznacznego wyboru.',
        #     world=True, comments=comments).render(format='png',
        #     filename=f'{f}{target_node_paths[0][-1].get("Name")}_nodes_to_choose',
        #     directory=f'{d}',
        #     cleanup=True)


        while True:
            decision = input(f"Wybierz węzeł: ")  # {prompt_all}
            # if not only_one and decision == 'all':
            #     return target_node_paths
            if decision.lower() == 'end':
                return None
            try:
                chosen_nr = int(decision)
            except:
                continue
            if chosen_nr in range(len(target_node_paths)):
                break
        return [target_node_paths[chosen_nr]]
    elif only_one and len(target_node_paths) > 1:
        print("Niejednoznaczne wskazanie węzła.")
        return
    return target_node_paths


def find_layer_from_input(prompt) -> str:
    target_layer = input(prompt)
    if target_layer not in ['Locations', 'Characters', 'Items', 'Narration']:
        print("Błędnie podana warstwa docelowa.")
        return
    return target_layer


def add_attributes_from_input():
    attributes = {}
    stop_flag = False
    print("Podaj atrybuty w formacie: Nazwa=wartość. Wpisz enter by przejść dalej, „end” by zakończyć.")
    while True:  # pozyskujemy od użytkownika informację o wyborze działania
        # attr = (input(f'Podaj atrybut i wartość: ')).split("=", 1)
        attr = re.split(r"\s*=\s*", input(f'Podaj atrybut i wartość: '), 1)
        if attr[0].lower() == 'end':
            stop_flag = True
            break
        if attr[0].lower() == '':
            break
        if len(attr) != 2:
            continue
        if True:  # trzeba będzie sprawdzać czy pascal case
            attr_key = attr[0]
        else:
            continue

        attr_value = None
        if attr[1].lower() == 'true':
            attr_value = True
        elif attr[1].lower() == 'false':
            attr_value = False
        else:
            try:
                attr_value = int(attr[1])
            except:
                try:
                    attr_value = float(attr[1])
                except:
                    pass
            if attr_value is None:
                attr_value = attr[1]
        attributes[attr_key] = attr_value

    return attributes, stop_flag


def draw_variants_graphs (matches_lists, world, d_title, d_dir):
    for match_list, nr2 in zip(matches_lists, range(len(matches_lists))):
        red_nodes = []
        red_edges = []
        comments = {'color': 'red'}
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

        d_desc = f"Dopasowanie produkcji w świecie, wariant {nr2:03d}"
        d_file = f'match_{nr2:03d}'

        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments)


def game_init(gp):
    player_to_filename = re.sub(r'[^\w\d-]+', '', gp["Player"])
    file_path = f'{gp["FilePath"]}/gameplay_{gp["QuestName"]}_{gp["WorldName"]}_{gp["DateTimeStart"]}_{player_to_filename}.json'
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding="utf8") as outfile:
        json.dump(gp, outfile, indent=4, ensure_ascii=False)


def game_over(gp, reason = None):
    print(
        f"""
       ________                                                  
      /  _____/_____    _____   ____     _______  __ ___________ 
     /   \  ___\__  \  /     \_/ __ \   / __ \  \/ // __ \_  __ \\
     \    \_\  \/ __ \|  Y Y  \  ___/  | (__) |   /\  ___/|  | \/
      \______  (____  /__|_|  /\____>   \____/ \_/  \____>|__|   
     """)

    gp["DateTimeEnd"] = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    gp["EndReason"] = reason or ''
    if reason == "Decyzja użytkownika":
        print('Podaj powód zakończenia:')
        print('A – udało mi się wypełnić misję')
        print('B – nie mam pomysłu, co dalej')
        print('C – znudziło mi się')
        explanation = input('lub inny, jaki? ')
        if explanation.lower() == 'a':
            gp["EndDecisionExplanation"] = 'Udało mi się wypełnić misję.'
        elif explanation.lower() == 'b':
            gp["EndDecisionExplanation"] = 'Nie mam pomysłu, co dalej.'
        elif explanation.lower() == 'c':
            gp["EndDecisionExplanation"] = 'Znudziło mi się.'
        else:
            gp["EndDecisionExplanation"] = explanation

    gp["PlayerComment"] = input("Wpisz uwagi, jakie ci się nasuwały podczas procesu decyzyjnego (wulgaryzmy nie będą cenzurowane ;--):\n")
    player_to_filename = re.sub(r'[^\w\d-]+', '', gp["Player"])
    file_path = f'{gp["FilePath"]}{os.sep}gameplay_{gp["QuestName"]}_{gp["WorldName"]}_{gp["DateTimeStart"]}_{player_to_filename}.json'

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    draw_narration_line(gp["Moves"], f'gameplay_{gp["QuestName"]}_{gp["WorldName"]}_{gp["DateTimeStart"]}_{player_to_filename}', f'{gp["FilePath"]}')
    del (gp["FilePath"])

    with open(file_path, 'w', encoding="utf8") as outfile:
        json.dump(gp, outfile, indent=4, ensure_ascii=False)


    exit(0)


def dict_from_variant(variant):
    variant_dicts = []
    for ls_node, w_node in variant:
        # ls_node = ctypes.cast(ls_node_id, ctypes.py_object).value
        # w_node = ctypes.cast(w_node_id, ctypes.py_object).value
        variant_dicts.append({
            "LSNodeRef": ls_node.get('Id',ls_node.get('Name')),
            "WorldNodeId": id(w_node),
            "WorldNodeName": w_node.get('Name'),
            "WorldNodeAttr": w_node.get('Attributes')
        })
    return variant_dicts


def looking_for_main_character(gameplay, world, name=None, pointer=None, failure_text = '', zero_text = '', multi_text = ''):
    if name:
        character_paths = breadcrumb_pointer(world, name_or_id=name, layer="Characters")
    elif pointer:
        character_paths = breadcrumb_pointer(world, pointer=pointer)
        name = pointer.get("Name")
    if not character_paths:
        reason = f"Nie ma postaci {name} w świecie. {failure_text + zero_text}"
        print(reason)
        game_over(gameplay, reason)
    if len(character_paths) > 1:
        reason = f"Niejednoznaczne wskazanie postaci {name} w świecie. {failure_text + multi_text}"
        game_over(gameplay, reason)

    return character_paths


def retrace_gameplay(gameplay_dir, gameplay_filename):

    gp = json.load(open(f'{gameplay_dir}/{gameplay_filename}', encoding="utf8"))

    productions_chars_turn_to_match = []
    productions_world_turn_to_match = []
    for prod_list in gp["QuestSource"]:
        for quest_name, prods in prod_list.items():
            for prod in prods:
                productions_chars_turn_to_match.append(prod)
                if not destinations_change_to_nodes(prod['LSide']['Locations']):
                    print("Problem wczytywania produkcji.")
                    return False
    for prod_list in gp["WorldResponseSource"]:
        for quest_name, prods in prod_list.items():
            for prod in prods:
                productions_world_turn_to_match.append(prod)
                if not destinations_change_to_nodes(prod['LSide']['Locations']):
                    print("Problem wczytywania produkcji.")
                    return False
    prod_dict = {}
    for prod in productions_world_turn_to_match + productions_chars_turn_to_match:
        prod_dict[prod["Title"]] = prod


    world = gp['WorldSource'][0]['LSide']['Locations']

    # world_before = gp['Moves'][0]['WorldBefore']
    # print(f'Świat początkowy i świat pierwszego ruchu { "są identyczne." if world == world_before else "są różne."}')
    destinations_change_to_nodes(world, world=True, remove_ids=False)

    print(f'Wykonano {len(gp["Moves"])} ruchów.')


    for nr, move in enumerate(gp['Moves']):
        who = 'Automatycznie wykonała się produkcja' if move["Object"] == "Action automatically performed" else f'{move["Object"]} wykonał produkcję'
        print(f'{nr:02d}. {who} „{move["ProductionTitle"].split(" / ")[1]}”')
        # if nr < len(gp["Moves"])-1:
        #     if gp['Moves'][nr]["WorldAfter"] == gp['Moves'][nr + 1]["WorldBefore"]:
        #         print(f'    Światy po tej produkcji i przed następną są identyczne.')
        #     else:
        #         print(f'    Światy po tej produkcji i przed następną są różne. UWAGA!')
        # print()

        ################################################################
        current_world_dict = {}
        for node in nodes_list_from_tree(move["WorldAfter"], "Locations"):
            current_world_dict[node['node']['Id']] = node['node']

        production = prod_dict[move["ProductionTitle"]]
        ls = production["LSide"]["Locations"]

        # odtwarzanie wariantu dopasowania
        variant = []
        red_nodes = []
        for pair in move["LSMatching"]:
            ls_node_paths = breadcrumb_pointer(ls, name_or_id=pair['LSNodeRef'])
            w_node_paths = breadcrumb_pointer(world, name_or_id=str(pair['WorldNodeId']))
            if not ls_node_paths or len(ls_node_paths) != 1 or not w_node_paths or len(w_node_paths) != 1:
                print("Error")
            variant.append((ls_node_paths[0][-1], w_node_paths[0][-1]))

        # generowanie stanu świata przed zastosowaniem produkcji.
        red_nodes, red_edges, comments = get_reds(variant)

        d_title = move["ProductionTitle"]
        who = f'automatycznej' if move["Object"] == "Action automatically performed" else f'dla {move["Object"]}'
        d_desc = f'Dopasowanie produkcji {who} w świecie, wariant {move["MatchedVariantIndex"]:03d}'
        d_file = f'{nr:03d}a_world_before_{move["ProductionTitle"].split(" / ")[0].replace("’", "")}'
        d_dir = f'{gameplay_dir}/world_states_retraced/'

        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments, draw_id=False)

        # wykonywanie produkcji
        print('\nDopasowanie lewej strony (wariant):')
        for ls_node, w_node in variant:
            print(f'{ls_node.get("Id",ls_node.get("Name"))} = {w_node.get("Name")}')

        red_nodes_new = apply_instructions_to_world(production, variant, world)
        print('\nWęzły zmienione w produkcji a węzły zapisane jako zmienione:')
        for node1_id, node2_id in zip(move['ModifiedNodes'], red_nodes_new):
            node1 = current_world_dict[str(node1_id)]
            node2 = ctypes.cast(node2_id, ctypes.py_object).value
            if node2.get('Id') and node2.get('Id') != node1.get('Id'):
                print(f'Error! Problem z: {node1.get("Name")}, {node2.get("Name")}')
            if not node2.get('Id'):
                node2['Id'] = node1.get('Id')
            print(f'{node1.get("Name")} = {node2.get("Name")}')

        red_nodes.extend(red_nodes_new)
        d_desc = f'Stan świata po zastosowaniu produkcji w wariancie {move["MatchedVariantIndex"]:03d}'
        d_file = f'{nr:03d}b_world_after_{production["Title"].split(" / ")[0].replace("’", "")}'
        draw_graph(world, d_title, d_desc, d_file, d_dir, red_nodes, red_edges, comments, draw_id=False)

        d_title = f'Świat w oczekiwaniu na ruch gracza'
        d_desc = f'Pomiędzy kolejnymi produkcjami'
        d_file = f'{nr:03d}c_world_between_moves'
        draw_graph(world, d_title, d_desc, d_file, d_dir, draw_id=False)


        for loc1, loc2 in zip(move["WorldAfter"], world):
            similarity = True
            for k1, k2 in zip(loc1, loc2):
                if k1 != 'Connections':
                    if loc1[k1] != loc2[k2]:
                        similarity = False
            print(f'Zastosowanie produkcji {"dało identyczny efekt co WorldAfter!" if similarity else "nie dało rady ;--("}')
        print()




def resume_gameplay(gameplay_dir, gameplay_filename):



    gp = json.load(open(f'{gameplay_dir}/{gameplay_filename}', encoding="utf8"))

    world_name = gp["WorldName"]
    character_name = gp["MainCharacter"]
    if gp.get("Moves"):
        world_source = {'file_path': f'{gameplay_dir}/{gameplay_filename}', 'json': gp["Moves"][-1]["WorldAfter"]}
    elif gp.get("WorldSource"):
        world_source = {'file_path': f'{gameplay_dir}/{gameplay_filename}', 'json': gp["WorldSource"]}
    else:
        print(f"Nie można wczytać świata z pliku {gameplay_dir}/{gameplay_filename}")

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


    # prod_chars_turn_jsons = [deepcopy(x[x.get_keys(0)]) for x in gp["QuestSource"]]
    # prod_world_turn_jsons = [deepcopy(x[x.get_keys(0)]) for x in gp["WorldResponseSource"]]

    productions_chars_turn_to_match = []
    productions_world_turn_to_match = []
    for prod_list in gp["QuestSource"]:
        for quest_name, prods in prod_list.items():
            for prod in prods:
                productions_chars_turn_to_match.append(prod)
                if not destinations_change_to_nodes(prod['LSide']['Locations']):
                    print("Problem wczytywania produkcji.")
                    return False
    for prod_list in gp["WorldResponseSource"]:
        for quest_name, prods in prod_list.items():
            for prod in prods:
                productions_world_turn_to_match.append(prod)
                if not destinations_change_to_nodes(prod['LSide']['Locations']):
                    print("Problem wczytywania produkcji.")
                    return False
    prod_dict = {}
    for prod in productions_world_turn_to_match + productions_chars_turn_to_match:
        prod_dict[prod["Title"]] = prod


    # world = gp['WorldSource'][0]['LSide']['Locations']
    #
    # # world_before = gp['Moves'][0]['WorldBefore']
    # # print(f'Świat początkowy i świat pierwszego ruchu { "są identyczne." if world == world_before else "są różne."}')
    # destinations_change_to_nodes(world, world=True, remove_ids=False)

    if gp.get("Moves"):
        print(f'Wykonano {len(gp["Moves"])} ruchów.')



    return world, productions_chars_turn_to_match, productions_world_turn_to_match


def get_reds(variant, prev_rn = None, prev_re = None, prev_rc = None, c_color = None):
    red_nodes = prev_rn or []
    red_edges = prev_re or []
    comments = prev_rc or {'color': 'red'}
    if c_color:
        comments['color'] =  c_color

    for node in variant:
        red_nodes.append(id(node[1]))
        if 'Connections' in node[0]:
            for dest in node[0]['Connections']:
                for any_node in variant:
                    if any_node[0] is dest['Destination']:  # zm
                        red_edges.append((id(node[1]), id(any_node[1])))
        id_to_comment = node[0].get('Id')
        if id_to_comment:
            comments[id(node[1])] = id_to_comment

    return red_nodes, red_edges, comments

def get_quest_description(quest_name):
    desc = {
        'quest00_Dragon_story':'Jesteś głównym bohaterem gry (Main_hero). Twoim celem w tej misji jest zdobycie smoczego jaja pilnowanego przez groźnego smoka. Smoka możesz zabić w walce (pod warunkiem, że uzyskasz odpowiednio dużo siły), otruć lub wypłoszyć z legowiska. Siłę zwiększamy jedząc obiekty o dużej wartości odżywczej, truciznę dostaniemy od przyjaciół lub pozyskamy z trujących roślin.',
        "quest_DragonStory": 'Jesteś głównym bohaterem gry (Main_hero). Twoim celem w tej misji jest zdobycie smoczego jaja pilnowanego przez groźnego smoka. Smoka możesz zabić w walce (pod warunkiem, że uzyskasz odpowiednio dużo siły), otruć lub wypłoszyć z legowiska. Siłę zwiększamy jedząc obiekty o dużej wartości odżywczej, truciznę dostaniemy od przyjaciół lub pozyskamy z trujących roślin.',
        "quest_RumcajsStory_close": 'Jesteś głównym bohaterem gry (Rumcajs). Możesz zbierać chrust i sprzedać go w Jiczynie, a za uzyskane pieniadze kupić swojej ukochanej żonie piękny naszyjnik.',
        "quest07_Hacking_in_Inn": "Jesteś głównym bohaterem gry (Main_hero). Jeśli znajdziesz przypadkowo zgubiony list miłosny zamężnej kobiety do jej kochanka, to możesz uzyskać pewne – wymierne lub nie – korzyści od którejś z osób zainteresowanych zawartością listu.",
        "quest_17": "Coś",
        "quest2020-13_Help_in_the_field": "Jesteś głównym bohaterem gry (Main_hero). Przeczytaj ogłoszenia na słupie. Może trafi się okazja do zarobku. Pamiętaj, że uczciwość popłaca, ale nieuczciwość czasem też przynosi profity.",
        "quest12_2": "Jesteś głównym bohaterem gry (Main_hero). Przeczytaj ogłoszenie na słupie. Jeśli twój przyjaciel jest razem z Tobą, to sie zmartwi. Szkoda, że twoim przyjacielem nie jest zbójca Ziutek, bo ze swoją bandą stanową siłę. Gdyby tak pomóc jego kamratom wyciągnąć go z więzienia, to oni mogliby odwdzięczyć się tobie. A gdybyś go sam wyciągnął, to nosiliby Cię na rękach.",
        "potyczka_w_tawernie_produkcje": "Po licznych przygodach strudzony bohater trafia do tawerny wraz z eliksirem wzmacniającym i leczniczymi ziołami w swoim ekwipunku (warunek początkowy). Zauważa tam wyraźnie pijanego kupca, który przechwala się swoją siłą przed młodą panną i zapewnia ją, że pokonał by stojącego obok pijanego osiłka. Ku nieszczęściu kupca osiłek słyszy jego deklaracje i wyzywa go na pojedynek,  a w przypływie paniki kupiec prosi bohatera o pomoc w pojedynku. Deklaruje on również, iż szczodrze wynagrodzi naszą pomoc i wspomina on o posiadanej przy sobie sporej sumie pieniędzy i bilecie na statek, które mogłyby posłużyć jako potencjalna nagroda.Po licznych przygodach strudzony bohater trafia do tawerny wraz z eliksirem wzmacniającym i leczniczymi ziołami w swoim ekwipunku (warunek początkowy). Zauważa tam wyraźnie pijanego kupca, który przechwala się swoją siłą przed młodą panną i zapewnia ją, że pokonał by stojącego obok pijanego osiłka. Ku nieszczęściu kupca osiłek słyszy jego deklaracje i wyzywa go na pojedynek,  a w przypływie paniki kupiec prosi bohatera o pomoc w pojedynku. Deklaruje on również, iż szczodrze wynagrodzi naszą pomoc i wspomina on o posiadanej przy sobie sporej sumie pieniędzy i bilecie na statek, które mogłyby posłużyć jako potencjalna nagroda.",
        "przygody w więzieniu": "Jesteś głównym bohaterem gry (Main_hero). Twoim celem w tej misji jest dostanie się na statek, aby zacząć przygodę życia. Poćwicz celność rzucając kamieniami w wilki. Odwiedź Targowisko, a może coś zarobisz, aby przekupić posiadacza hasła na statek.",
        "quest2021-13_Fiddler_story": "Jesteś głównym bohaterem gry (Main_hero). Jeśli dowiesz się o problemach skrzypka, możesz spróbować mu pomóc a byc może pomożecie sobie wzajemnie.",
        "produkcje_szczegolowe_q18": "Jesteś głównym bohaterem. otwórz skrzynię kluczami",
        "5quest2021-05_Prison_break": "Jesteś głównym bohaterem gry (Main_hero). Jesteś w więzieniu. Jeśli zyskałeś sobie przyjaciół to jest szansa, że ktoś cię z więzienia wyciągnie. Liczysz na zaprzyjaźnionego trola, narzeczoną lub skrzypka, ale możesz tylko czekać.",
        "potyczka_w_tawernie_produkcje": "Jesteś głównym bohaterem gry (Main_hero). Idź do tawerny, może zarobisz albo coś zyskasz a na pewno możesz coś zjeść.",
        "misja_10": "Jesteś głównym bohaterem gry (Main_hero). Postaraj się uciec.",
        "q11": "Jesteś głównym bohaterem gry (Main_hero). Chcesz kupić konia. Zorientuj się, kto ma konia i za co chce go sprzedać.",
    }
    return desc.get(quest_name,"Brak opisu")

def ids_list_update(old_list, old_pair_list, new_list):
    for node_id in new_list:
        if node_id not in old_list:
            old_list.append(node_id)
            old_pair_list.append(((node_id), ctypes.cast(node_id, ctypes.py_object).value))