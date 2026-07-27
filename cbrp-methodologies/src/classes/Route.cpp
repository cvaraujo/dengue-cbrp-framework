//
// Created by carlos on 04/01/25.
//

#include "Route.hpp"
#include "../heuristic/stochastic/Utils.hpp"
#include <iterator>

Route::Route(Input *input, const vector<pair<int, int>> &arcs, const vector<int> &blocks) {
    this->input = input;
    this->x = arcs;
    this->PopulateRouteDataStructures(arcs);
    this->PopulateBlocksDataStructures(blocks);
}

void Route::PopulateDataStructures() {
    Graph *graph = getActiveGraph();

    string key = BlockConnection::GenerateStringFromIntVector(this->sequence_of_attended_blocks);
    this->route = getRouteBlockConnectionRoute(key);
    this->time_route = getRouteBlockConnectionTime(key);
    int B = graph->getB();
    preds = vector<int>(graph->getN() + 1, -1);
    route_blocks = set<int>();

    // Attended blocks
    blocks_attended = vector<bool>(B, false);
    this->time_blocks = 0;
    for (int b : this->sequence_of_attended_blocks) {
        time_blocks += graph->getTimePerBlock(b);
        blocks_attended[b] = true;
    }

    // Route starts and ends at node N
    used_node_to_attend_block = vector<int>(B, -1);
    this->blocks_attendeds_per_node = std::unordered_map<int, vector<int>>();
    set<int> node_blocks;
    int i, origin, destination;

    for (i = 1; i < this->route.size(); i++) {
        origin = route[i - 1], destination = route[i];
        node_blocks = graph->getNode(destination).second;

        this->preds[destination] = origin;
        this->route_blocks.insert(node_blocks.begin(), node_blocks.end());

        for (int b : node_blocks) {
            if (blocks_attended[b] && this->used_node_to_attend_block[b] == -1) {
                if (this->blocks_attendeds_per_node.find(destination) == this->blocks_attendeds_per_node.end())
                    this->blocks_attendeds_per_node[destination] = vector<int>();
                this->blocks_attendeds_per_node[destination].push_back(b);
                this->used_node_to_attend_block[b] = destination;
            }
        }
    }

}

void Route::PopulateRouteDataStructures(const vector<pair<int, int>> &arcs) {
    Graph *graph = this->getActiveGraph();
    preds = vector<int>(graph->getN() + 1, -1);
    route_blocks = set<int>();

    for (auto arc : arcs) {
        int i = arc.first, j = arc.second;
        this->route[i] = j, this->preds[j] = i;
        Arc *g_arc = graph->getArc(i, j);

        if (g_arc == nullptr) {
            cout << "i: " << i << ", j: " << j << endl;
            throw std::runtime_error("[!!!] Invalid arc while populate route data structures!");
        }

        this->time_route += g_arc->getLength();
        set<int> blocks_i = graph->getNode(i).second, blocks_j = graph->getNode(j).second;
        route_blocks.insert(blocks_i.begin(), blocks_i.end());
        route_blocks.insert(blocks_j.begin(), blocks_j.end());
    }
}

void Route::PopulateBlocksDataStructures(const vector<int> &blocks) {
    Graph *graph = this->getActiveGraph();
    this->blocks_attended = vector<bool>(graph->getB(), false);

    for (auto b : blocks) {
        this->blocks_attended[b] = true;
        time_blocks += graph->getTimePerBlock(b);

        set<int> nodes = graph->getNodesFromBlock(b);
        for (auto node : nodes) {
            if (preds[node] != -1) {
                // if (this->att_blocks_per_node.find(node) == this->att_blocks_per_node.end())
                //     this->att_blocks_per_node[node] = vector<int>();

                // this->att_blocks_per_node[node].push_back(b);
                // this->used_node_attended_block[b] = node;
                break;
            }
        }
    }
}

