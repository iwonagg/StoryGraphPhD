import json
from copy import deepcopy
from json import JSONDecodeError
from typing import Tuple, List, Union, Dict

import re
from jsonschema import Draft7Validator

from config.config import path_root
from json_validation.json_schema import schema, schema_sheaf

from library.tools import get_json_files_paths, print_lines, nodes_list_from_tree, breadcrumb_pointer, \
    attributes_from_nodes_list, find_node_layer_name, paths_convert_to_text


def name_in_allowed_names(name: str, layer: str) -> bool:
    """
    Checks if the given string is a valid name of the given layer
    :param name: given name
    :param layer: given layer
    :return: True or False
    """
    allowed_locations = json.load(open('../json_validation/allowed_names/locations.json', encoding="utf8"))
    allowed_locations += json.load(open('../json_validation/allowed_names/locations_Wojtek.json', encoding="utf8"))
    allowed_characters = json.load(open('../json_validation/allowed_names/characters.json', encoding="utf8"))
    allowed_characters += json.load(open('../json_validation/allowed_names/characters_Wojtek.json', encoding="utf8"))
    allowed_items = json.load(open('../json_validation/allowed_names/items.json', encoding="utf8"))
    allowed_items += json.load(open('../json_validation/allowed_names/items_Wojtek.json', encoding="utf8"))

    if layer == 'Locations' and name in allowed_locations:
        return True
    elif layer == 'Characters' and name in allowed_characters:
        return True
    elif layer == 'Items' and name in allowed_items:
        return True
    elif layer == 'Narration' and name not in allowed_locations + allowed_characters + allowed_items:
        return True

    return False


def get_generic_productions_from_file(generic_path: str) -> Tuple[dict, dict]:
    """
    Temporary function to get dict of the generic productions from one given file. Used in API to extend the production list
    :param generic_path: file location + name
    :return: dict of productions, dict of errors with the key of the filepath
    """
    production_titles_dict = {}
    errors = {}
    # generic_schema_validated, errors = get_jsons_schema_validated(generic_path, json_schema_path, mask)
    generic_schema_validated = json.load(open(generic_path, encoding="utf8"))

    # budowanie listy nazw produkcji i sprawdzanie ich unikalności

    for production in generic_schema_validated:
        if production['Title'] not in production_titles_dict:
            production_titles_dict[production['Title']] = {"production": production, "file_path": generic_path}
        else:
            err_comm = f'Tytuł produkcji „{production["Title"]}” został już użyty w pliku: \n{ production_titles_dict[production["Title"]]["file_path"]}.'
            if production == production_titles_dict[production["Title"]]["production"]:
                err_comm += "\nProdukcje te są identyczne. Proszę poprawić lub usunąć drugą."
            else:
                err_comm += "\nProdukcje te się różną. Proszę poprawić lub usunąć drugą."
            if generic_path not in errors:
                errors[generic_path] = {}

            errors[generic_path][production["Title"]] = [err_comm]


    return production_titles_dict, errors


def get_allowed_names() -> dict:
    """
    Imports the allowed nodes names from the JSON files located in json_validation folder.
    :return: The dict with three keys: "Locations", "Characters", "Items" and lists of names as values.
    """
    allowed_locations = json.load(open('../json_validation/allowed_names/locations.json', encoding="utf8"))
    allowed_locations += json.load(open('../json_validation/allowed_names/locations_Wojtek.json', encoding="utf8"))

    allowed_characters = json.load(open('../json_validation/allowed_names/characters.json', encoding="utf8"))
    allowed_characters += json.load(open('../json_validation/allowed_names/characters_Wojtek.json', encoding="utf8"))

    allowed_items = json.load(open('../json_validation/allowed_names/items.json', encoding="utf8"))
    allowed_items += json.load(open('../json_validation/allowed_names/items_Wojtek.json', encoding="utf8"))

    allowed_names = {"Locations": allowed_locations, "Characters": allowed_characters, "Items": allowed_items}

    return allowed_names


def get_prod_ids(nodes_list: List[dict]) -> Tuple[List[str], List[str]]:
    """
    Gets list of the node ids used in the production LHS
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :return: list of errors, list of ids
    """
    ids_list = []
    errors = []
    for n in nodes_list:
        if n["node"].get("Id"):
            if n["node"].get("Id") in ids_list:
                errors.append(f'Id „{n["node"].get("Id")}” nie jest unikalne w lewej stronie produkcji.')
            else:
                ids_list.append(n["node"].get("Id"))

    return errors, ids_list


def get_prods_names_count(nodes_list: List[dict]) -> dict:
    """
    Gets dict of the node names used in the production LHS with counter as value
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :return: dict of name: counter
    """
    names_dict = {}
    for n in nodes_list:
        if n["node"].get("Name"):
            if names_dict.get(n["node"]["Name"]):
                names_dict[n["node"]["Name"]] += 1
            else:
                names_dict[n["node"]["Name"]] = 1

    return names_dict


