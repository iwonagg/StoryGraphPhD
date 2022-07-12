from datetime import datetime
from pathlib import Path
from typing import List, Union

import graphviz
import re

import os

from config.helpers import qdebug


def get_json_files_paths(path: str, mask: str = '*.json') -> List[Path]:
    """
    Scans path recursively and looks for files with .json extensions.
    :param mask: pattern of file names taken into consideration
    :param path: folder path name
    :return: list of the files in folder according to the pattern
    """
    return [path for path in Path(path).rglob(mask)]


def breadcrumb_pointer(json_dict_or_list: Union[list, dict], path: list = None, parent_key: str = 'root',
                       pointer: dict = None, name_or_id: str = None, attr: dict = None, layer: str = None,
                       remove: bool = False, is_object: bool = False) -> list:
    """
    Find the list of paths from the root to all the leaves of given value (name or attributes or layer)
    :param json_dict_or_list: tree based on JSON
    :param path: path to the parent (for recursion)
    :param parent_key: layer name of the current root. If not applicable, use "root"
    :param pointer: node pointer as a condition of fitting
    :param name_or_id: node name or id as a condition of fitting
    :param attr: node attributes as a condition of fitting
    :param layer: node layer as a condition of fitting
    :param remove: niepotrzebny
    :return: The list of paths, i.e. list of lists of the pointers to the succeeding children from the root to the found fit nodes.
    """
    # https://www.py4u.net/discuss/162893
    # https://stackoverflow.com/questions/69537624/nested-dictionary-path-find-by-value

    if path is None:
        path = []
    if isinstance(json_dict_or_list, dict):
        for k, v in json_dict_or_list.items():
            if k == 'LSide':
                p = breadcrumb_pointer(v, path, "root", pointer, name_or_id, attr, layer, remove, is_object)
                if p:
                    return p
            if k in ("Locations", "Characters", "Items", "Narration", "root"):
                p = breadcrumb_pointer(v, path, k, pointer, name_or_id, attr, layer, remove, is_object)
                if p:
                    return p
            # bardzo brzydkie sprawdzanie, czy korzeń nie jest poszukiwanym wierzchołkiem:
            if not path and (k == 'Name' or k == 'Id'): # to znaczy, że zaczynamy od konkretnego węzła, który może już pasować
                if not parent_key:
                    if layer:
                        raise Exception(f'Próba dopasowania węzła-korzenia do layer jest niemożliwa bez podania warstwy w parametrach wywołania (parent_key).')
                    else:
                        parent_key = 'root'
                return breadcrumb_pointer({parent_key: [json_dict_or_list]}, path, parent_key, pointer, name_or_id, attr, layer, remove, is_object)
            # koniec bardzo brzydkiego sprawdzania, czy korzeń nie jest poszukiwanym wierzchołkiem

    elif isinstance(json_dict_or_list, list):
        current_path = []
        lst = json_dict_or_list
        for i in range(len(lst)):
            if pointer:
                if pointer is lst[i]:
                    current_path.append(path + [lst[i]])
                    return current_path
            else:
                check_name = True
                check_attr = True
                check_layer = True
                check_is_object = True
                # name_or_id =  lst[i]["Name"] if "Name" in lst[i] else lst[i]["Id"] if "Id" in lst[i] else None
                if name_or_id and lst[i].get("Name") != name_or_id and lst[i].get("Id")!= name_or_id:
                    check_name = False
                if layer and parent_key != layer:
                    check_layer = False
                if attr:
                    if "Attributes" not in lst[i]:
                        check_attr = False
                    else:
                        for a, v in attr.items():
                            if a not in lst[i]["Attributes"]:
                                check_attr = False
                            elif (lst[i]["Attributes"][a] != v) and v != None:
                                check_attr = False
                if is_object and not lst[i].get("IsObject"):
                    check_is_object = False
                if check_name and check_attr and check_layer and check_is_object:
                    current_path.append(path + [lst[i]])
            p = breadcrumb_pointer(lst[i], [lst[i]], parent_key, pointer, name_or_id, attr, layer, remove, is_object)
            if p:
                for element in p:
                    current_path.append(path + element)
        return current_path
    return []


def breadcrumb_dict(dictionary: dict, value: str) -> dict:
    for k, v in dictionary.items():
        if k == value:
            return dictionary
        else:
            result = breadcrumb_dict(v, value)
            if result:
                return result


