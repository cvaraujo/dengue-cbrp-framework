//
// Created by carlos on 04/01/25.
//

#ifndef DPARP_STOCHASTIC_ROUTE_H
#define DPARP_STOCHASTIC_ROUTE_H

#include "Graph.hpp"
#include "Input.hpp"
#include "Parameters.hpp"
#include <algorithm>
#include <cstdlib>
#include <set>
#include <unordered_map>
#include <utility>

class Route {

  private:
    Input *input;
    Graph *graph_override = nullptr;
    int scenario_idx = -1;
    int time_blocks = 0, time_route = 0;
    vector<int> route, preds, used_node_to_attend_block, sequence_of_attended_blocks;
    vector<bool> blocks_attended;
    std::set<int> route_blocks;
    std::unordered_map<int, vector<int>> blocks_attendeds_per_node;
    vector<pair<int, int>> x; // Maybe not needed

    bool CanAlocateRemainingBlocksIntoOtherNodes(
        Graph *graph, int removed_b, int node,
        std::unordered_map<int, int> &new_node_to_block);

    void ChangeNodeAttendingBlock(int block, int old_node, int new_node);

    void RemoveBlockAndNodeIfPossible(Graph *graph, int block, int node);

    std::unordered_map<int, int> GetAttendedRealocatedBlocks(Graph *graph,
                                                             int node);

  public:
    Graph *getActiveGraph() const {
        return graph_override ? graph_override : input->getGraph();
    }

    int getRouteArcTime(int i, int j);
    vector<int> getRouteBlockConnectionRoute(const string &key);
    int getRouteBlockConnectionTime(const string &key);

    Route(Input *input, const vector<pair<int, int>> &arcs, const vector<int> &blocks);

    Route(Input *input, const vector<int> &y) {
        this->input = input;
        this->sequence_of_attended_blocks = y;
        this->PopulateDataStructures();
    };

    Route(Input *input, Graph *graph, int scenario_idx, const vector<int> &y) {
        this->input = input;
        this->graph_override = graph;
        this->scenario_idx = scenario_idx;
        this->sequence_of_attended_blocks = y;
        this->PopulateDataStructures();
    };

    Route(Input *input, const vector<pair<int, int>> &arcs) {
        this->input = input;
        this->x = arcs;
        this->PopulateRouteDataStructures(arcs);
    };

    // Destructor
    ~Route() {
        route.clear();
        preds.clear();
        blocks_attended.clear();
        used_node_to_attend_block.clear();
        route_blocks.clear();
        blocks_attendeds_per_node.clear();
        x.clear();
        sequence_of_attended_blocks.clear();
    };

    void GeneralSwapBlocks(int b1, int b2);

    explicit Route(Input *input) { this->input = input; };

    void setSequenceOfAttendingBlocks(vector<int> sequence) {
        this->sequence_of_attended_blocks = std::move(sequence);
    };

    void setRoute(vector<int> r) {
        for (int i = 1; i < r.size(); i++) {
            preds[r[i]] = r[i - 1];
        }
        this->route = std::move(r);
    };

    vector<int> getRoute() { return this->route; };

    set<int> getRouteBlocks() { return this->route_blocks; };

    int getTimeRoute() const { return this->time_route; };

    int getTimeAttBlocks() const { return this->time_blocks; };

    void setTimeRoute(int time) { this->time_route = time; };

    void setTimeBlocks(int time) { this->time_blocks = time; };

    vector<int> getSequenceOfAttendingBlocks() const {
        return this->sequence_of_attended_blocks;
    };

    void PopulateDataStructures();

    void PopulateRouteDataStructures(const vector<pair<int, int>> &arcs);

    void PopulateBlocksDataStructures(const vector<int> &blocks);

    void SwapInRouteBlocks(int b1, int b2);

    void SwapOutRouteBlocks(int b1, int b2);

    void RemoveBlockFromAttended(int b);

    void RemoveNodeFromRoute(int node);

    int EvaluateTimeChangeByRemovingNodeAndBlocks(int node_idx);

    int EvaluateTimeChangeByRemovingNodeAndReallocateBlocks(int node_idx);

    void RemoveBlockFromRoute(int b);

    void AddBlockToRoute(int b, bool in_best_order);

    int_pair EvaluateBlockInsertion(int prev_node, int next_node, int new_block);

    int_pair FindBestPositionToInsertBlock(int new_block);

    void AddBlockToAttended(int b);

    bool IsBlockInRoute(int b) {
        return this->blocks_attended[b] || this->route_blocks.find(b) != this->route_blocks.end();
    };

    bool IsBlockInsertionFactible(int block, int route_time_increase) {
        int total_time = this->time_route + this->time_blocks + route_time_increase +
                         this->input->getBlockTime(block);
        return (total_time <= this->input->getT());
    };

