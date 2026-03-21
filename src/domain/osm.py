from pathlib import Path
import osmnx as ox
import matplotlib.pyplot as plt
# import contextily as ctx
import numpy as np
import matplotlib as mpl
from collections import defaultdict
from matplotlib.colors import LinearSegmentedColormap
from shapely.geometry import Polygon, MultiLineString, LineString
import geopandas as gpd
from matplotlib.lines import Line2D
from shapely.ops import polygonize
from mpl_toolkits.axes_grid1 import make_axes_locatable

ox.settings.log_console = False

class OpenStreetMap:
    def __init__(self, query: str, city_key: str, radius: int = 0, load_from_radius: bool = False):
        self.query: str = query
        self.city_key: str = city_key
        self.radius: int = radius
        self.osm_map = None

        try:
            if not self.check_map_exists():
                if load_from_radius:
                    print("Using radius to load map...")
                    self.osm_map = ox.graph_from_address(query, radius, simplify=True)
                else:
                    print("Ignoring radius and loading map from place name...")
                    self.osm_map = ox.graph_from_place(query, network_type="drive", simplify=True)
        except Exception as e:
            print(f"Error to load the map: {e}")
            raise
    
    def check_map_exists(self) -> bool:
        folder_name = f"{self.city_key}_{self.radius}"
        local_shp_folder = Path("./src/includes") / folder_name
        edges_shp = local_shp_folder / "edges.shp"
        nodes_shp = local_shp_folder / "nodes.shp"
        
        if edges_shp.exists() and nodes_shp.exists():
            print(f"Found local shapefiles for map: {local_shp_folder}")
            try:
                # Carregar nodes e edges dos shapefiles
                nodes_gdf = gpd.read_file(nodes_shp)
                edges_gdf = gpd.read_file(edges_shp)

                nodes_gdf = nodes_gdf.set_index('osmid') if 'osmid' in nodes_gdf.columns else nodes_gdf
                edges_gdf = edges_gdf.set_index(['u', 'v', 'key']) if all(col in edges_gdf.columns for col in ['u', 'v', 'key']) else edges_gdf
        
                
                self.osm_map = ox.graph_from_gdfs(nodes_gdf, edges_gdf)
                print(f"Map loaded from local files: {local_shp_folder}")
                return True
            except Exception as e:
                print(f"Error loading local shapefiles: {e}")
                raise
        
        return False
        
    def plot_map(self, show: bool = True, save_path: str = None, **kwargs):
        if self.osm_map is not None:
            nodes, edges = ox.graph_to_gdfs(self.osm_map)
            fig, ax = plt.subplots(figsize=(10, 10))
            edges.plot(ax=ax, linewidth=1, edgecolor="k", alpha=0.7, zorder=2)
            nodes.plot(ax=ax, markersize=5, color="grey", zorder=3)

            # Set extent for basemap
            xmin, ymin, xmax, ymax = nodes.total_bounds
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)

            # Add a realistic basemap (e.g., OSM or satellite)
            try:
                # You can change the source to ctx.providers.Stamen.Terrain, .Toner, or .Esri.WorldImagery for satellite
                # Increase the quality of the basemap by setting a higher zoom level and using antialiasing
                ctx.add_basemap(
                    ax,
                    source=ctx.providers.OpenStreetMap.Mapnik,
                    crs=nodes.crs,
                    zorder=1,
                    zoom=17,
                    interpolation='antialiased'
                )
            except Exception as e:
                print(f"Could not add basemap: {e}")

            ax.axis("off")
            if save_path:
                plt.savefig(save_path, bbox_inches='tight', dpi=300)
            if show:
                plt.show()
            plt.close(fig)
        else:
            print("No OSM map loaded to plot.")

    def plot_map_with_cases(self, cases: np.array, save_path: str):
        if self.osm_map is not None:
            nodes, edges = ox.graph_to_gdfs(self.osm_map)
            fig, ax = plt.subplots(figsize=(10, 10))

            nodes.plot(ax=ax, markersize=5, color="grey", zorder=3)

            # Map block number to number of cases for quick lookup
            block_cases = {block: num_cases for block, num_cases in enumerate(cases, 0) if num_cases > 0}

            # --- Prepare block->edges and block->nodes mapping ---
            block_to_edges = defaultdict(list)
            block_to_nodes = defaultdict(set)
            for u, v, data in self.osm_map.edges(data=True):
                block = data.get("block")
                if block is not None:
                    block_to_edges[block].append((u, v))
                    block_to_nodes[block].add(u)
                    block_to_nodes[block].add(v)

            cmap_cases = mpl.cm.Reds

            if block_cases:
                num_cases_list = list(block_cases.values())
                min_cases = min(num_cases_list)
                max_cases = max(num_cases_list)
                norm_cases = mpl.colors.Normalize(vmin=min_cases, vmax=max_cases if max_cases > min_cases else min_cases + 1)
            else:
                norm_cases = None
                cmap_cases = None



            # --- Fill polygons for each block with real cases (red) ---
            for block, num_cases in block_cases.items():
                edge_tuples = block_to_edges.get(block, [])
                if not edge_tuples:
                    continue
                lines = []
                for u, v in edge_tuples:
                    try:
                        line = edges.loc[edges.index.isin([(u, v)])].geometry.values
                        if len(line) > 0:
                            lines.append(line[0])
                    except Exception:
                        continue
                if not lines:
                    continue
                try:
                    mls = MultiLineString(lines)
                    from shapely.ops import polygonize
                    polys = list(polygonize(mls))
                    if polys:
                        poly = max(polys, key=lambda p: p.area)
                        color = cmap_cases(norm_cases(num_cases)) if cmap_cases and norm_cases else (1, 0, 0, 0.5)
                        gpd.GeoSeries([poly]).plot(ax=ax, facecolor=color, edgecolor=None, alpha=0.5, zorder=2)
                except Exception as e:
                    print(f"Could not polygonize block {block} (cases): {e}")

            # --- Plot edges with color intensity based on number of cases (red) ---
            edge_blocks = []
            for u, v, data in self.osm_map.edges(data=True):
                block = data.get("block")
                num_cases = block_cases.get(block, 0)
                if num_cases > 0:
                    edge_blocks.append(((u, v), num_cases))

            if edge_blocks and cmap_cases and norm_cases:
                for (u, v), num_cases in edge_blocks:
                    edge_gdf = edges.loc[edges.index.isin([(u, v)])]
                    color = cmap_cases(norm_cases(num_cases))
                    edge_gdf.plot(ax=ax, linewidth=2, edgecolor=color, zorder=4)

            # Add colorbars for both real cases, with same scale, size, and label above
            # Determine the global min/max for both real cases for a unified scale
            min_val = 0
            max_val = 0
            if block_cases:
                max_val = max(max_val, max(block_cases.values()))
            # Avoid zero range
            if max_val == min_val:
                max_val = min_val + 1

            # Create a unified norm for both colorbars
            unified_norm = mpl.colors.Normalize(vmin=min_val, vmax=max_val)

            # Create ScalarMappables for both, using the unified norm
            sm_cases = None
            if cmap_cases:
                sm_cases = mpl.cm.ScalarMappable(cmap=cmap_cases, norm=unified_norm)
                sm_cases.set_array([])


            divider = make_axes_locatable(ax)
            # Place real cases colorbar to the right, simulated to the right of that
            cax1 = divider.append_axes("right", size="3%", pad=0.04)

            cbar_cases = None
            if sm_cases:
                cbar_cases = plt.colorbar(sm_cases, cax=cax1)
                cbar_cases.set_label('Real Cases', rotation=270, labelpad=10, fontsize=10, loc='center')
                cax1.xaxis.set_label_position('top')
                cax1.xaxis.set_ticks_position('bottom')

            # Set extent for basemap
            xmin, ymin, xmax, ymax = nodes.total_bounds
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)

            # Add a realistic basemap (e.g., OSM or satellite)
            try:
                ctx.add_basemap(
                    ax,
                    source=ctx.providers.OpenStreetMap.Mapnik,
                    crs=nodes.crs,
                    zorder=1,
                    zoom=17,
                    interpolation='antialiased'
                )
            except Exception as e:
                print(f"Could not add basemap: {e}")

            ax.axis("off")
            if save_path:
                plt.savefig(save_path, bbox_inches='tight', dpi=300)
            plt.close(fig)
        else:
            print("No OSM map loaded to plot.")