def nodes_list_from_tree(json_dict_or_list: Union[list, dict], parent_key: str = None) -> List[dict]:
    """
    Creates the list of layer-described nodes from the tree.
    :param json_dict_or_list: tree based on JSON
    :param parent_key: layer name of the current root. If not applicable, use "root"
    :return: list of layer-described nodes (dict: "layer", "node")
    """

    if isinstance(json_dict_or_list, dict):
        current_list = []
        if json_dict_or_list.get('Id', json_dict_or_list.get('Name')):
            if not parent_key:
                raise Exception(f'Brak informacji o warstwie. Jeśli zaczynamy od listy trzeba ją podać jako '
                                f'parametr wywołania „parent_key”.')
            current_list.append({"layer": parent_key, "node": json_dict_or_list})

        if json_dict_or_list.get('LSide'):
            current_list.extend(nodes_list_from_tree(json_dict_or_list.get('LSide'), "root"))
        for l in ["Locations", "Characters", "Items", "Narration", "root"]:
            if json_dict_or_list.get(l):
                current_list.extend(nodes_list_from_tree(json_dict_or_list.get(l), l))
        return current_list

    elif isinstance(json_dict_or_list, list):
        current_list = []
        for element in json_dict_or_list:
            current_list.extend(nodes_list_from_tree(element, parent_key))
        return current_list
    return []

def param_instr_from_nodes_list(production: dict, *param_names: str) -> set:
    param_nodes_set = set()
    for element in production:
        if element['node'].get("Instructions"):
            for instruction in element['node']['Instructions']:
                for param in instruction:
                        if not param_names or (param_names and param in param_names):
                            param_nodes_set.add(instruction[param])
    return param_nodes_set


def list_from_tree(json_dict_or_list, parent_key: str = 'root') -> list:
    """
    Generating the list of nodes of the graph tree given.
    :param json_dict_or_list: the current level of graph tree. Dict for layer, list for nodes.
    :param parent_key: the layer name of the current root. If not applicable, use "root"
    :return: The list of nodes as a dictionary with all the node keys + "Layer" key which indicates layer (values: "Locations", "Characters", "Items", Narration")
    """
    if type(json_dict_or_list) in (int, float, bool, str):
        return []
    elif isinstance(json_dict_or_list, dict):
        current_dict = {}
        if parent_key != 'root':
            current_dict['Layer'] = parent_key
        current_list = []
        for k, v in json_dict_or_list.items():
            if k == 'LSide':
                current_list.extend(list_from_tree(v, 'root'))
            elif k in ('Id', 'Name', 'Attributes', 'Connections', 'Preconditions', 'Instructions'):
                current_dict[k] = v
            elif k in ['Locations', 'Characters', 'Items', 'Narration']:  # isinstance(v, list):
                current_list.extend(list_from_tree(v, k))
        if current_dict:
            current_list.append(current_dict)
        return current_list
    elif isinstance(json_dict_or_list, list):
        lst = json_dict_or_list
        current_list = []
        for i in range(len(lst)):
            current_list.extend(list_from_tree(lst[i], parent_key))
        return current_list


def world_copy(old_one, new_one, sort_elements = True):
    sort_elements = True
    if type(new_one) in (int, float, bool, str): # new_one, żeby nie wchodzić w destination, które w starym są obiektem
        return []
    elif isinstance(old_one, dict):
        new_one['Id'] = str(id(old_one))
        # if remove_connections and 'Connections' in new_one:
        #     del(new_one['Connections'])
        if 'Connections' in new_one:
            for dest1, dest2 in zip(old_one['Connections'], new_one['Connections']):
                # dest['Destination'] = str(dest['Destination']['Id'])
                dest2['Destination'] = str(id(dest1['Destination']))

        for old_k, new_k in zip(old_one, new_one):
            if old_k in ["Locations", "Characters", "Items", "Narration"]:
                world_copy(old_one[old_k], new_one[new_k], sort_elements)


        if sort_elements:
                if 'Attributes' in new_one:
                    temp_attributes = new_one['Attributes']
                    del (new_one['Attributes'])
                else:
                    temp_attributes = None
                if 'Characters' in new_one:
                    temp_characters = new_one['Characters']
                    del (new_one['Characters'])
                else:
                    temp_characters = None
                if 'Items' in new_one:
                    temp_items = new_one['Items']
                    del (new_one['Items'])
                else:
                    temp_items = None
                if 'Narration' in new_one:
                    temp_narration = new_one['Narration']
                    del (new_one['Narration'])
                else:
                    temp_narration = None
                if 'Connections' in new_one:
                    temp_connections = new_one['Connections']
                    del (new_one['Connections'])
                else:
                    temp_connections = None
                if 'Name' in new_one:
                    temp_name = new_one['Name']
                    del (new_one['Name'])
                else:
                    temp_name = None
                if 'Id' in new_one:
                    temp_id = new_one['Id']
                    del (new_one['Id'])
                else:
                    temp_id = None

                if temp_id:
                    new_one['Id'] = temp_id
                if temp_name:
                    new_one['Name'] = temp_name
                if temp_attributes:
                    new_one['Attributes'] = temp_attributes
                if temp_characters:
                    new_one['Characters'] = temp_characters
                if temp_items:
                    new_one['Items'] = temp_items
                if temp_narration:
                    new_one['Narration'] = temp_narration
                if temp_connections:
                    new_one['Connections'] = temp_connections


        return new_one
    elif isinstance(old_one, list):
        old_lst = old_one
        new_lst = new_one
        for i in range(len(old_lst)):
            world_copy(old_lst[i], new_lst[i], sort_elements)
        return new_one


