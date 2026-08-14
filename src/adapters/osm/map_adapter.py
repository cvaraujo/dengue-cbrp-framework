import os, copy
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
from shapely.geometry import Polygon, MultiPolygon
from domain.osm import *
from domain.graph import *
from domain.utils import *


class MapAdapter:
    @staticmethod
    def add_key_block_arc_attrs(osm: OpenStreetMap, graph: Graph):
        try:
            for u, v, data in osm.osm_map.edges(data=True):
                data["block"] = graph.get_arc_block_from_osmid_nodes(str(u), str(v))
        except Exception as e:
            print("[!!!] Error:", e)

    @staticmethod
    def export_osm_to_shapefile(osm: OpenStreetMap, graph: Graph, path: str) -> bool:
        try:
            print(f"[*] Exporting OSM to shapefile to {path}")
            os.makedirs(path, exist_ok=True)
            MapAdapter.add_key_block_arc_attrs(osm, graph)
            gdf_nodes, gdf_arcs = ox.convert.graph_to_gdfs(osm.osm_map)
            gdf_nodes.to_file(
                path + "/nodes.shp", driver="ESRI Shapefile", encoding="utf-8"
            )
            gdf_arcs.to_file(
                path + "/edges.shp", driver="ESRI Shapefile", encoding="utf-8"
            )
            return True
        except Exception as e:
            print("[!!!] Error to write the shapefiles:", e)
            return False

    @staticmethod
    def plot_region_map(
        map_data,
        output_dir: str,
        filename: str = "osm_region_validation.png",
        show: bool = False,
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)

        if isinstance(map_data, nx.MultiDiGraph):
            fig, ax = ox.plot_graph(
                map_data,
                show=False,
                close=False,
                bgcolor="white",
                node_size=0,
                edge_linewidth=0.8,
                edge_color="#1f77b4",
            )
        elif isinstance(map_data, (Polygon, MultiPolygon)):
            fig, ax = plt.subplots(figsize=(10, 10))
            gpd.GeoSeries([map_data]).plot(
                ax=ax,
                facecolor="#a6cee3",
                edgecolor="#1f78b4",
                linewidth=1.2,
            )
            ax.set_aspect("equal")
        else:
            raise TypeError(
                "map_data must be an OSM graph (networkx.MultiDiGraph) or a shapely Polygon/MultiPolygon."
            )

        ax.set_axis_off()
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        if show:
            plt.show()
        plt.close(fig)
        return output_path

    @staticmethod
    def convert_osm_to_graph(osm: OpenStreetMap, always_two_ways: bool) -> Graph:
        osm_map = osm.osm_map
        nodes = list(osm_map.nodes(data=True))
        arcs = list(osm_map.edges(data=True))

        graph = Graph()

        for i, (node_id, data) in enumerate(nodes, 0):
            new_node = Node(osmid=str(node_id), index=i, lat=data["y"], lon=data["x"])
            graph.add_osm_node(new_node)

        graph.arcs = [[] for _ in range(graph.n)]
        arc_key = 0
        new_arcs = []

        if always_two_ways:
            for u, v, data in arcs:
                data["id_key"] = arc_key
                if graph.add_osm_arc((u, v, data), with_two_ways=True):
                    new_data = copy.deepcopy(data)
                    new_data["id_key"] = arc_key + 1
                    new_arcs.append((u, v, data))
                    new_arcs.append((v, u, new_data))
                    arc_key += 2
            osm.osm_map.remove_edges_from(list(osm_map.edges()))
            osm.osm_map.add_edges_from(new_arcs)
        else:
            for arc in arcs:
                graph.add_osm_arc(arc, graph)

        graph.set_graph_blocks()
        return graph