void Route::SwapInRouteBlocks(int b1, int b2) {
    // Basic checks
    if (!this->blocks_attended[b1])
        throw std::runtime_error("[!!!] Block " + to_string(b1) + " not attended to be swapped!");

    if (this->blocks_attended[b2])
        throw std::runtime_error("[!!!] Block " + to_string(b2) + " already attended!");

    this->RemoveBlockFromAttended(b1);
    this->AddBlockToAttended(b2);
}

void Route::SwapOutRouteBlocks(int b1, int b2) {
    // Basic checks
    if (!this->blocks_attended[b1])
        throw std::runtime_error("[!!!] Block " + to_string(b1) + " not attended to be swapped!");

    if (IsBlockInRoute(b2))
        throw std::runtime_error("[!!!] Block " + to_string(b2) + " already in route!");

    this->RemoveBlockFromRoute(b1);
    this->AddBlockToRoute(b2, true);
}

void Route::GeneralSwapBlocks(int b1, int b2) {
    // cout << "[!] GeneralSwapBlocks" << endl;
    bool b1_in_route = this->IsBlockInRoute(b1), b2_in_route = this->IsBlockInRoute(b2);
    bool b1_attended = this->IsBlockAttended(b1), b2_attended = this->IsBlockAttended(b2);

    if (b1_attended == b2_attended) {
        cout << "[!] Both blocks are in same situation, the swap is not feasible!" << endl
             << "(" << b1_attended << ", " << b2_attended << ")" << endl;
        return;
    }

    // Swap in route
    if (b1_in_route && b2_in_route) {
        int to_remove = b1_attended ? b1 : b2;
        int to_insert = b2_attended ? b1 : b2;
        this->SwapInRouteBlocks(to_remove, to_insert);
    } else {
        int to_remove = b1_attended ? b1 : b2;
        int to_insert = b2_attended ? b1 : b2;
        this->SwapOutRouteBlocks(to_remove, to_insert);
    }
}

void Route::RemoveBlockFromAttended(int b) {
    // cout << "[!] RemoveBlockFromAttended: " << b << endl;
    // Basic checks
    if (!this->blocks_attended[b])
        return;

    // Remove references of b
    this->blocks_attended[b] = false;
    auto it = find(sequence_of_attended_blocks.begin(), sequence_of_attended_blocks.end(), b);
    if (it != sequence_of_attended_blocks.end())
        sequence_of_attended_blocks.erase(it);

    int node_b = this->used_node_to_attend_block[b];
    this->used_node_to_attend_block[b] = -1;
    vector<int> &attended_blocks = this->blocks_attendeds_per_node[node_b];
    Utils::IntVectorRemove(attended_blocks, find(attended_blocks.begin(), attended_blocks.end(), b));
    this->blocks_attendeds_per_node[node_b] = attended_blocks;
    this->time_blocks -= input->getBlockTime(b);
}

bool Route::CanAlocateRemainingBlocksIntoOtherNodes(Graph *graph, int removed_b, int node, std::unordered_map<int, int> &new_node_to_block) {
    vector<int> blocks = this->blocks_attendeds_per_node[node];

    for (auto b : blocks) {
        if (b == removed_b)
            continue;

        set<int> nodes_b = graph->getNodesFromBlock(b);
        bool can_alocate = false;

        for (auto node_b : nodes_b) {
            if (node_b == node)
                continue;

            if (this->preds[node_b] != -1) {
                can_alocate = true;
                new_node_to_block[b] = node_b;
                break;
            }
        }

        if (!can_alocate)
            return false;
    }
    return true;
};