def world_cut_ids(old_one):
    if type(old_one) in (
    int, float, bool, str):  # new_one, żeby nie wchodzić w destination, które w starym są obiektem
        return []
    elif isinstance(old_one, dict):
        if 'Id' in old_one:
            del(old_one['Id'])

        for old_k in old_one:
            if old_k in ["Locations", "Characters", "Items", "Narration"]:
                world_cut_ids(old_one[old_k])

        return old_one
    elif isinstance(old_one, list):
        old_lst = old_one

        for i in range(len(old_lst)):
            world_cut_ids(old_lst[i])
        return old_one


def attributes_from_nodes_list(nodes_list: list, layer: str = '') -> set:
    """
    Generates the set of node attributes used in the list of graph nodes
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param layer: optional parametr to limit the set to the ids of the one layer
    :return: The set of the used attributes
    """
    attributes_set = set()
    for element in nodes_list:
        try:
            if layer:
                if layer == element['layer']:
                    attributes_set.update(element['node']['Attributes'].keys())
            else:
                attributes_set.update(element['node']['Attributes'].keys())
        except:
            pass
    return attributes_set


def compute_lps(pattern: str) -> List[int]:
    # Longest Proper Prefix that is suffix array
    lps = [0] * len(pattern)

    prefi = 0
    for i in range(1, len(pattern)):

        # Phase 3: roll the prefix pointer back until match or
        # beginning of pattern is reached
        while prefi and pattern[i] != pattern[prefi]:
            prefi = lps[prefi - 1]

        # Phase 2: if match, record the LSP for the current `i`
        # and move prefix pointer
        if pattern[prefi] == pattern[i]:
            prefi += 1
            lps[i] = prefi

        # Phase 1: is implicit here because of the for loop and
        # conditions considered above

    return lps


def kmp(pattern: str, text: str) -> List[int]:
    match_indices = []
    pattern_lps = compute_lps(pattern)

    patterni = 0
    for i, ch in enumerate(text):

        # Phase 3: if a mismatch was found, roll back the pattern
        # index using the information in LPS
        while patterni and pattern[patterni] != ch:
            patterni = pattern_lps[patterni - 1]

        # Phase 2: if match
        if pattern[patterni] == ch:
            # If the end of a pattern is reached, record a result
            # and use information in LSP array to shift the index
            if patterni == len(pattern) - 1:
                match_indices.append(i - patterni)
                patterni = pattern_lps[patterni]

            else:
                # Move the pattern index forward
                patterni += 1

        # Phase 1: is implicit here because of the for loop and
        # conditions considered above

    return match_indices


def naive_search(short_list: List[str], long_list: List[dict]) -> List[int]:
    """
    Searches for all the occurrences of short list of strings in the long list of dicts.
    :param short_list: list of names and ids (and some wildcards: L_STAR, C_STAR, I_STAR and V_STAR)
    :param long_list: list of the world nodes (the names and ids as elements of dictionary)
    :return: List of the numbers representing the offset of occurrence
    """
    match_indices = []

    for nr in range(len(long_list)-len(short_list) + 1):
        match_indicator = True
        for nr2 in range(len(short_list)):
            # porównywanie zwykłych list wyglądałoby tak:
            # if short_list[nr2] != long_list[nr + nr2]:
            #     match_indicator = False
            #     break
            if short_list[nr2] == 'L_STAR':
                if nr + nr2 != 0:
                    match_indicator = False
                    break
            elif short_list[nr2] == 'C_STAR':
                if long_list[nr + nr2] not in long_list[nr + nr2 - 1]['Characters']:
                    match_indicator = False
                    break
            elif short_list[nr2] == 'I_STAR':
                if long_list[nr + nr2] not in long_list[nr + nr2 - 1]['Items']:
                    match_indicator = False
                    break
            elif short_list[nr2] == 'N_STAR':
                if long_list[nr + nr2] not in long_list[nr + nr2 - 1]['Narration']:
                    match_indicator = False
                    break
            elif short_list[nr2] != long_list[nr + nr2].get("Id"):
                if short_list[nr2] != long_list[nr + nr2].get("Name"):
                    match_indicator = False
                    break
        if match_indicator:
            match_indices.append(nr)
    return match_indices


def find_node_layer_name(parent: dict, child:dict) -> str:
    """
    Indicates the name of the layer in parent children list in which the child node is found
    :param parent: node in which children list is child
    :param child: node which layer is needed for further manipulations
    :return: name of the layer
    """
    for layer in ['Locations', 'Characters', 'Items', 'Narration']:
        if layer in parent and child in parent[layer]:
            return layer


