//
// Created by carlos on 05/01/25
//

#ifndef DPARP_STOCHASTIC_LSEARCH_H
#define DPARP_STOCHASTIC_LSEARCH_H

#include "../../classes/Changes.hpp"
#include "../../classes/Input.hpp"
#include "../../classes/Parameters.hpp"
#include "../../classes/Solution.hpp"
#include "../GreedyHeuristic.hpp"
#include "Utils.hpp"

class LocalSearch {
    struct CompareSecond {
        bool operator()(const int_pair &a, const int_pair &b) const {
            return a.second > b.second; // min-heap based on second
        }
    };

    struct CompareSecondDouble {
        bool operator()(const double_pair &a, const double_pair &b) const {
            return a.second > b.second; // min-heap based on second
        }
    };

  private:
    Input *input;
    Solution *solution;
    string delta_type = "moderate";
    bool use_first_improve = false;

  public:
    LocalSearch(Input *input, Solution *solution) {
        this->input = input;
        this->solution = solution;
    }

    void setSolution(Solution *sol) { this->solution = sol; };

    void RunInRouteSwapImprove();

    double GetWeakDeltaSwapBlocksStartScenario(int b1, int b2);

    double GetUpdatedSecondStageCases(const Scenario *scenario, int block, bool attended_first_stage) {
        double cases = scenario->getCasesPerBlock(block);
        return attended_first_stage ? (1.0 - input->getAlpha()) * cases : cases;
    }

    double GetUpdatedFirstStageCases(int block) {
        return input->getFirstStageProfit(block);
    }

    int GetBestSecondStageOptionIfB1LeaveFSSolution(const Scenario *scenario,
                                                    const Route *f_stage_route,
                                                    const Route *s_stage_route, int b1,
                                                    int b2, int curr_time_change);

    int GetBestSecondStageOptionIfB2EnterFSSolution(Scenario *scenario,
                                                    Route *f_stage_route,
                                                    Route *s_stage_route, int b1,
                                                    int b2, int changed, int curr_time_change);

    double GetModerateDeltaSwapBlocksStartScenario(
        int b1, int b2, vector<pair<int, int_pair>> &second_stage_swaps);

    double GetWeakDeltaInsertBlock(int block);

    double GetWeakDeltaRemoveBlock(int block);

    double GetModerateDeltaInsertBlock(int block, vector<pair<int, int_pair>> &second_stage_swaps);

    double GetModerateDeltaRemoveBlock(int block, vector<pair<int, int_pair>> &second_stage_swaps);

    double GetModerateDeltaOutRouteSwap(int b1, int b2, vector<pair<int, int_pair>> &second_stage_swaps);

    Change ComputeSwapBlocks(bool is_out_route);

    Change ComputeOutRouteSwapBlocksStartScenario();

    static int_pair GetRandomB1NB2(const Route *route, vector<int> &blocks);

    Change SelectRandomSwapBlocks();

    int SelectRandomInsertBlock(bool try_improve_route);

    int_pair GetRandomBlocksFeasibleSwap(Route *route);

    Route *RemoveBlockFromRoute(int route_idx, int block);

    void InsertOutRouteBlock(int route_idx, int block);

    Change RunDefaultPerturbation(bool use_random);

    Change RandomBlockChange();

    double ComputeRandomBlockDiversification(vector<pair<int, int_pair>> &swaps);

    double ComputeRandomBlockIntensification(vector<pair<int, int_pair>> &swaps);

