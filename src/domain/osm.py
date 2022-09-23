import osmnx as ox
import logging

"""
    A class used to represent an OpenStreetMap.

    ...

    Attributes
    ----------
    query : str
        Formatted location to get the map using OSMnx.
    radius : float
        Circle size of the map.
    osm_map : osmnx.MultiDiGraph
        The map as a graph loaded using the OSMnx library.
    latitude : float
        Map latitude value.
    longitude : float
        Map longitude value.

    Methods
    -------
    load_map()
        Uses the OSMnx library to load the query map with the radius size.
    plot_map()
        Open a new window with a graph visualization of the map.
    add_edge_key_attribute()
        Insert the edke_key attribute in each street of the map.
    """


class OpenStreetMap:
    def __init__(self, query: str, radius: float):
        """
        Parameters
        ----------
        query : str
            Formatted location to get the map using OSMnx.
        radius : float
            Circle size of the map.
        """
        self._query = query
        self._radius = radius
        self._osm_map = None
        self._latitude = 0.0
        self._longitude = 0.0
        self._load_map()
        self._add_edge_key_attribute()

    def _load_map(self):
        """Load the map from de inserted addres and radius, saving also
        the values of latitude and longitude.

        Raises
        ------
        Exception
            If the map could not be loaded using this function.
        """
        try:
            self._osm_map, (self._latitude, self._longitude) = ox.graph_from_address(
                self._query, self._radius, return_coords=True, simplify=True
            )
        except Exception as ex:
            logging.info("[!] Error to load the map.")
            raise Exception("Load map error.")

    def plot_map(self):
        """Plot the map current loaded in the variable 'osm_map'

        Raises
        ------
        Exception
            If the map could not be ploted using this function.
        """
        try:
            ox.plot_graph(self._osm_map)
            return True
        except:
            logging.info("[!] Error to plot the map.")
            raise Exception("Plot map error.")

    def _add_edge_key_attribute(self):
        """Add a new key attribute in the map streets.
        This attribute is important to convert OpenStreetMap
        objects to Graph objects.

        Raises
        ------
        Exception
            If occurr some edge data access error.
        """
        try:
            edges = self._osm_map.edges.data()
            edge_key = 1
            for ed in edges:
                ed[2]["id_key"] = edge_key
                edge_key += 1
        except:
            logging.info("[!] Error to add edge keys.")
            raise Exception("Add edge keys error.")

    @property
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        self._radius = value

    @property
    def osm_map(self):
        return self._osm_map

    @osm_map.setter
    def osm_map(self, value):
        self._osm_map = value

    @property
    def latitude(self):
        return self._latitude

    @latitude.setter
    def latitude(self, value):
        self._latitude = value

    @property
    def longitude(self):
        return self._longitude

    @longitude.setter
    def longitude(self, value):
        self._longitude = value