def find_reference_leaves_single_graph(tree: Union[list, dict], reference: str) -> List:  # tree podajemy od layer
    """
    NOWE Finds the paths corresponding to given reference string. IGNORES the last element of ARRAY_REF if exists.
    :param reference: the string which indicates the leaf using a few of its ancestor to disambiguate.
    :param tree: the graph in which the path is searched
    :return: the sorted by length list of paths (list of lists of nodes starting from location, ending at leaf of reference)
    """
    # Założenie:
    # 1) ** zastępują parzystą liczbę segmentów, tzn następny po ** węzeł musi być poprzedzony segmentem
    #    Characters lub Items lub Narration.
    # 2) * jest poprzedzona wskazaniem warstwy.
    # Wniosek: Jeżeli chcemy połączyć ** i *, to między nimi jest wskazanie warstwy: np. Inn/**/Items/*
    # UWAGA: nie możemy np. policzyć wszystkich elementów z wszystkich warstw!

    def reference_order(l: list) -> int:
        return len(l)

    # print('--------------------------------')
    # print(reference)

    # czyścimy referencję
    reference = re.sub(r"^\*", "L_STAR", reference)
    reference = re.sub(r"/Characters/\*", "/C_STAR", reference)
    reference = re.sub(r"/Items/\*", "/I_STAR", reference)
    reference = re.sub(r"/Narration/\*", "/N_STAR", reference)
    reference_without_layers = re.sub(r"/(Characters|Items|Narration)", "", reference)
    # rozbijamy referencję na segmenty
    strips = reference_without_layers.split('/**/')
    strips_sliced = []
    for strip in strips:
        strips_sliced.append(strip.split('/'))
    # print(strips_sliced)

    # najczęstszy przypadek, w którym mamy po prostu id lub name
    if len(strips_sliced) == 1 and len(strips_sliced[0]) == 1:
        effect = breadcrumb_pointer(tree, name_or_id=strips_sliced[0][0])
        effect.sort(key=reference_order)
        return effect
        # szukamy węzłów kończących
    checked_leaves = []
    if strips_sliced[-1][-1] == 'C_STAR':
        unchecked_leaves = breadcrumb_pointer(tree, layer='Characters')
    elif strips_sliced[-1][-1] == 'I_STAR':
        unchecked_leaves = breadcrumb_pointer(tree, layer='Items')
    elif strips_sliced[-1][-1] == 'N_STAR':
        unchecked_leaves = breadcrumb_pointer(tree, layer='Narration')
    else:
        unchecked_leaves = breadcrumb_pointer(tree, name_or_id=strips_sliced[-1][-1])

    for leaf in unchecked_leaves:
        compatibility = True
        offset = len(leaf) - len(strips_sliced[-1])
        test_text = ''
        # for l in leaf:
        #     print(l.get("Id",l.get("Name")), end=" ")
        # print()

        # dopasowujemy wszystkie segmenty pomiędzy ** z wyjątkiem ostatniego
        if len(strips_sliced) > 1:
            offset2 = 0
            for strip in strips_sliced[0:-1]:
                # print(f"Strip {strips_sliced.index(strip)}: {strip}")
                before_star_match = naive_search(strip, leaf[offset2:offset])
                # print(before_star_match)
                if not before_star_match:
                    compatibility = False
                    break
                else:
                    # Tylko tworzenie tekstu dla celów diagnostycznych
                    for n in range(offset2 + before_star_match[0], offset2 + len(strip) + before_star_match[0]):
                        test_text += f"({n}) {strip[n-offset2-before_star_match[0]]}-{leaf[n].get('Id', leaf[n].get('Name'))} -> "
                    offset2 = offset2 + len(strip) + before_star_match[0]
                    test_text += f"... -> "

        # dopasowujemy ostatni segment
        if compatibility:
            last_strip_match = naive_search(strips_sliced[-1], leaf[offset:])
            if not last_strip_match:
                compatibility = False
            else:
                # Tylko tworzenie tekstu dla celów diagnostycznych
                for n in range(offset + last_strip_match[0], offset + len(strips_sliced[-1]) + last_strip_match[0]):
                    test_text += f"({n}) {strips_sliced[-1][n - offset - last_strip_match[0]]}-{leaf[n].get('Id', leaf[n].get('Name'))} -> "

        if compatibility:
            checked_leaves.append(leaf)
            # print(f"{test_text}Hurra")



    checked_leaves.sort(key=reference_order)

    return checked_leaves