def check_attribute_name(attr_name: str) -> Tuple[List[str], List[str]]:
    """
    Validates structure of the attribute name as string of PascalCase letters, digits or ?
    :param attr_name: Attribute name
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    if attr_name == "?":
        warnings.append(f'Produkcja zawierająca atrybut o nazwie „?” jest produkcją wzorcową, nie do stosowania.')
    elif not re.fullmatch(r"[A-Z][A-Za-z0-9]*", attr_name):
        errors.append(f'Nazwa atrybutu: „{attr_name}” nie spełnia warunku PascalCase i zawierania wyłącznie liter i cyfr.')

    return errors, warnings


def check_identifier(identifier_to_check: str, tree: Union[dict, list] = None, nodes_list: List[dict] = None,
                     name_as_id_warning: bool = False) -> Tuple[List[str], List[str], dict]:
    """
    Checks if the given string is an unambiguous identifier of LHS
    :param identifier_to_check: possible identifier
    :param tree: graph
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param name_as_id_warning: rather unnecessary constraint
    :return: list of errors, list of warnings, layer-described node found from node_list or new structure (dict: "layer", "node"), where node value is from tree
    """
    errors = []
    warnings = []
    result_node = {}

    if tree:
        first_segment_paths = breadcrumb_pointer(tree, name_or_id=identifier_to_check)

        if len(first_segment_paths) == 0:
            errors.append(f"Nazwa „{identifier_to_check}” nie jest identyfikatorem żadnego węzła w lewej stronie produkcji.")
        elif len(first_segment_paths) > 1:
            errors.append(f"Nazwa „{identifier_to_check}” nie jest jednoznacznym identyfikatorem w lewej stronie produkcji.")
        else:
            if len(first_segment_paths) == 1:
                layer = "Locations"
            else:
                layer = find_node_layer_name(first_segment_paths[0][-2], first_segment_paths[0][-1])
            result_node = {"layer": layer, "node": first_segment_paths[0][-1]}

            # zastrzeżenie przypuszczalnie do wycięcia
            if name_as_id_warning and first_segment_paths[0][-1].get("Name") == identifier_to_check:
                warnings.append(f'Po instrukcji zwiększającej liczbę węzłów (create, copy) nie wiem, czy identyfikowanie '
                                f'obiektów lewej strony produkcji poprzez nazwę może dać efekt różny od spodziewanego.')

    elif nodes_list:
        first_segments = []
        for n in nodes_list:
            if n["node"].get("Id", n["node"].get("Name")) == identifier_to_check:
                first_segments.append(n)

                # zastrzeżenie przypuszczalnie do wycięcia
                if name_as_id_warning and n["node"].get("Name") == identifier_to_check:
                    warnings.append(
                        f'Po instrukcji zwiększającej liczbę węzłów (create, copy) nie wiem, czy identyfikowanie '
                        f'obiektów lewej strony produkcji poprzez nazwę może dać efekt różny od spodziewanego.')

        if len(first_segments) == 0:
            errors.append(f"Nazwa „{identifier_to_check}” nie jest identyfikatorem żadnego węzła w lewej stronie produkcji.")
        elif len(first_segments) > 1:
            errors.append(f"Nazwa „{identifier_to_check}” nie jest jednoznacznym identyfikatorem w lewej stronie produkcji.")
        else:
            result_node = first_segments[0]



    else:
        # jeżeli żaden z argumentów: tree, nodes_list nie był podany
        warnings.append(f"Tekst „{identifier_to_check}” nie został zweryfikowany jako identyfikator ze względu na "
                        f"niepoprawnie podany parametr funkcji check_identifiers().")

    return errors, warnings, result_node


def check_multifererence_world_part(world_part: Union[list, str], allowed_names: Dict[str, List[str]], prod_ids: List[str] = None) -> Tuple[List[str], List[str]]:
    """
    Checks if the given string or list of substrings is a valid world part MULTI-REF string
    :param world_part: the given string
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :param prod_ids: list of the node ids used in the production LHS
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    # ujednolicamy format argumentów wejściowych
    if type(world_part) == list:
        multireference_split = world_part
    else:
        multireference_split = world_part.split('/')

    # sprawdzamy poprawność części światowej multireferencji
    if len(multireference_split) % 2 != 0:
        errors.append(f'Multireferencja „…/{"/".join(multireference_split)}” ma niewłaściwą liczbę segmentów.')

    else:
        # for layer in multireference_split[::2]:
        #     if layer not in ["Characters", "Items", "Narration"]:
        #         errors.append(f'Co drugi segment multireferencji nie jest nazwą warstwy: „…{"/".join(multireference_split)}”.')
        #         break
        #         return errors, warnings

        # sprawdzamy każdą parę warstwa, nazwa
        for nr in range(len(multireference_split))[::2]:
            # czy pierwszy człon jest warstwą
            if multireference_split[nr] not in ["Characters", "Items", "Narration"]:
                errors.append(f'Co drugi segment multireferencji nie jest nazwą warstwy: „…{"/".join(multireference_split)}”.')
                break
            # czy drugi człon nie jest id
            if prod_ids and multireference_split[nr + 1] in prod_ids:
                errors.append(f'Tekst „{multireference_split[nr + 1]}” to id a nie nazwa, więc nie może znajdować się w drugiej '
                              f'części multirferencji.')
            # czy drugi człon jest nazwą i to z właściwej warstwy
            elif (multireference_split[nr] != "Narration") and (multireference_split[nr + 1] not in allowed_names[multireference_split[nr]] + ['**', '*']):
                errors.append(f'Tekst „{multireference_split[nr + 1]}” znajduje się w multireferencji '
                    f'„…{"/".join(multireference_split)}” jako nazwa, a nie jest dozwoloną nazwą w świecie lub jest '
                    f'nazwą z inne warstwy niż wskazana w członie poprzedzającym („{multireference_split[nr]}”).')
            # jeśli wskazujemy węzeł z warstwy narracyjnej to niewiele możemy sprawdzić
            elif (multireference_split[nr] == "Narration") and not re.fullmatch(r"([A-Z][A-Za-z0-9_]*|\*|\*\*)", multireference_split[nr + 1]):
                warnings.append(f'Nazwa „{multireference_split[nr + 1]}” z warstwy „Narration” nie spełnia ogólnego '
                                f'wzorca nazw, to może być literówka.')

        # wszystkie człony są poprawne, co sprawdziliśmy powyżej, ale pojedynczy obiekt może być fragmentem lewej strony
        # to częsty błąd, więc ostrzegamy
        # wydaje się jednak, że to redundantne ostrzeżenie w kontekście sprawdzania ostatniego członu w funkcji
        # preconditions_validation_errors
        # if "*" not in "/".join(multireference_split):  # było: "*" not in "/".join(multireference_split)
        #     warnings.append(f'Multireferencja wielosegmentowa „…/{"/".join(multireference_split)}” wskazuje konkretny '
        #                     f'obiekt. Jeśli jest dopasowany w lewej stronie produkcji, to lepiej wskazać go '
        #                     f'bezpośrednio przez id lub nazwę (jeśli jest jednoznaczna).')

    return errors, warnings


def check_array_ref(array_ref: Union[list, str], tree: Union[dict, list] = None, nodes_list: List[dict] = None, param: str = None, name_as_id_warning: bool = None) -> Tuple[List[str], List[str]]:
    """
    Checks if the given string is correct ARRAY-REF.
    :param array_ref: possible array_ref
    :param tree: graph
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param name_as_id_warning: rather unnecessary constraint
    :param param: operation parameter in which the array_ref is used. Only to be displayed for user
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    # ujednolicamy format argumentów wejściowych
    if type(array_ref) == list:
        array_ref_split = array_ref
    else:
        array_ref_split = array_ref.split('/')

    if len(array_ref_split) != 2:
        errors.append(f'Referencja tablicowa „{array_ref}” {f"w parametrze „{param}” " if param else ""}musi składać się z dwóch '
                      f'segmentów: NODE-REF i nazwy warstwy.')
    else:
        # sprawdzamy poprawność pierwszej części
        first_segment = array_ref_split[0]
        id_check_err, id_check_wrn, id_result = check_identifier(first_segment, tree=tree, nodes_list=nodes_list, name_as_id_warning=name_as_id_warning)
        errors.extend(id_check_err)
        warnings.extend(id_check_wrn)

        # sprawdzamy poprawność drugiej części
        last_segment = array_ref_split[-1]
        if last_segment == "Locations":
            errors.append(f'Warstwa w referencji tablicowej {f"w parametrze „{param}” " if param else ""}nie może być '
                          f'warstwą lokacji, ponieważ w produkcjach nie wolno modyfikować warstwy lokacji.')
        elif last_segment not in ['Characters', 'Items', 'Narration']:
            errors.append(f'Drugi segment referencji tablicowej {f"w parametrze „{param}” " if param else ""}nie jest '
                          f'poprawną nazwą warstwy.')

    return errors, warnings


def check_node_ref_attr_name(reference: Union[list, str], tree: Union[dict, list] = None, nodes_list: List[dict] = None,
                             attr_exist: bool = False, name_as_id_warning: bool = False) -> Tuple[List[str], List[str], Tuple[dict, str]]:
    """
    Checks if reference is valid NODE-REF.ATTR-NAME structure.
    :param reference: given reference, already split or not
    :param tree: graph
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param attr_exist: indicates the attribute existence necessity
    :param name_as_id_warning: rather unnecessary constraint
    :return: list of errors, list of warnings, tuple of layer-described node and attribute name
    """
    errors = []
    warnings = []
    result = []

    # ujednolicamy format argumentów wejściowych
    if type(reference) == list:
        node_ref_attr_name = reference
    else:
        node_ref_attr_name = reference.split(".")

    if len(node_ref_attr_name) != 2:
        errors.append(
            f'Parametr „Attribute” musi składać się z dwóch części: identyfikatora węzła i nazwy atrybutu po kropce.')
    else:
        # sprawdzanie poprawności pierwszej części
        node_ref_err, node_ref_wrn, id_result = check_identifier(node_ref_attr_name[0], tree=tree, nodes_list=nodes_list, name_as_id_warning=name_as_id_warning)
        errors.extend(node_ref_err)
        warnings.extend(node_ref_wrn)
        # sprawdzanie poprawności drugiej części
        attr_name_err, attr_name_wrn = check_attribute_name(node_ref_attr_name[1])
        errors.extend(attr_name_err)
        warnings.extend(attr_name_wrn)

        if not node_ref_err and not attr_name_err:

            result = (id_result, node_ref_attr_name[1])

            if attr_exist:
                if "Attributes" not in id_result["node"] or node_ref_attr_name[1] not in id_result["node"]["Attributes"]:
                    warnings.append(f'Węzeł „{node_ref_attr_name[0]}” nie posiada atrybutu „{node_ref_attr_name[1]}” '
                        f'w warunkach dopasowania. Jeżeli węzeł dopasowany w świecie taki atrybut posiada, to zostanie '
                        f'on wykorzystany, w przeciwnym razie działanie zakończy się niepowodzeniem.')
                # TODO sprawdzić, czy warning, czy error powinien być

    return errors, warnings, result


def production_metainfo_validation(production: dict, generic_prod_dict: dict = None, prod_ids: List[str] = None) -> Tuple[List[str], List[str]]:
    """
    Validates the meta information of production: generic parenting, language etc.
    :param production: graph production
    :param generic_prod_dict: dictionary of all productions being checked {title: {"production", "file_path"}}
    :param prod_ids: list of the node ids used in the production LHS
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []

    if prod_ids is None:
        ids_err, prod_ids = get_prod_ids(nodes_list_from_tree(production['LSide']))

    if len(production['Title'].split(' / ')) != 2:
        errors.append(f'Tytuł produkcji powinien składać się z dwóch części, tytułu po angielsku i po polsku '
            f'oddzielonych „ / ”, a nie: „{production["Title"]}”.')
    if production['TitleGeneric'] and len(production['TitleGeneric'].split(' / ')) != 2:
        errors.append(f'Tytuł produkcji generycznej powinien składać się z dwóch części, tytułu po angielsku i po polsku '
            f'oddzielonych „ / ”, a nie: „{production["TitleGeneric"]}”.')
    if production['Title'] == production['TitleGeneric']:
        errors.append(f'Tytuł produkcji generycznej powinien różnić się od tytułu produkcji analizowanej.')

    if not generic_prod_dict:
        warnings.append(f'Istnienie produkcji generycznej nie zostało zweryfikowane.')
    elif production['TitleGeneric'] and production['TitleGeneric'] not in generic_prod_dict:
        errors.append(f'Produkcji generycznej „{production["TitleGeneric"]}” nie ma w sprawdzanym zbiorze produkcji.')

    if len(production['Description']) == 0 or production['Description'][-1] not in {'.', '?', '!', '…'}:
        errors.append(
            f'Opis produkcji powinien zawierać pełne zdania w języku polskim poprawne pod względem '
            f'ortograficznym, gramatycznym i interpunkcyjnym.')

    dest_ids = re.findall(r"«([^«»]*)»", production['Description'])
    if prod_ids:
        if len(prod_ids) == 1 and len(production["LSide"]["Locations"]) == 1 and prod_ids[0] == production["LSide"]["Locations"][0].get("Id"):
            pass
        elif not dest_ids:  # re.fullmatch(r".*«.+».*", production['Description']):
            if production.get("Instructions"):  # jeśli to nie świat
                warnings.append(f"Opis produkcji powinien zawierać istotne dla fabuły id lewej strony produkcji w cudzysłowie "
                                f"francuskim, np. «Anyone», w celu indywidualizacji komunikatów dla gracza.")
    # TODO sprawdzić, czy działa w obie strony
    # dest_ids = re.findall(r"«([^«»]*)»", production['Description'])
    if dest_ids:
        for di in dest_ids:
            if not prod_ids or di not in prod_ids:
                errors.append(
                    f'Tekst „{di}” nie odpowiada żadnemu id z lewej strony produkcji, a tylko one powinny się znaleźć '
                    f'w cudzysłowie francuskim («…») w celu podmiany w komunikacie dla gracza na nazwę.')

    return errors, warnings


