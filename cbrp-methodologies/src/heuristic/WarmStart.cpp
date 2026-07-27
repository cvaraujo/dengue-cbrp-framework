//
// Created by carlos on 28/12/22.
//

#include "../headers/WarmStart.h"
#include "set"

bool WarmStart::attend_max_blocks(Graph *graph, int j, float &available_time, float max_time,
                                  float &of, vector<float> &node_profit, vector<bool> &serviced, vector<pair<int, int>> &y)
{
    bool attend = false;
    int block, cases;
    vector<pair<int, int>> ordered_blocks;

    for (auto block : graph->nodes[j].second)
        if (block != -1)
            ordered_blocks.push_back(make_pair(block, graph->cases_per_block[block]));

    sort(ordered_blocks.begin(), ordered_blocks.end(), [](auto &a, auto &b)
         { return a.second > b.second; });

    for (auto pair : ordered_blocks)
    {
        block = pair.first, cases = pair.second;

        if (serviced[block])
            continue;

        float time = available_time - graph->time_per_block[block];

        if (time >= 0)
        {
            // Mark the block as served
            y.push_back(make_pair(j, block));
            serviced[block] = true;

            of += cases;

            // Change the available amount of resources
            available_time = time;
            attend = true;

            // Remove profit from other nodes of the block
            for (auto k : graph->nodes_per_block[block])
                node_profit[k] -= cases;
        }
    }

    return attend;
}

int WarmStart::bfs_first_profit(Graph *graph, int i, float &available_time,
                                vector<vector<bool>> &used_arcs, vector<float> &node_profit,
                                vector<pair<int, int>> &dfs_arcs)
{
    int s, j, n = graph->getN();
    vector<bool> visited = vector<bool>(n, false);
    vector<int> stack = vector<int>(), pred = vector<int>(n, -1);
    vector<float> dist = vector<float>(n, 0);
    dfs_arcs = vector<pair<int, int>>();

    stack.push_back(i);
    visited[i] = true, pred[i] = i;
    int next_node = -1;

    while (!stack.empty())
    {
        s = stack.back();
        stack.pop_back();

        if (!visited[s])
            visited[s] = true;

        for (auto *arc : graph->arcs[s])
        {
            j = arc->getD();
            if (j >= n || pred[s] != j)
                continue;

            if (!used_arcs[s][j] && !visited[j])
            {
                stack.push_back(j);
                pred[j] = s, dist[j] = dist[s] + arc->getLength();

                if (node_profit[j] > 0 && available_time > dist[j])
                {
                    next_node = j;
                    stack.clear();
                    break;
                }
            }
        }
    }

    if (next_node != -1)
    {
        s = next_node;
        while (s != i)
        {
            dfs_arcs.push_back(make_pair(pred[s], s));
            used_arcs[pred[s]][s] = true;
            s = pred[s];
        }
        available_time -= dist[next_node];
        reverse(dfs_arcs.begin(), dfs_arcs.end());
    }
    return next_node;
}

double WarmStart::compute_solution(Graph *graph, int max_time, vector<pair<int, int>> &x, vector<pair<int, int>> &y)
{
    // Initial infos
    int i, j, n = graph->getN();
    float available_time = max_time;
    float best_profit, of = 0.0;
    Arc *aux_arc;
    x = vector<pair<int, int>>();
    y = vector<pair<int, int>>();
    vector<bool> serviced = vector<bool>(graph->getB(), false);

    // Compute node profit
    vector<float> node_profit = vector<float>(n + 1, 0);
    vector<int> degree = vector<int>(n + 1, 0);
    vector<vector<bool>> used_arcs = vector<vector<bool>>(n + 1, vector<bool>(n + 1, false));

    for (auto node_pair : graph->nodes)
    {
        i = node_pair.first;
        for (auto block : node_pair.second)
            if (block != -1)
                node_profit[i] += graph->cases_per_block[block];
    }

    // Create greedy route
    i = n;
    while (available_time > 0)
    {
        best_profit = 0;
        for (auto *arc : graph->arcs[i])
            if (node_profit[arc->getD()] > best_profit)
                best_profit = node_profit[arc->getD()], aux_arc = arc;

        if (best_profit <= 0)
        {
            vector<pair<int, int>> bfs_arcs;
            int next_node = WarmStart::bfs_first_profit(graph, i, available_time, used_arcs, node_profit, bfs_arcs);

            if (next_node != -1)
            {
                bool attend = WarmStart::attend_max_blocks(graph, next_node, available_time, max_time, of, node_profit, serviced, y);

                if (attend)
                    x.insert(x.end(), bfs_arcs.begin(), bfs_arcs.end());
                if (node_profit[next_node] > 0)
                    break;
                else
                    node_profit[next_node] = 0, i = next_node;
            }
            else
                break;
        }
        else
        {
            j = aux_arc->getD();

            // Check the use of the arc
            available_time -= aux_arc->getLength();

            if (available_time <= 0)
                break;

            bool attend = WarmStart::attend_max_blocks(graph, j, available_time, max_time, of, node_profit, serviced, y);
            if (attend)
            {
                x.push_back(make_pair(i, j));
                used_arcs[i][j] = true;
            }
            if (node_profit[j] > 0)
                break;
            else
                node_profit[j] = 0, i = j;
        }
    }

    // Add the return to the dummy depot
    if (!x.empty())
    {
        auto last_arc = x.back();
        x.push_back(make_pair(last_arc.second, n));
    }
    else
    {
        x.push_back(make_pair(n, 0));
        x.push_back(make_pair(0, n));
    }

    // Compute route time
    float route_time = 0.0;
    vector<int> y_line = vector<int>(), time = vector<int>();
    vector<double> cases = vector<double>();
    set<int> blocks = set<int>();

    for (auto pair : x)
    {
        i = pair.first, j = pair.second;
        auto arc = graph->getArc(i, j);
        route_time += arc->getLength();

        for (auto b : graph->nodes[i].second)
            if (b != -1)
                blocks.insert(b);
    }

    graph->populateKnapsackVectors(blocks, cases, time);
    if (cases.empty() || blocks.empty())
        return of;

    double knapsack_profit = graph->knapsack(y_line, cases, time, max_time - route_time);

    y = vector<pair<int, int>>();
    for (auto block_idx : y_line)
    {
        set<int>::iterator it = blocks.begin();
        if (it == blocks.end())
            break;
        std::advance(it, block_idx);
        int block = *it;

        bool found = false;
        for (auto node : graph->nodes_per_block[block])
        {
            for (auto pair : x)
            {
                i = pair.first, j = pair.second;
                if (i == node)
                {
                    y.push_back(make_pair(i, block));
                    found = true;
                    break;
                }
                if (j == node)
                {
                    y.push_back(make_pair(j, block));
                    found = true;
                    break;
                }
            }
            if (found)
                break;
        }
    }

    // cout << "Knapsack profit: " << knapsack_profit << " | Real OF: " << of << endl;

    return of;
}