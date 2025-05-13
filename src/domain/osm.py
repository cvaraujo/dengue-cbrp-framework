import osmnx as ox

ox.settings.log_console = False

class OpenStreetMap:
    def __init__(self, query: str, radius: int):
        self.query: str = query
        self.radius: int = radius
        self.osm_map = None
        self.lat: float = 0.0
        self.lon: float = 0.0

        try:
            self.osm_map = ox.graph_from_address(query, radius, simplify=True)
        except Exception as e:
            print(f"Error to load the map: {e}")