void Route::RemoveNodeFromRoute(int node) {
    // cout << "[!] RemoveNodeFromRoute: " << node << endl;
    // Minimal route
    if (route.size() <= 3)
        return;

    int i, curr_node, prev_node, next_node;
    for (i = 1; i < route.size() - 1; i++) {
        curr_node = route[i];
        if (curr_node == node) {
            prev_node = route[i - 1], next_node = route[i + 1];
            this->time_route -= this->getRouteArcTime(prev_node, curr_node) + this->getRouteArcTime(curr_node, next_node);
            this->time_route += this->getRouteArcTime(prev_node, next_node);
            this->preds[next_node] = prev_node;
            route.erase(route.begin() + i);
            break;
        }
    }

    Graph *graph = this->getActiveGraph();
    this->preds[node] = -1;
    for (auto block : this->blocks_attendeds_per_node[node]) {
        this->blocks_attended[block] = false;
        this->used_node_to_attend_block[block] = -1;
        this->time_blocks -= input->getBlockTime(block);
    }

    this->blocks_attendeds_per_node.erase(node);

    // Reset Route_blocks
    route_blocks.clear();
    for (int route_node : route) {
        set<int> blocks = graph->getNode(route_node).second;
        route_blocks.insert(blocks.begin(), blocks.end());
    }
};

void Route::ChangeNodeAttendingBlock(int block, int old_node, int new_node) {
    // cout << "[!] ChangeNodeAttendingBlock: " << block << ", Old Node: " << old_node << ", New Node: " << new_node << endl;
    this->used_node_to_attend_block[block] = new_node;

    if (this->blocks_attendeds_per_node.find(new_node) == this->blocks_attendeds_per_node.end())
        this->blocks_attendeds_per_node[new_node] = vector<int>();
    this->blocks_attendeds_per_node[new_node].push_back(block);

    vector<int> &attended_blocks = this->blocks_attendeds_per_node[old_node];
    Utils::IntVectorRemove(attended_blocks, find(attended_blocks.begin(), attended_blocks.end(), block));
    this->blocks_attendeds_per_node[old_node] = attended_blocks;
};

void Route::RemoveBlockAndNodeIfPossible(Graph *graph, int block, int node) {
    std::unordered_map<int, int> block_to_new_node = GetAttendedRealocatedBlocks(graph, node);
    int num_blocks_to_realocate = int(blocks_attendeds_per_node[node].size()) - 1;

    int reallocatable_count = 0;
    for (auto &[b, _] : block_to_new_node)
        if (b != block)
            reallocatable_count++;

    if (reallocatable_count >= num_blocks_to_realocate) {
        for (auto &[realoc_block, new_node] : block_to_new_node) {
            if (realoc_block == block)
                continue;

            this->ChangeNodeAttendingBlock(realoc_block, node, new_node);
        }
    }

    this->RemoveBlockFromAttended(block);
    if (this->blocks_attendeds_per_node[node].size() <= 0 && this->route.size() > 3)
        this->RemoveNodeFromRoute(node);
}

std::unordered_map<int, int> Route::GetAttendedRealocatedBlocks(Graph *graph, int node) {
    std::unordered_map<int, int> block_to_new_node;
    vector<int> blocks = this->blocks_attendeds_per_node[node];

    for (auto b : blocks) {
        for (auto node_b : graph->getNodesFromBlock(b)) {
            if (node_b == node)
                continue;

            if (this->preds[node_b] != -1) {
                block_to_new_node[b] = node_b;
                break;
            }
        }
    }
    return block_to_new_node;
}

int Route::EvaluateTimeChangeByRemovingNodeAndBlocks(int node_idx) {
    int curr_time = this->time_route + this->time_blocks;
    int new_time = curr_time;
    int curr_node, prev_node, next_node;

    curr_node = route[node_idx], prev_node = route[node_idx - 1], next_node = route[node_idx + 1];
    new_time += getRouteArcTime(prev_node, next_node) - (getRouteArcTime(prev_node, curr_node) + getRouteArcTime(curr_node, next_node));

    for (auto block : blocks_attendeds_per_node[curr_node])
        new_time -= input->getBlockTime(block);

    return new_time - curr_time;
}