def identifiers_ls_validation(production: dict, nodes_list: List[dict], allowed_names: dict) -> Tuple[List[str], List[str]]:
    """
    Validates if the node names are from allowed set or of allowed structure (for narration nodes), ids are disjoint from the names and ids are used follows names.
    :param production:
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    for n in nodes_list:

        # sprawdzanie nazw
        if 'Name' in n['node']:
            # pytajnik jest nazwą w produkcji wzorcowej
            if n['node']['Name'] == "?":
                warnings.append(f'Produkcja zawierająca „?” jako nazwę jest produkcją wzorcową, nie do stosowania.')
            # nazwy w warstwie narracyjnej nie podlegają reglamentacji
            elif n['layer'] == "Narration":
                # ale nie mogą pokrywać się z nazwami innych warstw
                if n['node']['Name'] in allowed_names['Locations'] + allowed_names['Characters'] + allowed_names['Items']:
                    errors.append(f"Nazwa „{n['node']['Name']}” z warstwy „Narration” pokrywa się z nazwą ze zbioru "
                                  f"dozwolonych nazw innych warstw, a musi się różnić.")
                # i muszą mieć odpowiednią strukturę
                if not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", n['node']['Name']):
                    errors.append(f"Nazwa „{n['node']['Name']}” nie spełnia wymagań: \n* pierwsza duża litera, "
                                  f"\n* tylko znaki alfabetu łacińskiego, podkreślenia i cyfry.")
            # nazwy w pozostałych warstwach muszą być z odpowiedniej listy
            elif n['node']['Name'] not in allowed_names[n['layer']]:
                errors.append(f"Nazwa „{n['node']['Name']}” nie należy do zbioru dozwolonych nazw warstwy „{n['layer']}”.")

        # sprawdzanie id
        if 'Id' in n['node']:
            if n['node']['Id'] in allowed_names['Locations'] + allowed_names['Characters'] + allowed_names['Items']:
                errors.append(f"Id „{n['node']['Id']}” pokrywa się z nazwą ze zbioru dozwolonych nazw, a musi się różnić.")

            if not production.get("Instructions"):  # jeśli nie ma instrukcji, jest to świat, w którym pozwalamy na cyfrowe id
                if not re.fullmatch(r"[A-Z0-9][A-Za-z0-9_]*", n['node']['Id']):
                    errors.append(f"Id „{n['node']['Id']}” nie spełnia wymagań: \n* pierwsza duża litera lub cyfra, "
                              f"\n* tylko znaki alfabetu łacińskiego, podkreślenia i cyfry.")
            elif not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", n['node']['Id']):
                errors.append(f"Id „{n['node']['Id']}” nie spełnia wymagań: \n* pierwsza duża litera, "
                              f"\n* tylko znaki alfabetu łacińskiego, podkreślenia i cyfry.")

            # sprawdzanie, czy id są wykorzystywane
            if production.get("Instructions"): # jeśli są instrukcje, to nie jest to świat, w którym z definicji nie interesują nas id
                if 'Name' in n['node']:
                    need_for_id = False
                    if "Instructions" in production:
                        for instr in production["Instructions"]:
                            if n['node']['Id'] in [instr.get('Nodes', '').split('/')[0],
                                                   instr.get('To', '').split('/')[0],
                                                   instr.get('In', '').split('/')[0],
                                                   instr.get('Attribute', '').split('.')[0]]:
                                need_for_id = True
                    if "Preconditions" in production:
                        for prec in production["Preconditions"]:
                            if "Cond" in prec:
                                potential_ids = re.findall(r"[A-Z][A-Za-z0-9_]*", prec["Cond"])
                                if n['node']['Id'] in potential_ids:
                                    need_for_id = True
                            if "Count" in prec:
                                if n['node']['Id'] == prec["Count"].split('/')[0]:
                                    need_for_id = True
                    if "Connections" in production:
                        for dest in production["Connections"]:
                            if n['node']['Id'] == dest['Destination']:
                                need_for_id = True
                    if not need_for_id:
                        warnings.append(f"Id „{n['node']['Id']}” występuje w węźle równolegle z nazwą "
                            f"„{n['node']['Name']}”, a nie jest wykorzystywane w instrukcjach ani predykatach"
                            f"{' ani połączeniach lokacji' if n['layer'] == 'Locations' else ''}. "
                            f"Jaki był cel wprowadzenia id?")

    return errors, warnings


def ls_structure_validation(production: dict, production_type = None) -> Tuple[List[str], List[str]]:
    """
    Checks the structure of the production LHS, constraints not checked in schema
    :param production: given production
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    world = production["LSide"].get("Locations")
    if not world:
        errors.append(f"Każda produkcja musi być osadzona w lokacji.")

    if production.get("Instructions"): # czyli nie świat
        if production_type != "automatic":
            if "Characters" not in world[0]:
                errors.append(f"W produkcji w pierwszej lokacji musi być przynajmniej jedna postać – wykonawca akcji, która "
                              f"zostanie wskazana jako inicjator akcji (parametr „IsObject”).")
            else:
                object_indicated = 0
                managing_characters = world[0]["Characters"]
                for char in managing_characters:
                    if char.get("IsObject"):
                        object_indicated += 1
                if object_indicated == 0:
                    errors.append(f"W produkcji w pierwszej lokacji przynajmniej jedna postać musi być wskazana jako "
                                  f"podmiot produkcji (parametr „IsObject”).")
                elif object_indicated >1:
                    warnings.append(f"W produkcji więcej niż jedna postać jest wskazana jako podmiot działania.")

    elif production.get("Preconditions"):
        errors.append(f"W produkcji znajduje się lista niepustych predykatów stosowalności, ale nie ma instrukcji, do "
                      f"których ograniczenia miałyby służyć.")

    return errors, warnings


