//
// Created by carlos on 09/11/24.
//

#ifndef DPARP_LOCALSEARCH_H
#define DPARP_LOCALSEARCH_H

#include "../../classes/Input.hpp"
#include "../../classes/Solution.hpp"
#include <chrono>

class LocalSearch {

  private:
    static bool ImproveRouteTime(Route *current_route, Input *input) {
        vector<int> route_vec = current_route->getRoute();
        bool has_improved = false;
        int time_diff;

        while (true) {
            time_diff = ApplyNodeSwap(input, route_vec);

            if (time_diff <= 0)
                break;

            has_improved = true;
            current_route->ChangeRouteTime(-time_diff);
        }

        if (has_improved) {
            current_route->setRoute(route_vec);
            set<int> route_blocks = current_route->getRouteBlocks();
            vector<int> att_blocks;
            att_blocks.reserve(route_blocks.size());

            // Get only attended blocks
            for (int b : route_blocks)
                if (current_route->IsBlockAttended(b))
                    att_blocks.push_back(b);

            // Generate key
            BlockConnection *bc = input->getBlockConnection();
            bc->UpdateBestKnowBlockConnection(att_blocks, route_vec, current_route->getTimeRoute());
        }

        return has_improved;
    }

    static int ApplyNodeSwap(Input *input, vector<int> &route) {
        int i, j, N = int(route.size()), best_time_improve = 0;
        int curr_time_i, new_time_i, curr_time_j, new_time_j, time_diff;
        int best_i = -1, best_j = -1;

        // Only one node of the route is used, no improve is available
        if (N <= 4)
            return best_time_improve;

        for (i = 1; i < N; i++) {
            curr_time_i = getRouteConnectionTime(input, route[i - 1], route[i], route[i + 1]);

            for (j = i + 2; j < N - 2; j++) {
                curr_time_j = getRouteConnectionTime(input, route[j - 1], route[j], route[j + 1]);
                new_time_j = getRouteConnectionTime(input, route[i - 1], route[j], route[i + 1]);
                new_time_i = getRouteConnectionTime(input, route[j - 1], route[i], route[j + 1]);

                time_diff = (curr_time_i + curr_time_j) - (new_time_i + new_time_j);

                if (time_diff > best_time_improve) {
                    best_time_improve = time_diff;
                    best_i = i, best_j = j;
                }
            }
        }
        if (best_i != best_j)
            std::swap(route[best_i], route[best_j]);
        return best_time_improve;
    }

    static int getRouteConnectionTime(Input *input, int prev, int node, int next) {
        return input->getArcTime(prev, node) + input->getArcTime(node, next);
    }

    static int TryInsertMoreProfitableBlock(Input *input, Route *route, vector<double> &profit_per_block) {
        auto *graph = input->getGraph();
        int B = graph->getB();
        int delta = 0;

        // Get remaining blocks
        vector<int> not_attended_blocks;
        not_attended_blocks.reserve(B);
        for (int b = 0; b < B; b++) {
            if (!route->IsBlockAttended(b))
                not_attended_blocks.push_back(b);
        }

        if (not_attended_blocks.empty())
            return delta;

        int best_block;
        double best_profit;
        while (true) {
            best_block = -1;
            best_profit = -1.0;
            for (int b : not_attended_blocks) {
                if (profit_per_block[b] >= best_profit && route->IsBlockInsertionFactible(b)) {
                    best_block = b;
                    best_profit = profit_per_block[b];
                }
            }

            if (best_block == -1)
                return delta;

            route->AddBlockToRoute(best_block, true);
            not_attended_blocks.erase(find(not_attended_blocks.begin(), not_attended_blocks.end(), best_block));
            delta += int(graph->getCasesPerBlock(best_block));
        }
    }

    static bool isSwapFeasible(Route *route, int b_remove, int b_insert) {
        if (route->IsBlockInRoute(b_insert)) {
            return route->IsSwapFeasible(b_remove, b_insert);
        } else {
            return route->IsOutSwapFeasible(b_remove, b_insert);
        }
    }

    static double getDeltaSwap(int b_remove, int b_insert, vector<double> &profit_per_block) {
        return profit_per_block[b_insert] - profit_per_block[b_remove];
    }

    static int getRealCasesDelta(Graph *graph, int b_remove, int b_insert) {
        return int(graph->getCasesPerBlock(b_insert) - graph->getCasesPerBlock(b_remove));
    }

    static int TryApplyBestSwap(Input *input, Route *route, vector<double> &profit_per_block) {
        auto *Graph = input->getGraph();
        int total_delta = 0, B = Graph->getB();
        double best_delta;
        int_pair best_swap;
        int swap_iters = 0;
        constexpr int MAX_SWAP_ITERS = 500;

        while (true) {
            best_delta = -1.0;
            best_swap = {0, 0};
            for (int b_remove : route->getSequenceOfAttendingBlocks()) {
                for (int b_insert = 0; b_insert < B; b_insert++) {
                    if (route->IsBlockAttended(b_insert))
                        continue;

                    if (isSwapFeasible(route, b_remove, b_insert)) {
                        double delta = getDeltaSwap(b_remove, b_insert, profit_per_block);
                        if (delta >= best_delta) {
                            best_swap = {b_remove, b_insert};
                            best_delta = delta;
                        }
                    }
                }
            }

            if (best_delta <= 0.0)
                return total_delta;

            if (++swap_iters > MAX_SWAP_ITERS) {
                std::cout << "      [TrySwap] ABORT after " << swap_iters
                          << " iters, best_delta=" << best_delta
                          << " swap=(" << best_swap.first << "→" << best_swap.second << ")"
                          << " attended=" << route->getSequenceOfAttendingBlocks().size()
                          << std::endl << std::flush;
                return total_delta;
            }

            int b_remove = best_swap.first, b_insert = best_swap.second;
            route->GeneralSwapBlocks(b_remove, b_insert);
            total_delta += getRealCasesDelta(Graph, b_remove, b_insert);
        }

        return total_delta;
    }

  public:
    static int RunLocalSearch(Input *input, Route *route, vector<double> &profit_per_block) {
        int delta = 0;

        auto t0 = std::chrono::steady_clock::now();
        bool improve_route = ImproveRouteTime(route, input);
        auto t1 = std::chrono::steady_clock::now();
        long irt_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t1 - t0).count();

        if (improve_route) {
            delta += TryInsertMoreProfitableBlock(input, route, profit_per_block);
            auto t2 = std::chrono::steady_clock::now();
            long tip_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t2 - t1).count();
            if (tip_ms > 100)
                std::cout << "      [LS] TryInsert: " << tip_ms << "ms" << std::endl << std::flush;
            t1 = t2;
        }

        delta += TryApplyBestSwap(input, route, profit_per_block);
        auto t3 = std::chrono::steady_clock::now();
        long swap_ms = std::chrono::duration_cast<std::chrono::milliseconds>(t3 - t1).count();
        if (swap_ms > 100)
            std::cout << "      [LS] TrySwap: " << swap_ms << "ms" << std::endl << std::flush;

        long total = std::chrono::duration_cast<std::chrono::milliseconds>(t3 - t0).count();
        if (total > 200)
            std::cout << "      [LS] TOTAL: " << total << "ms (IRT=" << irt_ms << ")" << std::endl << std::flush;

        return delta;
    }
};

#endif