def find_reference_leaves(ls_tree: Union[list, dict], variant: list, reference: str) -> List[List[dict]]:
    """
    NOWE Finds the paths of nodes in the world corresponding to given reference string.
    :param ls_tree: the graph in which the initial name or id is searched
    :param variant: the matched pairs of nodes from LS and world.
    :param reference: the string starting with LS name or id followed by world nodes names. The last is searched leaf
    :return: the list of paths in the world (nodes from location to leaf node) ordered by length.
    """
    # Założenie:
    # 1) ** zastępują parzystą liczbę segmentów, tzn następny po ** węzeł musi być poprzedzony segmentem
    #    Characters lub Items lub Narration.
    # 2) * jest poprzedzona wskazaniem warstwy.
    # Wniosek: Jeżeli chcemy połączyć ** i *, to między nimi jest wskazanie warstwy: np. Inn/**/Items/*
    # UWAGA: nie możemy wobec tego np. policzyć wszystkich elementów z wszystkich warstw! TODO przemyśleć
    # 3) Poprzez id wyrażony może być tylko pierwszy człon multireferencji (ten z produkcji), następne są już
    #    nazwami lub * (te ze świata)

    # UWAGA: Ponieważ często przydaje nam się rodzic liścia, nawet jeśli referencja jest jednoelementowa – oraz w celu
    # zachowana maksymalnej spójności skryptu – zwracamy ścieżkę od lokacji w świecie do liścia w świecie a nie tylko tę
    # jej część, która pokrywa się z referencją.

    def reference_order(given_list: list) -> int:
        return len(given_list)

    qdebug('--------------------------------')
    qdebug(reference)

    # czyścimy referencję
    reference = re.sub(r"^\*", "L_STAR", reference)
    reference = re.sub(r"/Characters/\*", "/C_STAR", reference)
    reference = re.sub(r"/Items/\*", "/I_STAR", reference)
    reference = re.sub(r"/Narration/\*", "/N_STAR", reference)
    reference_without_layers = re.sub(r"/(Characters|Items|Narration)", "", reference)

    # rozbijamy referencję na segmenty
    strips = reference_without_layers.split('/**/')
    strips_sliced = []
    for strip in strips:
        strips_sliced.append(strip.split('/'))
    qdebug(strips_sliced)

    # szukamy punktu zaczepienia multireferencji
    root_ls_paths = breadcrumb_pointer(ls_tree, name_or_id=strips_sliced[0][0])
    if root_ls_paths and len(root_ls_paths) == 1:
        root_w_path = []
        for node in root_ls_paths[0]:  # uwaga, dodaję rozwinięcie w świecie ścieżki węzła inicjalnego z lewej strony
             root_w_path.append(ls_to_world(node, variant))
        root_w = root_w_path[-1]
        if len(root_w_path) > 1:
            root_w_layer = find_node_layer_name(root_w_path[-2], root_w_path[-1])
        else:
            root_w_layer = 'Locations'
        strips_sliced[0][0] = root_w.get('Name')
        if not root_w:
            qdebug(f"Nie udało się znaleźć w multireferencji odpowiednika węzła {root_ls_paths[0][-1].get('Id', root_ls_paths[0][-1].get('Name'))} w świecie.")
            return []
    elif root_ls_paths and len(root_ls_paths) > 1:
        qdebug(f"Niejednoznacznie wskazany początek multireferencji {reference}!")
        return []
    else:
        qdebug(f"Nie udało się znaleźć multireferencji {reference}!")
        return []

    # I teraz już przechodzimy do poszukiwań rozwinięcia referencji w świecie
    # Przypominam założenie: przez id wyraża się co najwyżej pierwszy człon referencji

    # najczęstszy przypadek, w którym mamy po prostu id lub name
    if len(strips_sliced) == 1 and len(strips_sliced[0]) == 1:
        return [root_w_path]

    # szukamy węzłów kończących
    checked_leaves = []
    if strips_sliced[-1][-1] == 'C_STAR':
        unchecked_leaves = breadcrumb_pointer(root_w, layer='Characters', parent_key=root_w_layer)
    elif strips_sliced[-1][-1] == 'I_STAR':
        unchecked_leaves = breadcrumb_pointer(root_w, layer='Items', parent_key=root_w_layer)
    elif strips_sliced[-1][-1] == 'N_STAR':
        unchecked_leaves = breadcrumb_pointer(root_w, layer='Narration', parent_key=root_w_layer)
    else:
        unchecked_leaves = breadcrumb_pointer(root_w, name_or_id=strips_sliced[-1][-1])
    # UWAGA: tutaj breadcrumby wyjątkowo nie idą od lokacji, ponieważ idą od root_w

    # szukamy pasujących ścieżek
    for leaf in unchecked_leaves:
        compatibility = True
        offset = len(leaf) - len(strips_sliced[-1])
        test_text = ''
        for l in leaf:
            qdebug(l.get("Id",l.get("Name")), end=" ")
            qdebug("\n")

        # dopasowujemy wszystkie segmenty pomiędzy ** z wyjątkiem ostatniego
        if len(strips_sliced) > 1:
            offset2 = 0
            for strip in strips_sliced[0:-1]:
                before_star_match = naive_search(strip, leaf[offset2:offset])
                if not before_star_match:
                    compatibility = False
                    break
                else:
                    # Tylko tworzenie tekstu dla celów diagnostycznych
                    for n in range(offset2 + before_star_match[0], offset2 + len(strip) + before_star_match[0]):
                        test_text += f"({n}) {strip[n-offset2-before_star_match[0]]}-{leaf[n].get('Id', leaf[n].get('Name'))} -> "
                    offset2 = offset2 + len(strip) + before_star_match[0]
                    test_text += f"... -> "

        # dopasowujemy ostatni segment
        if compatibility:
            last_strip_match = naive_search(strips_sliced[-1], leaf[offset:])
            if not last_strip_match:
                compatibility = False
            else:
                # Tylko tworzenie tekstu dla celów diagnostycznych
                for n in range(offset + last_strip_match[0], offset + len(strips_sliced[-1]) + last_strip_match[0]):
                    test_text += f"({n}) {strips_sliced[-1][n - offset - last_strip_match[0]]}-{leaf[n].get('Id', leaf[n].get('Name'))} -> "

        if compatibility:
            checked_leaves.append(leaf)
            qdebug(f"{test_text}Hurra")

    # dodajemy ścieżkę od lokacji do inicjalnego węzła referencji
    full_paths_of_multireference_leaves = []
    checked_leaves.sort(key=reference_order)
    for path in checked_leaves:
        full_paths_of_multireference_leaves.append(root_w_path[0:-1] + path)

    return full_paths_of_multireference_leaves