def nodes_structure_validation(nodes_list: List[dict]) -> Tuple[list, list]:
    """
    Validates the structure of the graph nodes
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    for n in nodes_list:
        if n["layer"] != "Locations" and "Connections" in n["node"]:
            errors.append(f'Klucz „Connections” dozwolony jest tylko dla lokacji, a nie dla węzła '
                          f'„{n["node"].get("Id", n["node"].get("Name"))}” z warstwy „{n["layer"]}”.')
        if n["layer"] != "Characters" and "IsObject" in n["node"]:
            errors.append(f'Klucz „IsObject” dozwolony jest tylko dla postaci, a nie dla węzła '
                          f'„{n["node"].get("Id", n["node"].get("Name"))}” z warstwy „{n["layer"]}”.')

    return errors, warnings


def destinations_validation(production: dict) -> Tuple[List[str], List[str]]:
    """
    Validates if identifiers of destinations match unambiguously any id or name in the list of locations.
    :param production: graph production
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    locations = production["LSide"]["Locations"]

    for location in locations:
        if "Connections" in location:
            for dest in location['Connections']:
                destination_nodes = breadcrumb_pointer(locations, name_or_id=dest['Destination'])
                if len(destination_nodes) > 1:
                    dest_text = ''
                    for dest_path in destination_nodes:
                        dest_text += f", {dest_path[-1].get('Name') or ''}"
                    errors.append(f"Dopasowanie nie jest jednoznaczne{dest_text} mają to samo id.")
                elif len(destination_nodes) == 0:
                    errors.append(f"Nie znaleziono dopasowania „{dest['Destination']}” wśród węzłów innych lokacji.")
                elif destination_nodes[0][-1] is location:
                    errors.append(f"Identyfikator połączenia „{dest['Destination']}” w węźle "
                                  f"{location.get('Id', location.get('Name'))} wskazuje sam na siebie.")

    return errors, warnings


def attributes_names_validation(production: dict, nodes_list: List[dict]) -> Tuple[List[str], List[str]]:
    """
    Validates the attributes in the production LHS
    :param production: given production
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    attr_set = attributes_from_nodes_list(nodes_list)

    # sprawdzamy poprawność struktury nazwy
    for attr_name in attr_set:
        attr_err, attr_wrn = check_attribute_name(attr_name)
        errors.extend(attr_err)
        warnings.extend(attr_wrn)

    # sprawdzamy wykorzystanie atrybutów o wartości null
    for n in nodes_list:
        if "Attributes" in n["node"]:
            for a, v in n["node"]["Attributes"].items():
                if v is None:
                    if not production.get("Instructions"): # czyli świat
                        errors.append(f'W definicji świata nie mogą występować atrybuty nieokreślone (o wartości null).')
                    else:
                        attribute_needed = False
                        node_used = False
                        if "Preconditions" in production:
                            for prec in production["Preconditions"]:
                                if prec.get("Cond"):
                                    potential_attr = re.findall(r"\.([A-Z][A-Za-z0-9]*)", prec.get("Cond"))
                                    if a in potential_attr:
                                        attribute_needed = True
                        if "Instructions" in production:
                            for instr in production["Instructions"]:
                                if instr.get("Op",'') in ["set", "unset", "mul", "add"]:
                                    if len(instr.get("Attribute", "").split(".")) > 1:
                                        if instr.get("Attribute", "").split(".")[1] == a:
                                            attribute_needed = True
                                if instr.get("Expr",''):
                                    potential_attr = re.findall(r"\.([A-Z][A-Za-z0-9]*)", instr.get("Expr"))
                                    if a in potential_attr:
                                        attribute_needed = True
                                if not attribute_needed:
                                    if n["node"].get("Id", n["node"].get("Name")) == instr.get("Nodes"):
                                        node_used = True
                                    if n["node"].get("Id", n["node"].get("Name")) == instr.get("To","").split("/")[0]:
                                        node_used = True
                                    if n["node"].get("Id", n["node"].get("Name")) == instr.get("In","").split("/")[0]:
                                        node_used = True
                        if not attribute_needed:
                            w_comm = f' (Być może atrybut ma uzasadnić działanie na całym węźle „{n["node"].get("Id", n["node"].get("Name"))}”.)' if node_used else ''
                            warnings.append(f'Atrybut „{a}” węzła „{n["node"].get("Id", n["node"].get("Name"))}” '
                                f'z wartością nieokreśloną występuje w lewej stronie produkcji, '
                                f'ale nie jest wykorzystany w predykatach ani w instrukcjach. Czy to celowe?{w_comm}')


    return errors, warnings


def sheaf_dict_validation(dict_to_check: dict, allowed_names: dict) -> Tuple[List[str], List[str], List[dict]]:
    """
    Checks if DICT structure is valid half_sheaf without ids
    :param dict_to_check: given dict
    :param dict_schema_path: schema for validating parameter „sheaf” in instructions
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :return: list of errors, list of warnings, list of half-sheaf layer-nodes (dict: "layer", "node")
    """
    errors = []
    warnings = []
    sheaf_nodes_list = []
    root_layer = ''

    # walidacja zgodności ze schemą
    # dict_schema = json.load(open(dict_schema_path, encoding="utf8"))
    dict_schema = schema_sheaf
    for err in validate_schema(dict_schema, dict_to_check, skip_names=True):
        errors.append(f'Błąd walidacji schematu JSON snopka: \n{err}')

    if not errors:
        # ustalanie warstwy korzenia
        for layer_name in allowed_names:
            if dict_to_check.get("Name") in allowed_names[layer_name]:
                root_layer = layer_name
        if not root_layer:
            root_layer = "Narration"

        # tworzenie listy węzłów z informacjami o warstwie
        sheaf_nodes_list = nodes_list_from_tree(dict_to_check, root_layer)

        for n in sheaf_nodes_list:
            # sprawdzanie nazw
            if 'Name' in n['node'] and n['node']['Name'] == "?":
                warnings.append(f"Produkcja zawierająca węzeł o nazwie „?” jest produkcją wzorcową, nie do stosowania.")
            elif 'Name' in n['node'] and n['layer'] == "Narration":  # nazwy w warstwie narracyjnej nie podlegają reglamentacji
                if n['node']['Name'] in allowed_names['Locations'] + allowed_names['Characters'] + allowed_names[
                    'Items']:
                    errors.append(f"Nazwa „{n['node']['Name']}” z warstwy „Narration” pokrywa się z nazwą ze zbioru "
                                  f"dozwolonych nazw innych warstw, a musi się różnić.")
                elif not re.fullmatch(r"[A-Z][A-Za-z0-9_]*", n['node']['Name']):
                    errors.append(f"Nazwa „{n['node']['Name']}” nie spełnia wymagań: \n* pierwsza duża litera, "
                                  f"\n* tylko znaki alfabetu łacińskiego, podkreślenia i cyfry.")
            else:
                if n['node']['Name'] not in allowed_names[n['layer']]:
                    errors.append(
                        f"Nazwa „{n['node']['Name']}” nie należy do zbioru dozwolonych nazw warstwy „{n['layer']}”.")

        # sprawdzanie atrybutów
        attr_set = attributes_from_nodes_list(sheaf_nodes_list)
        for attr_name in attr_set:
            attr_err, attr_wrn = check_attribute_name(attr_name)
            errors.extend(attr_err)
            warnings.extend(attr_wrn)


    return errors, warnings, sheaf_nodes_list


def expression_validation(expr: str, prod_ids: List[str], prod_names_c: dict, tree: Union[dict, list] = None,
                          nodes_list: List[dict] = None, bool_expr: bool = False) -> Tuple[List[str], List[str]]:
    """
    Estimates if the given expression is valid and can be calculated
    :param expr: given expression
    :param prod_ids: list of the node ids used in the production LHS
    :param prod_names_c: dict of the nodes names used in LHS with counter as value
    :param tree: graph
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param bool_expr: identifier if expression gives boolean value or other
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    # prod_ids = prod_ids if prod_ids else []
    # prod_names_c = prod_names_c if prod_names_c else {}

    # warnings.append(f'EXPR {expr} do sprawdzenia')
    potential_identifiers = re.findall(r"[A-Z][A-Za-z0-9_]*\.[A-Z][A-Za-z0-9]*", expr)
    if potential_identifiers:
        for node_attr in potential_identifiers:
            node, attr = node_attr.split(".")
            if node not in prod_ids and node not in prod_names_c:
                warnings.append(f'EXPR: „{node}” sprawia wrażenie identyfikatora węzła w wyrażeniu: „{expr}”, ale nie '
                                f'pasuje do żadnego węzła z lewej strony.')
            elif node in prod_names_c and prod_names_c[node] > 1:
                warnings.append(f'EXPR: Jeśli „{node}” jest nazwą w warunku: „{expr}”, to może być niejednoznaczny '
                                f'w prawej stronie.')
            else:
                err, wrn, result = check_node_ref_attr_name([node, attr], tree=tree, nodes_list=nodes_list, attr_exist=True)
                # błędy ignorujemy, bo to sprawdzanie hipotetyczne
                for w in wrn:
                    warnings.append(f'EXPR: {w} Warunek: „{expr}”.')

                # TODO przykład hp i hP się waliduje, choć nie powinien, a HP tylko wtedy, gdy jest w warunkach dopasowania


                # attr_exist = False
                # if tree:
                #     first_segment_paths = breadcrumb_pointer(tree, name_or_id=node)

                #     if len(first_segment_paths) != 1:
                #
                #     if len(first_segment_paths) == 0:
                #         warnings.append(
                #             f"Nazwa „{identifier_to_check}” nie jest identyfikatorem żadnego węzła w lewej stronie produkcji.")
                #     elif len(first_segment_paths) > 1:
                #         errors.append(
                #             f"Nazwa „{identifier_to_check}” nie jest jednoznacznym identyfikatorem w lewej stronie produkcji.")
                #     else:
                #         if len(first_segment_paths) == 1:
                #             layer = "Locations"
                #         else:
                #             layer = find_node_layer_name(first_segment_paths[0][-2], first_segment_paths[0][-1])
                #         result_node = {"layer": layer, "node": first_segment_paths[0][-1]}
                #
                # elif nodes_list:
                #     for n in nodes_list:
                #         if n["node"].get("Id", n["node"].get("Name")) == node and "Attributes" in n["node"] \
                #                 and attr in n["node"]["Attributes"]:
                #             attr_exist = True
                #     if not attr_exist:
                #         warnings.append(f'EXPR: Węzeł „{node}” nie posiada atrybutu „{attr}” w warunkach dopasowania, '
                #                         f'co może uniemożliwić walidację warunku: „{expr}”.')

    if bool_expr:
        comparison = re.split(r' (==|>=|<=|>|<|!=) ', expr)
        if len(comparison) != 3:
            warnings.append(f'EXPR: Warunek „{expr}” nie pasuje do wzorca prostego porównania. Trzeba go sprawdzić ręcznie.')

    return errors, warnings