int Route::EvaluateTimeChangeByRemovingNodeAndReallocateBlocks(int node_idx) {
    Graph *graph = this->getActiveGraph();
    int curr_time = this->time_route + this->time_blocks, new_time = curr_time;
    int curr_node, prev_node, next_node;

    curr_node = route[node_idx], prev_node = route[node_idx - 1], next_node = route[node_idx + 1];
    new_time += getRouteArcTime(prev_node, next_node) - (getRouteArcTime(prev_node, curr_node) + getRouteArcTime(curr_node, next_node));

    std::unordered_map<int, int> new_node_to_block = this->GetAttendedRealocatedBlocks(graph, curr_node);

    for (auto b : this->blocks_attendeds_per_node[curr_node]) {
        if (new_node_to_block.find(b) != new_node_to_block.end())
            continue;
        new_time -= graph->getTimePerBlock(b);
    }
    return new_time - curr_time;
}

void Route::RemoveBlockFromRoute(int b) {
    if (!this->IsBlockInRoute(b))
        throw std::runtime_error("[!] Block " + to_string(b) + " not in route to be removed!");

    Graph *graph = this->getActiveGraph();
    int i, block;
    for (i = 0; i < this->sequence_of_attended_blocks.size(); i++) {
        block = this->sequence_of_attended_blocks[i];
        if (block != b)
            continue;

        int node = this->used_node_to_attend_block[block];
        this->RemoveBlockAndNodeIfPossible(graph, block, node);
        break;
    }
}

int_pair Route::EvaluateBlockInsertion(int prev_node, int next_node, int new_block) {
    Graph *graph = this->getActiveGraph();
    set<int> nodes_from_block = graph->getNodesFromBlock(new_block);

    int insert_time, best_time = INT_MAX, best_node = -1;
    int arc_removed_time = getRouteArcTime(prev_node, next_node);

    for (auto node : nodes_from_block) {
        insert_time = (-1) * arc_removed_time;
        insert_time += getRouteArcTime(prev_node, node) + getRouteArcTime(node, next_node);

        if (this->IsTimeChangeFeasible(insert_time) && (insert_time < best_time))
            best_time = insert_time, best_node = node;
    }
    return make_pair(best_node, best_time);
}

int Route::GetBlockInsertionTime(int prev_node, int next_node, int new_block) {
    Graph *graph = this->getActiveGraph();
    set<int> nodes_from_block = graph->getNodesFromBlock(new_block);

    int insert_time, best_time = INT_MAX, best_node = -1;
    int arc_removed_time = getRouteArcTime(prev_node, next_node);

    for (auto node : nodes_from_block) {
        insert_time = (-1) * arc_removed_time;
        insert_time += getRouteArcTime(prev_node, node) + getRouteArcTime(node, next_node);

        if (insert_time < best_time)
            best_time = insert_time, best_node = node;
    }
    return best_time;
}

int_pair Route::FindBestPositionToInsertBlock(int new_block) {
    int best_time_insert = INF, best_node_insert = -1, best_position = -1;

    int_pair insert_pair;
    for (int i = 0; i < this->route.size() - 1; i++) {
        int prev_node = this->route[i], next_node = this->route[i + 1];
        insert_pair = this->EvaluateBlockInsertion(prev_node, next_node, new_block);
        int node_insert = insert_pair.first, time_insert = insert_pair.second;

        if (node_insert == -1)
            continue;

        if (time_insert < best_time_insert)
            best_time_insert = time_insert, best_node_insert = node_insert, best_position = i + 1;
    }

    return make_pair(best_node_insert, best_position);
}

void Route::AddBlockToRoute(int b, bool in_best_order) {
    if (this->IsBlockInRoute(b)) {
        this->AddBlockToAttended(b);
        return;
    }

    int used_node = -1, position = -1;
    if (in_best_order) {
        int_pair pos_insert_block = this->FindBestPositionToInsertBlock(b);
        used_node = pos_insert_block.first, position = pos_insert_block.second;
    } else {
        int previous_node = this->route[this->route.size() - 2], next_node = this->route[this->route.size() - 1];
        int_pair insert_on_end = this->EvaluateBlockInsertion(previous_node, next_node, b);
        used_node = insert_on_end.first, position = int(this->route.size()) - 1;
    }

    if (used_node == -1)
        return;

    this->InsertNodeInRoute(used_node, position);
    this->AddBlockToAttended(b);
}

