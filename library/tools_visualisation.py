import json
import os
import textwrap
from typing import List, Union

import graphviz
from PIL import Image, ImageOps
from graphviz.graphs import BaseGraph


def merge_images(images_paths: List[str], save_dir: str, save_file: str) -> None:
    """
    Merges images in images_paths to one big file and saves to save_path.
    :param images_paths:
    :param save_path:
    :return:
    """
    images = [ImageOps.expand(Image.open(x), border=20, fill='white') for x in images_paths]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height), color='white')

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    try:
        os.makedirs(save_dir)
    except:
        pass
    new_im.save(f'{save_dir}/{save_file}')


def draw_graph(graph, t, d, file, dr, r_n=None, r_e=None, c=None, w=True, f='png', clean=False, draw_id=True):
    if type(graph) == list:
        graph = {"Locations": graph}
    gv = GraphVisualizer()
    try:
        gv.visualise(graph, title=t, description=d, world=w, emph_nodes_ids=r_n, emph_edges=r_e, comments=c, draw_id=draw_id).render(
            format=f, filename=file, directory=dr, cleanup=clean)
    except Exception:
        pass
        # print(123)
        # print(json.dumps(graph, indent=4))


def draw_narration_line(move_list: list, mission_name, directory_path):
    graph = graphviz.Digraph(engine='dot')
    graph.attr(overlap='false')
    graph.attr(splines='polyline')
    graph.attr(dpi='150')
    graph.attr(ratio='fill')
    graph.attr(labelloc='t')
    graph.attr(rankdir='TB')
    graph.attr(shape='box')

    for nr, move in enumerate(move_list):
        node_attributes = {
            'shape': 'box',
            'style': 'filled',
            'fillcolor': 'white',
            # 'color': background_colors[parent_key],
        }
        label = f"{move['ProductionTitle'].split(' / ')[0]}"  # gdybyśmy chcieli dodac nr wierzchołka: ({nr[0]}<SUB>{nr[1:]}</SUB>)
        label_match = ''
        for m in move['LSMatching']:
            label_match += f"{m['LSNodeRef']} – {m['WorldNodeName']}, "
        label += f'<BR/><FONT POINT-SIZE="10">{label_match}</FONT>'

        try:
            graph.node(f'{nr}', f"< {label} >", **node_attributes)
        except TypeError:
            print(label)

        if nr > 0:
            graph.edge(f'{nr-1}', f'{nr}')


    graph.render(format='png', filename=f'{mission_name}',
                 directory=directory_path, cleanup=True)