    bool IsBlockInsertionFactible(int block) {
        Graph *graph = this->getActiveGraph();
        int T = this->input->getT();
        int block_time = graph->getTimePerBlock(block);
        int curr_time = this->time_route + this->time_blocks;

        if (IsBlockInRoute(block)) {
            return (curr_time + block_time <= T);
        }

        if (curr_time + block_time >= T)
            return false;

        set<int> nodes_from_block = graph->getNodesFromBlock(block);
        int insert_time, prev_node, next_node, arc_removed_time;

        for (int i = 0; i < this->route.size() - 1; i++) {
            prev_node = this->route[i], next_node = this->route[i + 1];
            arc_removed_time = this->getRouteArcTime(prev_node, next_node);

            for (auto node : nodes_from_block) {
                insert_time = getRouteArcTime(prev_node, node) + getRouteArcTime(node, next_node) - arc_removed_time;
                if (curr_time + insert_time + block_time <= T)
                    return true;
            }
        }
        return false;
    };

    void InsertNodeInRoute(int node, int position) {
        int previous_node = this->route[position - 1],
            next_node = this->route[position];
        int change_route_time = this->getRouteArcTime(previous_node, node) +
                                this->getRouteArcTime(node, next_node) -
                                this->getRouteArcTime(previous_node, next_node);

        this->route.insert(this->route.begin() + position, node);
        this->preds[node] = previous_node, this->preds[next_node] = node;
        this->time_route += change_route_time;

        set<int> node_blocks = this->getActiveGraph()->getNode(node).second;
        this->route_blocks.insert(node_blocks.begin(), node_blocks.end());
    };

    bool IsTimeChangeFeasible(int time_change) {
        if (this->time_route + this->time_blocks + time_change >
            this->input->getT())
            return false;
        return true;
    };

    int EvaluateNodeRemoval(int node) {
        for (int i = 0; i < this->route.size(); i++) {
            if (this->route[i] == node) {
                int prev_node = this->route[i - 1], next_node = this->route[i + 1];
                return this->getRouteArcTime(prev_node, next_node) -
                       (this->getRouteArcTime(prev_node, node) +
                        this->getRouteArcTime(node, next_node));
            }
        }
        return INF;
    };

    int EvaluateTimeGainByRemovingBlock(int block) {
        Graph *graph = this->getActiveGraph();
        int node = this->used_node_to_attend_block[block];

        if (node == -1)
            return -INF;

        int time_gain = graph->getTimePerBlock(block);
        std::unordered_map<int, int> new_node_to_block;

        if (CanAlocateRemainingBlocksIntoOtherNodes(graph, block, node, new_node_to_block))
            time_gain += EvaluateNodeRemoval(node);

        return time_gain;
    };

    void ChangeRouteTime(int time) {
        this->time_route += time;
    };

    int GetBlockInsertionTime(int prev_node, int next_node, int new_block);

    bool IsBlockAttended(int b) const { return this->blocks_attended[b]; };

    bool IsSwapFeasible(int b1, int b2);

    bool IsOutSwapFeasible(int b1, int b2);

    set<int> getBlocks() const { return this->route_blocks; };

    bool IsSwapTimeLowerThanT(int b1, int b2, int prev_time_change) const;

    double GetScenarioProfit(const vector<int> &fs_blocks, int s) const {
        double profit = 0;
        for (int b : this->getSequenceOfAttendingBlocks()) {
            profit += this->input->getSecondStageProfit(s, b);
        }
        return profit;
    }

    bool CheckSolution() {
        // Validate Times
        int attend_time = 0;

        for (int b : this->sequence_of_attended_blocks) {
            attend_time += this->input->getBlockTime(b);

            // All attended blocks have a node in route
            if (this->used_node_to_attend_block[b] == -1) {
                cout << "[!] Block " << b << " has no node used to attend" << endl;
                exit(EXIT_FAILURE);
            }

            if (route_blocks.find(b) == route_blocks.end()) {
                cout << "[!] Block " << b << " is not in route" << endl;
                exit(EXIT_FAILURE);
            }

            if (!this->blocks_attended[b]) {
                cout << "[!] Block " << b << " is not attended" << endl;
                exit(EXIT_FAILURE);
            }
        }

        if (attend_time != this->time_blocks) {
            cout << "[!] Attend Time = " << attend_time << ", Time Blocks = " << this->time_blocks << endl;
            exit(EXIT_FAILURE);
        }

        int route_time = 0;
        for (int i = 0; i < this->route.size() - 1; i++) {
            int prev_node = this->route[i], next_node = this->route[i + 1];
            int arc_time = this->getRouteArcTime(prev_node, next_node);

            if (arc_time == INF) {
                cout << "[!] Infinity Arc Time = " << arc_time << endl;
                exit(EXIT_FAILURE);
            }
            route_time += arc_time;

            if (this->preds[next_node] != prev_node) {
                cout << "[!] Route: " << prev_node << " -> " << next_node << endl;
                cout << "[!] Preds[" << prev_node << "] = " << this->preds[next_node] << endl;
                exit(EXIT_FAILURE);
            }

            for (int block : this->blocks_attendeds_per_node[prev_node]) {
                if (!this->blocks_attended[block]) {
                    cout << "[!] Block " << block << " is not attended in node " << prev_node << endl;
                    exit(EXIT_FAILURE);
                }
            }
        }

        if (route_time != this->time_route) {
            cout << "[!] Route Time = " << route_time << ", Time Route = " << this->time_route << endl;
            exit(EXIT_FAILURE);
        }

        return true;
    }
};
#endif