def show_path(path: list, delimiter: str=None) -> str:
    strip = ''
    if not delimiter:
        delimiter = '->'
    for element in path[0:-1]:
        strip += element.get('Id', element.get('Name')) + delimiter
    strip+= path[-1].get('Id', path[-1].get('Name'))
    return strip


def node_description(world, path: list, show_attr: bool = True) -> str:
    if path[-1].get('Id'):
        name_text = path[-1].get('Id')
        if path[-1].get('Name'):
            name_text += f' ({path[-1].get("Name")})'
    else:
        name_text = path[-1].get("Name")

    if len(path) == 1:
        layer = 'Locations'
        conn_out = False
        conn_out_names = []
        conn_in = False
        conn_in_names = []
        path_text = ''
        if 'Connections' in path[-1]:
            conn_out = True
            for dest in path[-1]['Connections']:
                conn_out_names.append(dest['Destination'].get('Id', dest['Destination'].get('Name')))
        for location in world:
            if 'Connections' in location:
                for dest in location['Connections']:
                    if dest['Destination'] is path[-1]:  # zm
                        conn_in = True
                        conn_in_names.append(location.get('Id', location.get('Name')))

        if conn_in and conn_out:
            connection_text = ', wejście od: '
            for conn in conn_in_names:
                connection_text += f'{conn}, '
            connection_text = connection_text.rstrip(', ')
            connection_text += ' a wyjście do: '
            for conn in conn_out_names:
                connection_text += f'{conn}, '
            connection_text = connection_text.rstrip(', ')
        elif conn_in:
            connection_text = ', wejście od: '
            for conn in conn_in_names:
                connection_text += f'{conn}, '
            connection_text += 'ale brak wyjść'
        elif conn_out:
            connection_text = ', brak wejść, ale wyjście do: '
            for conn in conn_out_names:
                connection_text += f'{conn}, '
            connection_text = connection_text.rstrip(', ')
        else:
            connection_text = ' jest lokacją izolowaną'


    else:
        connection_text = ''
        layer = find_node_layer_name(path[-2], path[-1])
        path_text = f', ścieżka: {show_path(path)}'
    children_len = 0
    for children_layer in ['Characters', 'Items', 'Narration']:
        if children_layer in path[-1]:
            children_len += len(path[-1][children_layer])
    if not children_len:
        children_text = ', nie ma dzieci'
    elif children_len == 1:
        children_text = ', ma 1 dziecko'
    else:
        children_text = f', ma {children_len} dzieci'

    description = f'Węzeł {name_text} z warstwy {layer}{path_text}{children_text}{connection_text}.'
    if show_attr:
        if 'Attributes' in path[-1] and len(path[-1]["Attributes"]):
            description += f'\n     Atrybuty: {path[-1]["Attributes"]}.'
        else:
            description += f' Nie ma zdefiniowanych atrybutów.'

    return description


