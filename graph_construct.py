import osmnx as ox
import rtree
from shapely.geometry import Point, LineString
import csv


def map_osm(place, network_type):
    print("Start Downloading Road Network of ", place, network_type, " From OpenStreetMap")
    try:
        graph = ox.graph_from_place(place,
                                    network_type=network_type,
                                    truncate_by_edge=True,
                                    simplify=True)
    except:
        graph = ox.graph_from_place(place,
                                    network_type=network_type,
                                    which_result=2,
                                    truncate_by_edge=True,
                                    simplify=True)

    print("Already Retrieved Map of ", place, " From OpenStreetMap")
    print("--------------------------------------------------------------------")

    return graph


def map_to_list(osm_g):
    node_col = {}
    ref_table = {}

    for n_id, n_inf in osm_g.nodes(data=True):
        if n_id not in ref_table:
            ref_table[n_id] = len(node_col)
            node_col[len(node_col)] = {'lng': n_inf['x'], 'lat': n_inf['y'], 'sites': set()}

    edge_col = {}
    for start_n, end_n, e_inf in osm_g.edges(data=True):
        if start_n != end_n:
            start_n, end_n = ref_table[start_n], ref_table[end_n]
            edge_col[(start_n, end_n)] = min(
                edge_col.get((start_n, end_n), float('inf')),
                e_inf['length']
            )
            if not e_inf['oneway']:
                edge_col[(end_n, start_n)] = min(
                    edge_col.get((end_n, start_n), float('inf')),
                    e_inf['length']
                )

    return node_col, edge_col


