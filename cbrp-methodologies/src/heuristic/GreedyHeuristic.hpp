//
// Created by carlos on 24/07/24.
//

#ifndef DPARP_GREEDYHEURISTIC_H
#define DPARP_GREEDYHEURISTIC_H

#include "../classes/Input.hpp"
#include "../classes/Parameters.hpp"
#include "../classes/Solution.hpp"
#include "../common/BlockConnection.hpp"
#include "../common/Knapsack.hpp"

class GreedyHeuristic {
    Input *input;
    vector<vector<pair<int, int>>> y;
    vector<pair<int, int>> x;
    double objective_value = 0;

    pair<double, double> getBlockSecondStageProfitAvg(const vector<Scenario> &scenarios, int b) {
        double profit = 0;
        for (int s = 0; s < this->input->getS(); s++)
            profit += (input->getAlpha() * input->getScenario(s)->getProbability() * input->getScenario(s)->getCasesPerBlock(b));
        return make_pair((profit / this->input->getS()), profit);
    };

    double getBlockSecondStageProfitSum(const vector<Scenario> &scenarios, int b) {
        double profit = 0;
        for (int s = 0; s < this->input->getS(); s++)
            profit += (input->getAlpha() * input->getScenario(s)->getProbability() * input->getScenario(s)->getCasesPerBlock(b));
        return profit;
    };

  public:
    GreedyHeuristic() = default;

    explicit GreedyHeuristic(Input *input);

    double SolveScenario(const vector<double> &cases, const vector<int> &time, int T, vector<int> &y,
                         Graph *graph = nullptr, BlockConnection *bc = nullptr, ShortestPath *sp = nullptr);

    Solution Run(double route_time_increase, int max_tries, bool use_avg);

    double BinarySolve(const vector<double> &cases, const vector<int> &time, int reserved_time, int T, vector<int> &y,
                       Graph *graph = nullptr, BlockConnection *bc = nullptr, ShortestPath *sp = nullptr);

    static double getRealValueOfFirstStageSolution(const vector<int> &y, vector<double> profit) {
        double of = 0;
        for (auto b : y)
            of += profit[b];
        return of;
    };
};

#endif