def preconditions_validation_errors(production: dict, nodes_list: List[dict], prod_ids: List[str], prod_names_c: dict,
                                    allowed_names: dict = None) -> Tuple[List[str], List[str]]:
    """
    Validates all the preconditions in production
    :param production: given production
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param prod_ids: list of the node ids used in the production LHS
    :param prod_names_c:
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    if "Preconditions" in production:
        for prec in production["Preconditions"]:

            if 'Cond' not in prec and 'Count' not in prec:
                errors.append(f'Podany jako warunek stosowalności słownik {prec} nie zawiera warunku '
                              f'(parametru „Cond” lub „Count”).')

            elif 'Cond' in prec:
                # TODO czy schema sprawdza, że cond jest stringiem?
                be_err, be_wrn =  expression_validation(prec['Cond'], prod_ids, prod_names_c, nodes_list=nodes_list, bool_expr=True)
                errors.extend(be_err)
                warnings.extend(be_wrn)

            elif 'Count' in prec:
                # sprawdzamy poprawność MULTI-REF
                prec['Count'] = re.sub(r'/\*\*/', '/', prec['Count'])  # możemy po prostu wyciąć wszystkie ** ponieważ jeśli multireferencja jest poprawna, to bez gwiazdek też będzie poprawna
                multireference_split = prec['Count'].split('/')
                id_err, id_wrn, id_result = check_identifier(multireference_split[0], nodes_list=nodes_list)
                warnings.extend(id_wrn)
                errors.extend(id_err)

                if len(multireference_split) > 1:
                    mwp_err, mwp_wrn = check_multifererence_world_part(multireference_split[1:], allowed_names, prod_ids)
                    errors.extend(mwp_err)
                    warnings.extend(mwp_wrn)

                    if multireference_split[-1] in prod_names_c:  # "*" not in prec['Count'] wcześniejszy warunek
                        if prec.get("Min") is not None:
                            war_min_max = f" w warunku >= {prec['Min']}"
                        elif prec.get("Max") is not None:
                            war_min_max = f" w warunku <= {prec['Max']}"
                        else:
                            war_min_max = ''
                        warnings.append(
                            f'Multireferencja „{prec["Count"]}”{war_min_max} może wskazywać na nazwę, która jest także dopasowana w lewej '
                            f'stronie ({paths_convert_to_text(breadcrumb_pointer(production["LSide"], name_or_id=multireference_split[-1]))}). '
                            f'Proszę porównać początki multireferencji. Jeśli są identyczne, to liczenie obiektów może '
                            f'mieć sens, ale w nielicznych przypadkach.')
                else:
                    warnings.append(
                        f'Referencja „{prec["Count"]}” wskazuje konkretny obiekt dopasowany w lewej stronie. Jego '
                        f'krotność jest zawsze równa 1.')

                # sprawdzamy ograniczenia
                if 'Min' not in prec and 'Max' not in prec:
                    warnings.append(f'Warunek „Count” dla multireferencji „{prec["Count"]}” nie podaje ani minimum ani '
                                    f'maksimum. Raczej podejrzane.')
                for par in ["Min", "Max"]:
                    if par in prec:
                        if type(prec.get(par)) != int or prec.get(par) < 0:
                            errors.append(f'Parametr „{par}” musi być liczbą całkowitą nieujemną, a nie: {prec.get(par)}.')

    return errors, warnings


def instruction_validation(instruction: dict, prod_ids: List[str], prod_names_c: dict, tree: Union[dict, list] = None,
                            nodes_list: List[dict] = None, allowed_names: dict = None,
                            name_as_id_warning: bool = None) -> Tuple[List[str], List[str], dict]:
    """
    Validates the production instruction.
    :param instruction: given instruction
    :param dict_schema_path: schema for validating parameter „sheaf” in instructions
    :param prod_ids: list of the node ids used in the production LHS
    :param prod_names_c: dict of the nodes names used in LHS with counter as value
    :param tree: The graph tree on which the instruction will be applied
    :param nodes_list: list of layer-described nodes (dict: "layer", "node"). If not given, is generated inside from tree
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :param name_as_id_warning: rather unnecessary constraint
    :return: list of errors, list of warnings, dict of application simulation data
    """
    err = []
    wrn = []
    apply = {}
    nodes_list = nodes_list or nodes_list_from_tree(tree, 'root')

    if 'Op' not in instruction:
        err.append(f'Podany jako instrukcja słownik nie zawiera instrukcji: {instruction}.')
        return err, wrn, apply
    if instruction['Op'] not in ('add', 'mul', 'create', 'copy', 'delete', 'move', 'set', 'unset', 'winning'):
        err.append(f'Niedozwolona nazwa instrukcji: „{instruction["Op"]}”.')
        return err, wrn, apply

    for k, v in instruction.items():
        if (k, v) == ('Op', 'move'):
            if 'Nodes' not in instruction:
                err.append(f'Instrukcja „move” wymaga parametru „Nodes”.')
            if 'To' not in instruction:
                err.append(f'Instrukcja „move” wymaga parametru „To”.')
        elif (k, v) == ('Op', 'copy'):
            if 'Nodes' not in instruction:
                err.append(f'Instrukcja „copy” wymaga parametru „Nodes”.')
            if 'To' not in instruction:
                err.append(f'Instrukcja „copy” wymaga parametru „To”.')
        elif (k, v) == ('Op', 'delete'):
            if 'Nodes' not in instruction:
                err.append(f'Instrukcja „delete” wymaga parametru „Nodes”.')
        elif (k, v) == ('Op', 'create'):
            if 'Sheaf' not in instruction:
                err.append(f'Instrukcja „create” wymaga parametru „Sheaf”.')
            if 'In' not in instruction:
                err.append(f'Instrukcja „create” wymaga parametru „In”.')
        elif (k, v) == ('Op', 'set'):
            if 'Attribute' not in instruction:
                err.append(f'Instrukcja „set” wymaga parametru „Attribute”.')
            if ('Value' not in instruction) and ('Expr' not in instruction):
                err.append(f'Instrukcje „set” wymaga parametru „Value” lub „Expr”.')
        elif (k, v) == ('Op', 'add') or (k, v) == ('Op', 'mul'):
            if 'Attribute' not in instruction:
                err.append(f'Instrukcje „set”, „add” i „mul” wymagają parametru „Attribute”.')
            if 'Value' not in instruction:
                err.append(f'Instrukcje „add” i „mul” wymagają parametru „Value”.')
        elif (k, v) == ('Op', 'unset'):
            if 'Attribute' not in instruction:
                err.append(f'Instrukcje „unset” wymaga parametru „Attribute”.')
        elif (k, v) == ('Op', 'winning'):
            pass

        elif k == 'Nodes':
            if instruction['Op'] not in {'move', 'copy', 'delete'}:
                err.append(f'Parametr „Nodes” ma sens dla operacji: „move”, „copy”, „delete”, a nie: '
                           f'„{instruction["Op"]}”.')

            # sprawdzamy poprawność MULTI-REF
            v = re.sub(r'/\*\*/','/',v)  # możemy po prostu wyciąć wszystkie ** ponieważ jeśli multireferencja jest poprawna, to bez gwiazdek też będzie poprawna
            multireference_split = v.split('/')
            # sprawdzamy pierwszy segment multireferencji
            id_err, id_wrn, id_result = check_identifier(multireference_split[0], nodes_list=nodes_list, name_as_id_warning=name_as_id_warning)
            wrn.extend(id_wrn)
            err.extend(id_err)
            # sprawdzamy część światową multireferencji
            if len(multireference_split) > 1:
                mwp_err, mwp_wrn = check_multifererence_world_part(multireference_split[1:], allowed_names, prod_ids)
                err.extend(mwp_err)
                wrn.extend(mwp_wrn)

                if multireference_split[-1] in prod_names_c:  # "*" not in prec['Count'] wcześniejszy warunek
                    wrn.append(
                        f'Multireferencja „{v}” może wskazywać na nazwę, która jest także dopasowana w lewej '
                        f'stronie. Jeśli chodzi o ten dopasowany obiekt, to trzeba użyć bezpośrednio jego nazwy, '
                        f'bo multireferencja znajdzie dowolny obiekt o tej nazwie na końcu ścieżki, niekoniecznie '
                        f'ten dopasowany (np. pozostały z kilku przedmiotów).')

            # do symulacji wykonania
            if len(multireference_split) == 1 and not id_err:
                apply["Nodes"] = deepcopy(id_result)
            elif len(multireference_split) > 1 and not mwp_err:
                apply["Nodes"] = {"layer": deepcopy(multireference_split[-2]), "node": "world nodes"}

        elif k == 'To':
            if instruction['Op'] not in {'move', 'copy'}:
                err.append(f'Parametr „To” ma sens dla operacji: „move” i „copy”, a nie: „{instruction["Op"]}”.')

            # sprawdzamy poprawność ARRAY-REF
            arr_err, arr_wrn = check_array_ref(v, nodes_list=nodes_list, param=k, name_as_id_warning=name_as_id_warning)
            err.extend(arr_err)
            wrn.extend(arr_wrn)

            # do symulacji wykonania
            if not arr_err:
                apply["To_layer"] = v.split("/")[-1]

        elif k == 'In':
            if instruction['Op'] not in {'create'}:
                err.append(f'Parametr „In” ma sens dla operacji: „create”, a nie: „{instruction["Op"]}”.')

            # sprawdzamy poprawność ARRAY-REF
            arr_err, arr_wrn = check_array_ref(v, nodes_list=nodes_list, param=k, name_as_id_warning=name_as_id_warning)
            wrn.extend(arr_wrn)
            err.extend(arr_err)

            # do symulacji wykonania
            if not arr_err:
                apply["In_layer"] = v.split("/")[-1]

        elif k == 'Sheaf':
            if instruction['Op'] not in {'create'}:
                err.append(f'Parametr „Sheaf” ma sens dla operacji: „create”, a nie: „{instruction["Op"]}”.')

            # sprawdzamy poprawność DICT
            dict_err, dict_wrn, dict_node_list = sheaf_dict_validation(v, allowed_names)
            err.extend(dict_err)
            wrn.extend(dict_wrn)

            # do symulacji wykonania
            if not dict_err:
                apply["Sheaf"] = deepcopy(dict_node_list)

        elif k == 'Attribute':
            if instruction['Op'] not in {'set', 'add', 'mul', 'unset'}:
                err.append(f'Parametr „Attribute” ma sens dla operacji: „set”,  „add”, „mul” i „unset”, a nie: '
                    f'„{instruction["Op"]}”.')

            #sprawdzanie, czy NODE-REF.ATTR-NAME jest poprawny i czy atrybut istnieje (dla unset)
            attr_exist = True if instruction['Op'] in ['unset'] else False
            nar_err, nar_wrn, result = check_node_ref_attr_name(v, nodes_list=nodes_list, attr_exist=attr_exist, name_as_id_warning=name_as_id_warning)
            err.extend(nar_err)
            wrn.extend(nar_wrn)

            # do symulacji wykonania
            if result:
                apply["Attr_node"], apply["Attr_name"] = deepcopy(result)

        elif (k == 'ChildrenLimiter') or (k == 'CharactersLimiter') or (k == 'ItemsLimiter') or (k == 'NarrationLimiter'):
            if instruction['Op'] not in {'delete'}:
                err.append(f'Parametr „{k}” ma sens dla operacji „delete”.')
            if v not in ['delete', 'prohibit', 'move']:
                err.append(f'Parametr „{k}” może przyjmować wartości: „delete”, „prohibit”, „move”, a nie: „{v}”.')

        elif k == 'Value':
            if instruction['Op'] not in {'set', 'add', 'mul'}:
                err.append(f'Parametr „Value” ma sens dla operacji „set”, „add” i „mul”, a nie: „{v}”.')
            if instruction['Op'] in {'add', 'mul'} and type(v) not in [int, float]:
                err.append(f'Parametr „Value” dla operacji „add” i „mul” musi być liczbą, a nie: „{v}”.')

        elif k == 'Expr':
            if instruction['Op'] not in {'set'}:
                err.append(f'Parametr „Expr” ma sens dla operacji „set”, a nie: „{v}”.')

            # szacowanie poprawności wyrażenia
            be_err, be_wrn =  expression_validation(v, prod_ids, prod_names_c, nodes_list=nodes_list)
            err.extend(be_err)
            wrn.extend(be_wrn)

        elif k == 'Limit':
            if instruction['Op'] not in {'move', 'delete'}:
                err.append(f'Parametr „Limit” ma sens dla operacji „move” i „delete”, a nie: „{v}”.')
            if type(v) not in [int] or v < 1:
                err.append(f'Parametr „Limit” musi być liczbą całkowitą dodatnią, a nie: „{v}”.')
        elif k == "Count":
            if instruction['Op'] not in {'create', 'copy'}:
                err.append(f'Parametr „Count” ma sens dla operacji „create” i „copy”, a nie: „{v}”.')
            if type(v) not in [int] or v < 0:
                err.append(f'Parametr „Count” musi być liczbą całkowitą nieujemną, a nie: „{v}”.')
            # else:
            #     apply["Count"] = v

        elif k == 'Comment':
            pass

        else:
            err.append(f'Parametr „{k}” z wartością „{v}” nie został rozpoznany dla operacji: „{instruction["Op"]}”.')

    return err, wrn, apply


def get_instructions_validation_errors(production: dict, nodes_list: List[dict], allowed_names: dict,
                                       prod_ids: List[str], prod_names_c: dict) -> Tuple[List[str], List[str]]:
    """
    Validates all the instructions in production
    :param production: given production
    :param nodes_list: list of layer-described nodes (dict: "layer", "node")
    :param dict_schema_path: schema for validating parameter „sheaf” in instructions
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :param prod_ids: list of the node ids used in the production LHS
    :param prod_names_c: dict of the nodes names used in LHS with counter as value
    :return: list of errors, list of warnings
    """
    errors = []
    warnings = []
    name_as_id_warning = False

    if "Instructions" in production:
        for instr in production["Instructions"]:
            credibility_loss = False
            err, wrn, app = instruction_validation(instr, prod_ids, prod_names_c, nodes_list=nodes_list, allowed_names=allowed_names, name_as_id_warning=name_as_id_warning)
            errors.extend(err)
            warnings.extend(wrn)

            # sprawdzanie warunków spójności warstw
            if instr['Op'] == 'move':
                if "Nodes" in app and "To_layer" in app:
                    if app["Nodes"]["layer"] != app["To_layer"]:
                        errors.append(f'Nie wolno przenosić węzła z warstwy „{app["Nodes"]["layer"]}” '
                                      f'do warstwy „{app["To_layer"]}”.')

            elif instr['Op'] == 'create':
                if "Sheaf" in app and "In_layer" in app:
                    if app["In_layer"] != "Narration" and app["Sheaf"][0]["node"].get("Name",'') != "?" \
                            and app["Sheaf"][0]["node"].get("Name",'') not in allowed_names[app["In_layer"]]:
                        errors.append(f'Nie wolno tworzyć w warstwie „{app["In_layer"]}” węzła '
                                      f'„{app["Sheaf"][0]["node"].get("Name")}”, to nazwa dozwolona w innej warstwie.')

                    else:
                        # Zakładam, że jednak tworzone węzły nie dołączają do lewej strony, spytać Wojtka
                        pass
                        # app_count = app.get("Count") if app.get("Count") else 1
                        # for nr in range(app_count):
                        #     app_sheaf = {"layer": app["In_layer"], "node": deepcopy(app["Sheaf"])}
                        #     nodes_list.append(app_sheaf)

            elif instr['Op'] == 'copy':
                if "Nodes" in app and "To_layer" in app:
                    if app["Nodes"]["layer"] != app["To_layer"]:
                        errors.append(f'Nie wolno kopiować do warstwy „{app["To_layer"]}” węzła z warstwy '
                                      f'„{app["Nodes"]["layer"]}”.')
                    else:
                        # Zakładam, że jednak tworzone węzły nie dołączają do lewej strony, spytać Wojtka
                        pass
                        # app_count = app.get("Count") if app.get("Count") else 1

            # symulacja wykonania instrukcji krytycznych dla sprawdzania następnych
            elif instr['Op'] == 'delete':
                if "Nodes" in app and app["Nodes"]["node"] != "world nodes":
                    try:
                        nodes_list.remove(app["Nodes"])
                        # print(f'    Usunięto węzeł „{app["Nodes"]["node"].get("Id", app["Nodes"]["node"].get("Name"))}”.')

                        if app["Nodes"]["node"].get("Id"):
                            try:
                                prod_ids.remove(app["Nodes"]["node"]["Id"])
                                # print(f'    Usunięto id „{app["Nodes"]["node"].get("Id")}” z listy id.')
                            except:
                                warnings.append(f'W procesie walidacji nie udało się usunąć id '
                                    f'„{app["Nodes"]["node"]["Id"]}” z listy dostępnych id po usunięciu '
                                    f'węzła. Dalsza walidacja może być niewiarygodna.')
                        if app["Nodes"]["node"].get("Name"):
                            prod_names_c[app["Nodes"]["node"]["Name"]] -= 1
                            # print(f'    Zmniejszono krotność nazwy „{app["Nodes"]["node"].get("Name")}” w liczniku.')

                    except:
                        warnings.append(f'W procesie walidacji nie udało się zasymulować usunięcia węzła '
                            f'„{app["Nodes"]["node"].get("Id", app["Nodes"]["node"].get("Name"))}”. '
                            f'Dalsza walidacja może być niewiarygodna.')
                        credibility_loss = True

            elif instr['Op'] == 'unset':
                if 'Attr_node' in app and "Attr_name" in app:
                    try:
                        del(app['Attr_node']["node"]["Attributes"][app['Attr_name']])
                    except:
                        warnings.append(f"Przypuszczalnie nie uda się usunąć atrybutu „{app['Attr_name']}” z węzła "
                                        f"„{app['Attr_node']['node'].get('Id', app['Attr_node']['node'].get('Name'))}”.")

            if credibility_loss:
                warnings.append(f"Dalsza walidacja może być niewiarygodna z powodu błędów instrukcji krytycznych dla sprawdzania "
                                f"poprawności następnych.")

    return errors, warnings


def validate_schema(schema, instance: Union[dict, list], skip_names: bool = False) -> iter:
    """
    Validates JSON instance with the schema.
    :param skip_names: Show if the part of the schema could be ignored
    :param schema: JSON schema
    :param instance: given mission as JSON list
    :return: Iterable of errors
    """
    # TODO jakiego typu jest schema?
    if skip_names:
        schema['definitions']['node']['properties']['Name'].pop('enum', None)

    v = Draft7Validator(schema)
    return v.iter_errors(instance)


def get_quest_validated(production_list: List[dict], allowed_names: dict = None,
                        productions_titles_dict: dict = None, production_type = None) -> Tuple[List[dict], dict, dict]:
    """
    Gets the list of productions validated with system rules from one JSON and errors and warnings from other.
    :param production_list: list of productions taken from one JSON file
    :param dict_schema_path: schema for validating parameter „sheaf” in instructions
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :param productions_titles_dict:
    :return: list of valid productions, dict of production names as keys and list of errors as values
    """

    prods_sg_validated = []
    all_errors = {}
    all_warnings = {}
    if not allowed_names:
        allowed_names = get_allowed_names()

    for production in production_list:
        errors = []
        warnings = []
        prod_nodes = nodes_list_from_tree(production["LSide"])
        id_err, prod_ids = get_prod_ids(prod_nodes)
        prod_names_c = get_prods_names_count(prod_nodes)
        errors.extend(id_err)
        # ls = production["LSide"]
        # print(f'### {production["Title"]}')

        # print("Sprawdzanie poprawności opisu produkcji...", end='')
        err, wrn = production_metainfo_validation(production, productions_titles_dict, prod_ids)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności identyfikatorów lewej strony...", end='')
        err, wrn = identifiers_ls_validation(production, prod_nodes, allowed_names)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności struktury lewej strony...", end='')
        err, wrn = ls_structure_validation(production, production_type)
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności struktury węzłów...", end='')
        err, wrn = nodes_structure_validation(prod_nodes)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności destynacji...", end='')
        err, wrn = destinations_validation(production)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności nazw atrybutów...", end='')
        err, wrn = attributes_names_validation(production, prod_nodes)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        if production['RSide']:
            errors.extend([f'Prawa strona produkcji powinna pozostać pusta.'])

        # print("Sprawdzanie poprawności predykatów stosowalności...", end='')
        err, wrn = preconditions_validation_errors(production, prod_nodes, prod_ids, prod_names_c, allowed_names)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        # print("Sprawdzanie poprawności instrukcji...", end='')
        err, wrn = get_instructions_validation_errors(production, prod_nodes, allowed_names, prod_ids, prod_names_c)
        # print(" OK") if not err and not wrn else print("Err")
        errors.extend(err)
        warnings.extend(wrn)

        if not errors:
            prods_sg_validated.append(production)
        if errors:
            all_errors[production["Title"]] = errors
        if warnings:
            all_warnings[production["Title"]] = warnings

    return prods_sg_validated, all_errors, all_warnings


def get_jsons_opened(json_path: str, mask: str = '*.json') -> Tuple[List[dict], dict]:
    """
    Gets the list of valid JSONs from opened files.
    :param json_path: filepath to root folder of folders with JSON files
    :param mask: structure of filenames included to analysis
    :return: list of JSONs, dict of errors (key filepath, value: {"file": list of errors})
    """
    json_files = get_json_files_paths(json_path, mask=mask)
    jsons_opened = []
    errors = {}

    for json_file in json_files:

        if 'Stare wersje misji' in str(json_file.absolute()):
            continue

        if 'temp' in str(json_file.absolute()):
            continue

        try:
            info_json_file_path = f'{str(json_file.absolute()).replace(f"{path_root}/","")}'
            json_instance = json.loads(json_file.read_text(encoding="utf8"))
            jsons_opened.append({'file_path': info_json_file_path, 'json': json_instance})

        except JSONDecodeError as e:
            # print(f'Nie można wczytać pliku „{json_file.parent.name}/{json_file.name}”\n{e}\n')
            errors[f'{json_file.parent.name}/{json_file.name}'] = \
                {"file": [f'Nie można wczytać pliku „{json_file.parent.name}/{json_file.name}”\n{e}\n']}


    return jsons_opened, errors


def get_jsons_schema_validated(json_path: str, mask: str = '*.json') -> Tuple[List[dict], dict]:
    """
    Gets the list of JSONs validated with schema from list of valid JSONs
    :param json_path: filepath to root folder of folders with JSON files
    :param json_schema_path: filepath to file with JSON schema for production
    :param mask: structure of filenames included to analysis
    :return: list of JSONs schema-validated, dict of errors (key filepath, value: {"file": list of errors})
    """

    # otwieranie plików. Zwraca listę słowników: "file_path", "json" i listę błędów
    jsons_opened_list, opening_errors = get_jsons_opened(json_path, mask)
    if not jsons_opened_list:
        print("Nie udało się wczytać żadnego pliku.")
        exit(1)
    # else:
        # print(f'Znaleziono {len(jsons_opened_list)} plików {mask}')

    # walidowanie zgodności ze schemą. Zwraca listę słowników: "file_path", "json" i listę błędów
    # json_schema = json.load(open(json_schema_path, encoding="utf8"))
    json_schema = schema
    jsons_schema_validated = []
    all_errors = opening_errors
    for json_instance in jsons_opened_list:
        errors = []
        for err in validate_schema(json_schema, json_instance['json'], skip_names=True):
            errors.append(f'Błąd walidacji schematu JSON misji: \n{err}')

        if errors:
            errors.append(f'Dalsza walidacja pliku „{json_instance["file_path"]}” została przerwana.')
            all_errors[json_instance["file_path"]] = {}
            all_errors[json_instance["file_path"]]["file"] = errors
        else:
            jsons_schema_validated.append(json_instance)

    return jsons_schema_validated, all_errors


def print_errors_warnings(jsons_schema_validated, errors = None, warnings = None):
    errors = {} if errors is None else errors
    warnings = {} if warnings is None else warnings

    # wypisywanie błędów i ostrzeżeń
    print(f'\n\n##################################### Błędy otwierania plików i walidacji schematu JSON:')
    for file, prods in errors.items():
        for title, errs in prods.items():
            if title == "file":
                print(f'\n######## {file}')
                for nr, e in enumerate(errs):
                    if len(e) < 9000:
                        print_lines(f'{nr:03d}. {e}', 90, '', '     ')
                    else:
                        print_lines(f'{nr:03d}. {e[0:9000]}…', 90, '', '     ')

    print(f'\n\n##################################### Błędy i ostrzeżenia walidacji reguł systemu:')
    for file in jsons_schema_validated:
        if file['file_path'] in errors or file['file_path'] in warnings :
            print(f'\n########## {file["file_path"]}')

        for prod in file['json']:
            if prod["Title"] in errors.get(file['file_path'], []) or prod["Title"] in warnings.get(file['file_path'], []):
                print(f'#### {prod["Title"]}')
                if prod["Title"] in errors.get(file['file_path'], []):
                    print(f'     Błędy:')
                    for nr, e in enumerate(errors[file['file_path']][prod["Title"]]):
                        # for nr, e in errs):
                            if len(e) < 9000:
                                print_lines(f'{nr:03d}. {e}', 90, '     ', '          ')
                            else:
                                print_lines(f'{nr:03d}. {e[0:9000]}…', 90, '     ', '          ')
                if prod["Title"] in warnings.get(file['file_path'], []):
                    print(f'     Ostrzeżenia:')
                    for nr, w in enumerate(warnings[file['file_path']][prod["Title"]]):
                        # for nr, e in enumerate(wrns):
                            if len(w) < 350:
                                print_lines(f'{nr:03d}. {w}', 90, '     ', '          ')
                            else:
                                print_lines(f'{nr:03d}. {w[0:350]}…', 90, '     ', '          ')

def production_names_list_builder(jsons_schema_validated: list, production_titles_dict:dict = None, errors:list = None, warnings:list = None):

    if production_titles_dict is None:
        production_titles_dict = {}

    for json_instance in jsons_schema_validated:
        for production in json_instance['json']:
            if production['Title'] not in production_titles_dict:
                production_titles_dict[production['Title']] = {"production": production, "file_path": json_instance['file_path']}
            else:
                if production == production_titles_dict[production["Title"]]["production"]:
                    wrn_comm = f'Tytuł produkcji „{production["Title"]}” został już użyty w pliku: \n{production_titles_dict[production["Title"]]["file_path"]}.'
                    wrn_comm += "\nProdukcje te są identyczne, lepiej jednak usunąć drugą."
                    if json_instance['file_path'] not in warnings:
                        warnings[json_instance['file_path']] = {}
                    warnings[json_instance['file_path']][production["Title"]] = [wrn_comm]
                else:
                    err_comm = f'Tytuł produkcji „{production["Title"]}” został już użyty w pliku: \n{production_titles_dict[production["Title"]]["file_path"]}.'
                    err_comm += "\nProdukcje te się różną. Proszę poprawić lub usunąć drugą."
                    if json_instance['file_path'] not in errors:
                        errors[json_instance['file_path']] = {}
                    errors[json_instance['file_path']][production["Title"]] = [err_comm]
    return production_titles_dict, errors, warnings

def get_jsons_storygraph_validated(json_path: str, mask: str = '*.json', production_titles_dict:dict = None,
                                   allowed_names: dict = None) -> Tuple[List[dict], List[dict], dict, dict]:
    """
    Gets the list of JSONs validated with system rules from list of JSONs validated with schema from the list of valid JSONs files
    :param json_path: filepath to root folder of folders with JSON files
    :param json_schema_path: filepath to file with JSON schema for production
    :param dict_schema_path: filepath to file with JSON schema for sheaf dict
    :param mask: structure of filenames included to analysis
    :param production_titles_dict: dict with production title as the key and dict {"production": "file_path":} as value
    :param allowed_names: dict with three keys: "Locations", "Characters", "Items" and lists of allowed names as values
    :return: list of JSONs system-validated, list of JSONs schema-validated, dict of errors, dict of warnings (key filepath, value: {"file"/production_title: list of errors})
    """

    jsons_sg_validated = []
    warnings = {}
    jsons_schema_validated, errors = get_jsons_schema_validated(json_path, mask)
        # for file, err in errors.items():
    #     print(f'### {file}')
    #     for e in err:
    #         print(e)

    # tworzenie zbioru wszystkich zarezerwowanych nazw
    if not allowed_names:
        allowed_names = get_allowed_names()

    # tworzenie zbioru produkcji generycznych
    # na razie słownik, nie drzewo, kiedyś będzie drzewo
    if production_titles_dict is None:
        production_titles_dict = {}

    # budowanie listy nazw produkcji i sprawdzanie ich unikalności
    production_titles_dict, errors, warnings = production_names_list_builder(jsons_schema_validated, production_titles_dict, errors, warnings)

    # sprawdzanie, czy produkcje generyczne są w ścieżce oznaczonej "gener"
    for json_instance in jsons_schema_validated:
        for production in json_instance['json']:                                                # czyli nie jest światem
            if not production['TitleGeneric'] and "gener" not in json_instance['file_path'] and production.get("Instructions"):
                if json_instance['file_path'] not in warnings:
                    warnings[json_instance['file_path']] = {}
                warnings[json_instance['file_path']][production["Title"]] = [f'Produkcja „{production["Title"]}” nie jest '
                    f'w pliku z produkcjami generycznymi a nie jest pochodną żadnej produkcji generycznej. Podejrzane.']

    # walidowanie poszczególnych produkcji zgodnie z regułami systemu
    for json_instance in jsons_schema_validated:
        # print(f'### {json_instance["file_path"]}')
        if "automat" in json_instance['file_path']:
            production_type = "automatic"
        elif "gener" in json_instance['file_path']:
            production_type = "generic"
        else:
            production_type = None
        productions_sg_validated, sg_errors, sg_warnings = \
            get_quest_validated(json_instance['json'], allowed_names, production_titles_dict, production_type)


        # Dodawanie do słownika błędów klucza ścieżki pliku i wartości listy błędów
        if sg_errors:
            if json_instance['file_path'] not in errors:
                errors[json_instance["file_path"]] = {}

            for title, e in sg_errors.items():
                if e:
                    if title not in errors[json_instance['file_path']]:
                        errors[json_instance['file_path']][title] = []
                    errors[json_instance['file_path']][title].extend(e)

        # Dodawanie do słownika ostrzeżeń klucza ścieżki pliku i wartości listy błędów
        if sg_warnings:
            if json_instance['file_path'] not in warnings:
                warnings[json_instance["file_path"]] = {}

            for title, e in sg_warnings.items():
                if e:
                    if title not in warnings[json_instance['file_path']]:
                        warnings[json_instance['file_path']][title] = []
                    warnings[json_instance['file_path']][title].extend(e)

        # dodawanie poprawnego jsona do listy bezbłędnych
        if not sg_errors:
            jsons_sg_validated.append(json_instance)


    return jsons_sg_validated, jsons_schema_validated, errors, warnings