def draw_production_tree(production_dict, missing = None, mission_name = None, directory_path='../visualisation/out_hierarchy_new'):
    if mission_name is None:
        mission_name = f'missions_{datetime.now().strftime("%Y%m%d%H%M%S")}'
    node_attributes = {
        'shape': 'box',
        'style': 'filled',
        # 'fillcolor': 'white',
        # 'width': '10'
        # 'color': background_colors[parent_key],
    }
    graph = graphviz.Digraph(engine='dot')
    graph.attr(overlap='false')
    graph.attr(splines='polyline')
    graph.attr(dpi='150')
    graph.attr(ratio='fill')
    graph.attr(labelloc='t')
    graph.attr(rankdir='LR')
    graph.attr(shape='box')

    graph.node('root')
    if missing:
        graph.node('start','', fillcolor='white', color='white', style='filled')
        graph.edge('start', 'root', fillcolor='white', color='white')
        graph.node('missing', fillcolor='#F8CECC', color='red', style='filled')
        graph.edge('start', 'missing', fillcolor='white', color='white')
        for t in missing:
            graph.node(t.split(" / ")[0], fillcolor='#F8CECC', color='red', style='filled', shape='box')
            graph.edge('missing', t.split(" / ")[0], color='red')

    for p, v in production_dict.items():
        nodes_list = nodes_list_from_tree(v["prod"]['LSide'])
        gen_locations = False
        gen_others = False
        for node in nodes_list:
            if node['layer'] == "Locations" and not node['node'].get('Name'):
                gen_locations = True
            if node['layer'] != "Locations" and not node['node'].get('Name'):
                gen_others = True
        if "Użyto „?”" in v["prod"].get("Comment",""):
            fc = '#f5f5f5'
        elif gen_others:
            fc = 'white'
        elif gen_locations:
            fc = '#e8f2e8'
        else:
            fc = '#D5E8D4'
        graph.node(p.split(" / ")[0], **node_attributes, fillcolor=fc)
        if v["parent"] != 'missing':
            if  v.get("hierarchy_mismatch"):
                edge_attributes = { 'style': 'dashed', 'color': 'red', "fontcolor": 'red'}
                edge_label = v.get("hierarchy_mismatch")
            else:
                edge_attributes = {
                    # 'style': 'solid', 'color': 'black'
                }
                edge_label = None

            graph.edge(v["parent"].split(" / ")[0], p.split(" / ")[0], label=edge_label, **edge_attributes)
        else:

            graph.edge(v["prod"]["TitleGeneric"].split(" / ")[0], p.split(" / ")[0])
    # if len(production_missing['missing']):
    #     graph.node('start')
    #     graph.edge('start', 'root')
    #     graph.node('missing', fillcolor='#F8CECC', color='red', style='filled')
    #     graph.edge('start', 'missing')

    graph.render(format='png', filename=f'{mission_name}',
                 directory=directory_path, cleanup=True)


def destinations_change_to_nodes(locations: list, world=False, remove_ids = True) -> bool:
    for location in locations:
        if 'Connections' in location:
            for dest in location['Connections']:
                if type(dest['Destination']) == str:
                    destination_nodes = breadcrumb_pointer(locations, name_or_id=dest['Destination'])
                    if len(destination_nodes) > 1:
                        dest_text =''
                        for dest_path in destination_nodes:
                            dest_text += f", {dest_path[-1].get('Name') or ''}"
                        print(f"Dopasowanie nie jest jednoznaczne{dest_text} mają to samo id.")
                        return False
                    elif len(destination_nodes) == 1:
                        dest['Destination'] = destination_nodes[0][-1]
                    else:
                        print(f"Nie znaleziono dopasowania {dest['Destination']}!")
                        return False
    if world:
        world_cut_ids(locations)
        # for location in locations:
        #     if remove_ids and location.get('Id'):
        #         del(location['Id'])
                # location['Id'] = id(location) # zostawiamy Id ale świeże, żeby mieć łatwiej przy zapisywaniu
    return True


def add_mandatory_attributes(world_elements:list, attributes: dict):
    modified_nodes = []
    for layer in attributes:
        for element in world_elements:
            if element['layer'] == layer:
                if "Attributes" not in element['node']:
                    element['node']["Attributes"] = {}
                for a, v in attributes[layer].items():
                    if a not in element['node']["Attributes"]:
                        element['node']["Attributes"][a] = v
                        print(f"{element['node'].get('Id', element['node'].get('Name'))} – {a}: {v}")
                        modified_nodes.append(id(element['node']))
    if not modified_nodes:
        print("Żadne atrybuty nie wymagały uzupełnienia.")
    return modified_nodes


def ls_to_world(node: dict, variant: list) -> dict:
    """
    Finds the world node match in the list of matched pairs to the given LS node.
    :param node: node from LS
    :param variant: list of pairs of matched nodes: left from the production nodespace and right form the world nodespace
    :return: node form the world
    """
    for pair in variant:
        if pair[0] is node:
            return pair[1]
    return {}


def get_quest_nr(quest_title: str, json_list: list) -> int:
    for nr, quest in enumerate(json_list):
        if os.path.split(quest['file_path'])[-1].split('.')[0] == quest_title:
            return nr


def eval_expression_po_rozmowie_z_Wojtkiem(expression: str, package):
    from types import SimpleNamespace

    translator = {}
    for pair in package:
        # przypisuję nowemu obiektowi wszystkie atrybuty dopasowanego węzła świata, nawet jeżeli w LS nie zostały przywołane
        if "Attributes" in pair[1] and len(pair[1]['Attributes']):
            translator[pair[0].get('Id', pair[0].get('Name'))] = SimpleNamespace(**pair[1]['Attributes'])

    return eval(expression, translator)


def personalise_description(description: str, variant):
    dict_from_variant = {}
    for pair in variant:
        dict_from_variant[pair[0].get('Id', pair[0].get('Name'))] = pair[1].get('Name')

    description_to_eval = '"' + description.replace('«', '" + ').replace('»', '+ "') + '"'

    # translator = {}
    # for pair in variant:
    #     # przypisuję nowemu obiektowi wszystkie atrybuty dopasowanego węzła świata, nawet jeżeli w LS nie zostały przywołane
    #     if "Attributes" in pair[1] and len(pair[1]['Attributes']):
    #         translator[pair[0].get('Id', pair[0].get('Name'))] = SimpleNamespace(**pair[1]['Attributes'])
    #

    return eval(description_to_eval, dict_from_variant)