void Route::AddBlockToAttended(int b) {
    Graph *graph = this->getActiveGraph();
    if (this->blocks_attended[b])
        throw std::runtime_error("[!!!] Block " + to_string(b) + " already attended!");

    int time_block = graph->getTimePerBlock(b);
    if (this->time_route + this->time_blocks + time_block > this->input->getT()) {
        cout << this->time_route << " " << this->time_blocks << " " << time_block << " " << this->input->getT() << endl;
        throw std::runtime_error("[!!!] Time to Insert Block " + to_string(b) + " exceeds time limit!");
    }

    set<int> nodes_b = graph->getNodesFromBlock(b);
    int assigned_node = -1;
    for (auto node : nodes_b) {
        if (preds[node] != -1) {
            if (this->blocks_attendeds_per_node.find(node) == this->blocks_attendeds_per_node.end())
                this->blocks_attendeds_per_node[node] = vector<int>();

            this->blocks_attendeds_per_node[node].push_back(b);
            this->used_node_to_attend_block[b] = node;
            assigned_node = node;
            break;
        }
    }

    if (assigned_node == -1)
        return;

    this->blocks_attended[b] = true;
    this->sequence_of_attended_blocks.push_back(b);
    this->time_blocks += time_block;
};

bool Route::IsSwapFeasible(int b1, int b2) {
    return (this->time_route + this->time_blocks) + (input->getBlockTime(b2) - input->getBlockTime(b1)) <= input->getT();
};

bool Route::IsOutSwapFeasible(int b1, int b2) {
    Graph *graph = this->getActiveGraph();
    int time_change = graph->getTimePerBlock(b2) - this->EvaluateTimeGainByRemovingBlock(b1);

    // Only attend the block is already infeasible
    if (this->time_route + this->time_blocks + time_change > input->getT())
        return false;

    set<int> nodes_from_block = graph->getNodesFromBlock(b2);
    int insert_time, prev_node, next_node, arc_removed_time;
    for (int i = 0; i < this->route.size() - 1; i++) {
        prev_node = this->route[i], next_node = this->route[i + 1];
        arc_removed_time = this->getRouteArcTime(prev_node, next_node);

        for (auto node : nodes_from_block) {
            insert_time = getRouteArcTime(prev_node, node) + getRouteArcTime(node, next_node) - arc_removed_time;
            if (this->time_route + this->time_blocks + insert_time + time_change <= input->getT()) {
                return true;
            }
        }
    }

    return false;
}

bool Route::IsSwapTimeLowerThanT(int b1, int b2, int prev_time_change) const {
    return (this->time_route + this->time_blocks) + prev_time_change + (input->getBlockTime(b2) - input->getBlockTime(b1)) <= input->getT();
}

int Route::getRouteArcTime(int i, int j) {
    if (scenario_idx < 0)
        return input->getArcTime(i, j);

    Graph *sg = getActiveGraph();
    int N = sg->getN();
    if (i >= N || j >= N)
        return 0;

    ::Arc *arc = sg->getArc(i, j);
    if (arc != nullptr)
        return arc->getLength();

    ShortestPath *ssp = input->getScenarioSP(scenario_idx);
    vector<int> path;
    return ssp->ShortestPathST(i, j, path);
}

vector<int> Route::getRouteBlockConnectionRoute(const string &key) {
    if (scenario_idx < 0)
        return input->getBlockConnectionRoute(key);
    return input->getScenarioBCon(scenario_idx)->getBlocksAttendPath(key);
}

int Route::getRouteBlockConnectionTime(const string &key) {
    if (scenario_idx < 0)
        return input->getBlockConnectionTime(key);
    return input->getScenarioBCon(scenario_idx)->getBlocksAttendCost(key);
}
