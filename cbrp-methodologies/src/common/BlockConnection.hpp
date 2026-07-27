//
// Created by Carlos on 20/04/2024.
//

#ifndef SCBRP_BC_H
#define SCBRP_BC_H

#include "../classes/Arc.hpp"
#include "../classes/Graph.hpp"
#include "../classes/Parameters.hpp"
#include "ShortestPath.hpp"

class BlockConnection {

  private:
    Graph *graph;
    ShortestPath *sp;
    map<string, int> blocks_attend_cost;
    map<string, vector<int>> blocks_attend_path, best_order_attend_blocks;
    vector<vector<int>> block_2_block_cost;

  public:
    BlockConnection() = default;

    BlockConnection(Graph *graph, ShortestPath *sp) {
        this->graph = graph;
        this->sp = sp;
    };

    ~BlockConnection() {};

    int HeuristicBlockConnection(Graph *graph, ShortestPath *sp, vector<int> blocks, string key);

    set<int> computeBlock2BlockCost() {
        // Remove unecessary arcs between blocks
        int B = graph->getB();
        this->block_2_block_cost = vector<vector<int>>(B, vector<int>(B, INF));
        set<int> set_of_used_nodes, nodes_in_path, union_set;

        for (int b = 0; b < B - 1; b++) {
            for (int b2 = b + 1; b2 < B; b2++) {
                nodes_in_path = set<int>();
                int cost = this->sp->SHPBetweenBlocks(b, b2, nodes_in_path);

                if (cost < INF) {
                    union_set = set<int>();
                    set_union(nodes_in_path.begin(), nodes_in_path.end(), set_of_used_nodes.begin(), set_of_used_nodes.end(), inserter(union_set, union_set.begin()));
                    set_of_used_nodes = union_set;
                    this->block_2_block_cost[b][b2] = this->block_2_block_cost[b2][b] = cost;
                }
            }
        }

        return set_of_used_nodes;
    };

    static string GenerateStringFromIntVector(vector<int> blocks) {
        stringstream result;
        vector<int> keys(std::move(blocks));
        sort(keys.begin(), keys.end());
        copy(keys.begin(), keys.end(), ostream_iterator<int>(result, "_"));

        return result.str();
    };

    int_pair MinNode2BlockTime(int node, int block) {
        int time, min_node = -1, min_time = INF;
        for (int to : this->graph->getNodesFromBlock(block)) {
            if (node == to)
                return {0, node};

            time = this->sp->ShortestPathST(node, to);
            if (time < min_time) {
                min_time = time, min_node = to;
            }
        }
        return {min_time, min_node};
    }

    vector<vector<Arc>> createLayeredDag(vector<int> nodes, unordered_map<int, int> &dag_2_graph, int &V);

    vector<int> getBestOrderToAttendBlocks(const vector<int> &blocks, int block_sort_option);

    void setBlocksAttendCost(const string &key, int cost) { this->blocks_attend_cost[key] = cost; }

    void setBlocksAttendPath(const string &key, vector<int> path) { this->blocks_attend_path[key] = std::move(path); }

    int getBlocksAttendCost(const string &key) {
        auto it = this->blocks_attend_cost.find(key);
        if (it != this->blocks_attend_cost.end())
            return it->second;
        return INF;
    }

    vector<int> getBlocksAttendPath(const string &key) {
        auto it = this->blocks_attend_path.find(key);
        if (it != this->blocks_attend_path.end())
            return it->second;
        return {};
    }

    void setBlock2BlockCost(vector<vector<int>> block_2_block_cost) { this->block_2_block_cost = std::move(block_2_block_cost); }

    vector<vector<int>> getBlock2BlockCost() { return this->block_2_block_cost; }

    void setBestOrderToAttendBlocks(const string &key, vector<int> order) { this->best_order_attend_blocks[key] = std::move(order); }

    vector<int> getBestOrderToAttendBlocks(const string &key) {
        auto it = this->best_order_attend_blocks.find(key);
        if (it != this->best_order_attend_blocks.end())
            return it->second;
        return {};
    }

    int getBlock2BlockCost(int i, int j) { return this->block_2_block_cost[i][j]; }

    vector<int> getBestOrderToAttendBlocksB2B(const vector<int> &blocks, int block_sort_option);

    bool keyExists(const string &key) { return this->blocks_attend_cost.find(key) != this->blocks_attend_cost.end(); }

    void updateBlock2BlockCost(int i, int j, int cost) { this->block_2_block_cost[i][j] = cost; }

    void UpdateBestKnowBlockConnection(vector<int> &blocks, vector<int> &path, int time) {
        string key = BlockConnection::GenerateStringFromIntVector(blocks);
        setBlocksAttendCost(key, time);
        setBlocksAttendPath(key, path);
    }
};

#endif // SCBRP_SHP_H