def sheaf_description(location):
    print(f'     ┌──────────────────────────────────────────────────────────────────────────────────────')
    print(f'     │ Lokacja {location.get("Name")} {"ma pewne właściwości: " + str(location.get("Attributes")) if location.get("Attributes") else "nie ma żadnych własności"}.')
    if location.get("Items") and len(location['Items']) > 0:
        print(f'     │ Znajduje się w niej: ')
        for ch in location['Items']:
            print(f'     │ ❑ {ch.get("Name")} {ch.get("Attributes") or ""}')


    if location.get("Characters") and len(location['Characters']) > 0:
        print(f'     │ Przebywa{"ją" if len(location["Characters"]) > 1 else ""} w niej:')
        for ch in location['Characters']:
            print(f'     │ ☺ {ch.get("Name")} {ch.get("Attributes") or ""}')
            if ch.get("Items") and len(ch['Items']) > 0:
                print('     │     który posiada przedmioty:')
                for it in ch['Items']:
                    print(f'     │     ❑ {it.get("Name")} {it.get("Attributes") or ""}')
            if ch.get("Characters") and len(ch['Characters']) > 0:
                print('     │     który kieruje losem postaci:')
                for it in ch['Characters']:
                    print(f'     │     ☹ {it.get("Name")} {it.get("Attributes") or ""}')
            if ch.get("Narration") and len(ch['Narration']) > 0:
                knowledge_text = False
                for it in ch['Narration']:
                    if it.get('Attributes') and len(it['Attributes']) > 0:
                        if it.get('Attributes').get('Knowledge'):
                            if not knowledge_text:
                                print(f'     │     który wie, że:')
                                knowledge_text = True
                            print_lines(it.get("Attributes").get("Knowledge"), 80, prefix=f'     │     🕮 ', prefix2=f'     │        ')
                sound_text = False
                for it in ch['Narration']:
                    if it.get('Attributes') and len(it['Attributes']) > 0:
                        if it.get('Attributes').get('Sound'):
                            if not sound_text:
                                print(f'     │     który:')
                                sound_text = True
                            print_lines(it.get("Attributes").get("Sound"), 80, prefix=f'     │     🕭 ', prefix2=f'     │        ')
    else:
        print(f'     │ Nikogo w niej nie ma.')

    print(f'     └──────────────────────────────────────────────────────────────────────────────────────')


def action_description(production, variant):
    description = personalise_description(production["Description"], variant)
    print(f'     ┌──────────────────────────────────────────────────────────────────────────────────────')
    print_lines(f'{production["Title"].split(" / ")[1]}. {description}', 80, prefix='     │ ')
    print(f'     └──────────────────────────────────────────────────────────────────────────────────────')


def print_lines(given_text, line_limit, prefix = '', prefix2 = '', suffix = '', ole_avoid = True):
    # „ole” stands for „one letter endings”

    given_text = re.sub(r" ?\n", r" \n", given_text)
    text_words = given_text.split(" ")
    word_limit = max([len(x) + 1 for x in text_words])
    if word_limit >= line_limit:
        line_limit = word_limit
        ole_avoid = False
    line = ''
    first_line = True
    if not prefix2:
        prefix2 = prefix
    for nr, word in enumerate(text_words):
        if not word:
            continue
        if (word[0] == "\n") or (len(line) + len(word) + 1 > line_limit) or \
        (nr < len(text_words) - 2 and ole_avoid and len(word) == 1 and len(line) + len(word) + 1 + len(text_words[nr + 1]) + 1 > line_limit):
            print(prefix if first_line else prefix2, line, end='', sep='')
            first_line = False
            if suffix:
                print(" " * (line_limit - len(line)), end='', sep='')
                print(suffix)
            else:
                print()
            if word[0] == "\n":
                if len(word) > 1:
                    word = word[1:]
                else:
                    word =''

            line = word + (' ' if word else '')

        else:
            line += word + ' '
    if len(line) > 1:
        print(prefix if first_line else prefix2, line[:-1], end='', sep='')
        if suffix:
            print(" " * (line_limit - len(line[:-1])), end='', sep='')
            print(suffix)
        else:
            print()
    return


def ls_convert_to_world(production):
    print("ls_convert_to_world Jeszcze nie gotowe")
    return False

def paths_convert_to_text(paths:list):
    paths_text = ''
    for nr, path in enumerate(paths):
        for nr2, element in enumerate(path):
            if nr2 > 0:
                paths_text += "/"
            paths_text += f"{element.get('Id',element.get('Name'))}"
        if nr > len(paths)-1:
            paths_text += ", "
    return paths_text