class PoI_Graph:
    def __init__(self, place:str, map_type:str):

        osm_graph = map_osm(place, map_type)

        self.node_col, self.edge_col = map_to_list(osm_graph)
        #self.poi_col = poi
        self.tree_idx, self.tree_count = self.build_tree()

    def build_tree(self):
        print("Start Building Rtree for Overlaying")
        #p = rtree.index.Property()
        tree_idx = rtree.index.Index(interleaved=True)
        tmp_id_count = 0

        for k, v in self.edge_col.items():
            corrd_1_lng, corrd_1_lat = self.node_col[k[0]]['lng'], self.node_col[k[0]]['lat']
            corrd_2_lng, corrd_2_lat = self.node_col[k[1]]['lng'], self.node_col[k[1]]['lat']
            left_c, bottom_c = min(corrd_1_lng, corrd_2_lng), min(corrd_1_lat, corrd_2_lat)
            right_c, top_c = max(corrd_1_lng, corrd_2_lng), max(corrd_1_lat, corrd_2_lat)
            tree_idx.insert(tmp_id_count, (left_c, bottom_c, right_c, top_c), obj=k)
            tmp_id_count += 1

        print("Already Done with R-tree")
        print("--------------------------------------------------------------------")

        return tree_idx, tmp_id_count-1

    def poi_overlay(self, pois):
        print_count = 1
        for k, v in pois.items():
            # lng & lat of each site
            p_lng, p_lat = v[0], v[1]

            '''
            Note: maybe more than 1 nearest edges (very normal) 
                Reason 1: Two-way road; 
                Reason 2: distance(site, edges) same.
            For Reason 1, update twice
            For Reason 2, randomly pick one would not influence the result
            '''
            # Get the nearest edge(s) of current site
            nearest_es = [(i.id, i.object, i.bbox) for i in self.tree_idx.nearest(
                (p_lng, p_lat, p_lng, p_lat),
                1,
                objects=True)]
            pick_e_info = nearest_es[0]
            # Get node idx of edge
            pick_id, pick_e, pick_bound = pick_e_info[0], pick_e_info[1], pick_e_info[2]

            start_e, end_e = self.node_col[pick_e[0]], self.node_col[pick_e[1]]

            # Project site node to nearest edge
            line_seq = LineString([(start_e['lng'], start_e['lat']), (end_e['lng'], end_e['lat'])])
            d_nn_part = line_seq.project(Point(p_lng, p_lat), normalized=True)

            if d_nn_part == 0:
                # Attach to start node of edge
                # But no change to edge
                self.node_col[pick_e[0]]['sites'].add(k)
                print("Match to existing node (start)...")
            elif d_nn_part == 1:
                # Attach to end node of edge
                # But no change to edge
                self.node_col[pick_e[1]]['sites'].add(k)
                print("Match to existing node (end)...")
            else:
                print("Match to new creating node...")
                # Create new node along edge
                projected_node = line_seq.interpolate(d_nn_part, normalized=True)
                # Add new node to node_col
                new_id = max(self.node_col) + 1
                self.node_col[new_id] = {'lng': projected_node.x, 'lat': projected_node.y, 'sites': set([k])}
                # Add new edges to edge_col & Delete previous edge(s) from edge_col
                start_site_len = self.edge_col[pick_e] * d_nn_part
                site_end_len = self.edge_col[pick_e] * (1 - d_nn_part)
                self.edge_col[(pick_e[0], new_id)] = start_site_len
                self.edge_col[(new_id, pick_e[1])] = site_end_len
                del self.edge_col[pick_e]

                # Add new edges to R Tree & Delete previous edge(s) from R Tree
                self.tree_count += 1
                left_c = min(projected_node.x, self.node_col[pick_e[0]]['lng'])
                bottom_c = min(projected_node.y, self.node_col[pick_e[0]]['lat'])
                right_c = max(projected_node.x, self.node_col[pick_e[0]]['lng'])
                top_c = max(projected_node.y, self.node_col[pick_e[0]]['lat'])
                self.tree_idx.insert(self.tree_count, (left_c, bottom_c, right_c, top_c), obj=(pick_e[0], new_id))

                self.tree_count += 1
                left_c = min(projected_node.x, self.node_col[pick_e[1]]['lng'])
                bottom_c = min(projected_node.y, self.node_col[pick_e[1]]['lat'])
                right_c = max(projected_node.x, self.node_col[pick_e[1]]['lng'])
                top_c = max(projected_node.y, self.node_col[pick_e[1]]['lat'])
                self.tree_idx.insert(self.tree_count, (left_c, bottom_c, right_c, top_c), obj=(new_id, pick_e[1]))

                self.tree_idx.delete(pick_id, tuple(pick_bound))

                print("Already updated edges...")

                # Check if it is a one-way road. If not, then update anti-way edge
                if (pick_e[1], pick_e[0]) in self.edge_col:
                    print("Updating anti-way edge...")
                    self.edge_col[(new_id, pick_e[0])] = start_site_len
                    self.edge_col[(pick_e[1], new_id)] = site_end_len
                    del self.edge_col[(pick_e[1], pick_e[0])]

                    self.tree_count += 1
                    self.tree_idx.insert(self.tree_count, (left_c, bottom_c, right_c, top_c), obj=(new_id, pick_e[0]))
                    self.tree_count += 1
                    self.tree_idx.insert(self.tree_count, (left_c, bottom_c, right_c, top_c), obj=(pick_e[1], new_id))

                    for each_n_e in nearest_es:
                        if each_n_e[1] == (pick_e[1], pick_e[0]):
                            self.tree_idx.delete(each_n_e[0], tuple(each_n_e[2]))
                            print("Already updated anti-way edges...")
                            break

            print("Done with ", print_count, " out of ", len(pois))
            print("----------------------------------------------")
            print_count += 1

        return self.node_col, self.edge_col


def main():
    city_name = 'New York city'
    state_name = 'New York'
    file_name = 'NY'

    osm_graph = PoI_Graph(city_name + ", " + state_name + ", USA", "drive")

    # Insert PoIs into network
    poi_dict = {}

    with open("PoI_Network/attractionNYLngLat.csv", 'r') as rhandle:
        spamreader = csv.reader(rhandle)

        # Skip the col names/titles
        next(spamreader)

        for each_poi in spamreader:
            poi_dict[each_poi[0]] = (float(each_poi[1]), float(each_poi[2]))

    ns_dict, es_dict = osm_graph.poi_overlay(poi_dict)

    print("Start Writing to files...")

    with open("PoI_Network/" + file_name + "_ns.csv", 'w', newline='') as whandle:
        spamwriter = csv.writer(whandle)

        spamwriter.writerow(['no', 'lng', 'lat', 'sites'])

        for k, v in ns_dict.items():
            spamwriter.writerow([
                k, v['lng'], v['lat'], '|'.join(list(v['sites']))
            ])

    with open("PoI_Network/" + file_name + "_es.csv", 'w', newline='') as whandle:
        spamwriter = csv.writer(whandle)

        spamwriter.writerow(['start', 'end', 'length'])

        for k, v in es_dict.items():
            spamwriter.writerow([
                k[0], k[1], v
            ])


if __name__ == "__main__":
    main()