class GraphVisualizer:
    def __init__(self):
        self._vertex_counter = 1

    def _visualise_process(self, json_dict_or_list, parent_key: str, parent_name: str, graph: BaseGraph,
                           emph_nodes_ids: list = None, comments: dict = None, world=False, draw_id = True) -> list:
        """
        Generating the list of nodes of the graph tree given.
        :param json_dict_or_list: the current level of graph tree. Dict for layer, list for nodes.
        :param parent_key: the layer name of the current root. If not applicable, use "root"
        :return: The list of nodes with: )
        """

        if not emph_nodes_ids:
            emph_nodes_ids = []
        if not comments:
            comments = {}
        current_list = []
        if isinstance(json_dict_or_list, dict):
            current_dict = {}
            if parent_key != 'root':
                current_dict["Layer"] = parent_key

            for k, v in json_dict_or_list.items():
                if k in "LSide":
                    current_list.extend(self._visualise_process(v, 'root', 'root', graph, emph_nodes_ids, comments, world, draw_id))
                elif k in ("Id", "Name", "Attributes", "Connections", "Preconditions", "Instructions"):
                    current_dict[k] = v
                elif k in "Locations":
                    current_list.extend(self._visualise_process(v, k, 'root', graph, emph_nodes_ids, comments, world, draw_id))
                elif k in ("Characters", "Items", "Narration"):
                    current_list.extend(self._visualise_process(v, k, parent_name, graph, emph_nodes_ids, comments, world, draw_id))

        elif isinstance(json_dict_or_list, list):
            lst = json_dict_or_list
            for i in range(len(lst)):
                nr = f'v{self._vertex_counter}'
                node_name = lst[i]['Name'] if 'Name' in lst[i] else None
                node_id = lst[i]['Id'] if 'Id' in lst[i] else None
                node_connections = lst[i]['Connections'] if 'Connections' in lst[i] else None
                node_dict = lst[i]

                text = ''
                if node_name:
                    text = node_name
                if draw_id:
                    if node_name and node_id:
                        text += ", "
                    if node_id:
                        text += node_id
                # text_attributes = str(lst[i]['Attributes']) if 'Attributes' in lst[i] else ''
                if 'Attributes' in lst[i]:
                    text_attributes = ''
                    for a, v in lst[i]['Attributes'].items():
                        if type(v) == str:
                            value = f"'{v.split(' / ')[0][0:30]}…'" if len(v.split(' / ')[0]) > 30 else f"'{v.split(' / ')[0]}'"
                        else:
                            value = v
                        text_attributes += f'{a}: {value}, '
                    text_attributes = text_attributes.rstrip(', ')
                else:
                    text_attributes = ''

                background_colors = {
                    'Items': '#FFF2CC',
                    'Narration': '#E1D5E7',
                    'Locations': '#D5E8D4',
                    'Characters': '#DAE8FC',
                }

                node_attributes = {
                    'shape': 'box',
                    'style': 'filled,rounded',
                    'fillcolor': background_colors[parent_key],
                    'color': background_colors[parent_key],
                }
                if id(lst[i]) in emph_nodes_ids:
                    node_attributes['color'] = 'red'
                    node_attributes['penwidth'] = '3'

                label = f"{text}"  # gdybyśmy chcieli dodac nr wierzchołka: ({nr[0]}<SUB>{nr[1:]}</SUB>)
                if text_attributes and text_attributes != '{}':
                    label += f'<BR/><FONT POINT-SIZE="10">{text_attributes}</FONT>'

                comment = comments.get(id(lst[i]))
                col = comments.get('color','black')
                if comment is not None:
                    label += f'<BR/><FONT POINT-SIZE="10" COLOR="{col}">{comment}</FONT>'
                graph.node(nr, f'< {label} >', **node_attributes)

                # if id(lst[i]) in emph_nodes_ids:
                #     node_attributes['color'] = 'red'
                #     node_attributes['penwidth'] = '3'

                self._vertex_counter += 1
                current_list.append(
                    {'node_nr': nr, 'node_dict': node_dict, 'node_name': node_name, 'node_id': node_id, 'node_conn': node_connections})



                if parent_name != 'root':
                    if id(lst[i]) in emph_nodes_ids:
                        graph.edge(nr, parent_name, color='red', penwidth="3")
                    else:
                        graph.edge(nr, parent_name)
                if not world and parent_key == 'Locations':
                    graph.edge(nr, 'root', color='white')



                current_list.extend(self._visualise_process(lst[i], parent_key, nr, graph, emph_nodes_ids, comments, world, draw_id))
        return current_list

    def visualise(self, what: Union[list, dict], title: str = None, description: str = None,
                  world: bool = False, emph_nodes_ids: list = None, emph_edges: list = None, comments: dict = None, draw_id = True) -> BaseGraph:
        """
        Visualize left or right side as graph.
        :param emph_edges:
        :param emph_nodes_ids:
        :param comments:
        :param what: for example production side
        :param title:
        :param description:
        :param world:
        :return:
        """
        if not emph_nodes_ids:
            emph_nodes_ids = []
        if not emph_edges:
            emph_edges = []
        if not comments:
            comments = {}
        # world = True
        if world:
            graph = graphviz.Digraph(engine='neato')  # neato
        else:
            graph = graphviz.Digraph(engine='dot')
        graph.attr(overlap='false')
        graph.attr(splines='true')
        graph.attr(dpi='150')
        graph.attr(ratio='fill')
        graph.attr(labelloc='t')

        full_desc = f'< {title}<BR/><BR/>'
        desc_formatted = ''
        if description:
            desc_formatted = '<BR/>'.join(textwrap.wrap(text=description, width=100))
            desc_formatted = f'<FONT POINT-SIZE="10">{desc_formatted}</FONT>'

        full_desc += desc_formatted
        full_desc += '<BR/> >'

        graph.attr(label=full_desc)

        if not world:
            graph.node('root', '', color='white')

        self._vertex_counter = 1
        node_list = self._visualise_process(what, 'root', '', graph, emph_nodes_ids, comments, world=world, draw_id = draw_id) # sprawdzić, czy root czy Root



        for node in node_list:
            try:
                for destination in node['node_conn']:
                    conn = None
                    for node2 in node_list:
                        try:
                            if node2['node_dict'] is destination["Destination"]:  # zm # było: if node2['node_name'] == destination["Destination"]:
                                conn = node2
                                break
                        except:
                            pass

                    if conn:
                        if (id(node['node_dict']), id(conn['node_dict'])) in emph_edges:
                            graph.edge(node['node_nr'], conn['node_nr'], color='red', penwidth="3", constraint='false')
                        else:
                            graph.edge(node['node_nr'], conn['node_nr'], constraint='false')
            except:
                pass

        return graph