    int SelectTopTimeBlock(bool use_lowest, bool is_remove) {
        // cout << "\t[*] SelectTopTimeBlock" << endl;
        Route *route = this->solution->getRouteFromScenario(0);
        set<int> route_blocks = route->getBlocks();

        if (is_remove) {
            int selec_block = -1, top_time = 0, time;
            for (int b : route_blocks) {
                time = use_lowest ? input->getBlockTime(b) : -input->getBlockTime(b);
                if (time < top_time) {
                    selec_block = b;
                    top_time = time;
                }
            }
            return selec_block;
        }

        priority_queue<int_pair, vector<int_pair>, CompareSecond> pq;
        int block_time = 0;
        for (int b : route_blocks) {
            if (route->IsBlockAttended(b))
                continue;
            block_time = use_lowest ? input->getBlockTime(b) : -input->getBlockTime(b);
            pq.emplace(b, block_time);
        }

        int block = -1;
        while (!pq.empty()) {
            int_pair p = pq.top();
            block = p.first;
            if (route->IsBlockInsertionFactible(block)) {
                return block;
            }
            pq.pop();
        }
        return -1;
    };

    int SelectTopProfitBlock(bool use_lowest, bool is_remove) {
        // cout << "\t[*] SelectTopProfitBlock" << endl;
        Route *route = this->solution->getRouteFromScenario(0);
        set<int> route_blocks = route->getBlocks();

        if (is_remove) {
            int selec_block = -1;
            double top_profit = INF, profit;

            for (int b : route_blocks) {
                profit = input->getFirstStageProfit(b);
                if (profit <= 0)
                    continue;

                profit = use_lowest ? profit : -profit;

                if (profit < top_profit) {
                    selec_block = b;
                    top_profit = profit;
                }
            }
            return selec_block;
        }

        priority_queue<double_pair, vector<double_pair>, CompareSecond> pq;
        double block_profit = 0;
        for (int b : route_blocks) {
            block_profit = input->getFirstStageProfit(b);
            if (block_profit <= 0 || route->IsBlockAttended(b))
                continue;

            block_profit = use_lowest ? block_profit : -block_profit;
            pq.emplace(b, block_profit);
        }

        int block = -1;
        while (!pq.empty()) {
            int_pair p = pq.top();
            block = p.first;

            if (route->IsBlockInsertionFactible(block)) {
                return block;
            }
            pq.pop();
        }
        return -1;
    };

    int SelectTopProportionBlock(bool use_lowest, bool is_remove) {
        // cout << "\t[*] SelectTopProportionBlock" << endl;
        Route *route = this->solution->getRouteFromScenario(0);
        set<int> route_blocks = route->getBlocks();

        if (is_remove) {
            int selec_block = -1;
            double top_proportion = INF, proportion;

            for (int b : route_blocks) {
                proportion = input->getTimeProfitProportion(b);
                if (proportion <= 0)
                    continue;

                proportion = use_lowest ? proportion : -proportion;

                if (proportion < top_proportion) {
                    selec_block = b;
                    top_proportion = proportion;
                }
            }
            return selec_block;
        }

        priority_queue<double_pair, vector<double_pair>, CompareSecond> pq;
        double block_proportion = 0;
        for (int b : route_blocks) {
            block_proportion = input->getTimeProfitProportion(b);
            if (block_proportion <= 0.0 || route->IsBlockAttended(b))
                continue;

            block_proportion = use_lowest ? block_proportion : -block_proportion;
            pq.emplace(b, block_proportion);
        }

        int block = -1;
        while (!pq.empty()) {
            int_pair p = pq.top();
            block = p.first;

            if (route->IsBlockInsertionFactible(block))
                return block;
            pq.pop();
        }
        return -1;
    };

    int SelectRandomRemoveBlock() {
        // cout << "\t[*] SelectRandomRemoveBlock" << endl;
        Route *route = solution->getRouteFromScenario(0);
        vector<int> blocks = route->getSequenceOfAttendingBlocks();
        if (blocks.empty())
            return -1;

        static mt19937 gen(random_device{}());
        uniform_int_distribution<> distrib(0, int(blocks.size()) - 1);
        return blocks[distrib(gen)];
    };

    Change SelectRemoveBlock(int option);

    Change SelectInsertBlock(int option);

    void ImproveRouteTime();

    int ApplyNodeSwap(vector<int> &route);

    int getRouteConnectionTime(int prev, int node, int next);

    void PostProcessing(Solution &sol);

    static void ImproveSecondStageRoutes(Input *input, Solution *sol, bool use_full_replace);
};

#endif
