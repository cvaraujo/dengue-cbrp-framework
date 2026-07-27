
//
// Created by Carlos on 20/04/2024.
//

#ifndef SCBRP_SHP_H
#define SCBRP_SHP_H

#include "../classes/Graph.hpp"
#include "../classes/Parameters.hpp"

class ShortestPath {

  private:
    Graph *graph;
    vector<vector<int>> dist, next;
    vector<vector<vector<int>>> ij_path;

  public:
    explicit ShortestPath(Graph *graph) {
        this->graph = graph;
        allPairsShortestPath();
    };

    ShortestPath() = default;

    ~ShortestPath() {}

    void allPairsShortestPath();

    static int DijkstraLayeredDAG(vector<vector<Arc>> dag, int n, int s, int t, vector<int> &pred);

    static int DijkstraLayeredDAG(Graph *graph, unordered_map<int, int> &dag_2_graph, vector<vector<Arc>> dag, int n, int s, int t, vector<int> &pred);

    int ShortestPathST(int s, int t, vector<int> &path);

    int ShortestPathST(int s, int t);

    int SHPBetweenBlocks(int b1, int b2, set<int> &nodes);

    vector<int> getPath(int s, int t);
};

#endif // SCBRP_SHP_H
