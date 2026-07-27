//
// Created by carlos on 07/12/24.
//

#ifndef DPARP_STOCHASTIC_STARTSOLUTION_H
#define DPARP_STOCHASTIC_STARTSOLUTION_H

#include "../../classes/Input.hpp"
#include "../../classes/Solution.hpp"
#include "../GreedyHeuristic.hpp"
#include "Utils.hpp"

class StartSolution {

  public:
    static Solution CreateStartSolution(Input *input) {
#ifndef Silence
        cout << "[*] Creating Start Solution..." << endl;
#endif
        Graph *graph = input->getGraph();
        int S = input->getS(), T = input->getT(), B = graph->getB();

        vector<int> y_0 = vector<int>(), y = vector<int>();
        Solution solution = Solution(input);

        // Solving the first stage problem
        GreedyHeuristic greedy_heuristic = GreedyHeuristic(input);

        vector<double> cases_per_block = vector<double>(B, 0);
        vector<int> time_per_block = graph->getTimePerBlock();

        for (int b = 0; b < B; b++)
            cases_per_block[b] = input->getFirstStageProfit(b);

        // Solve first stage
        double of = greedy_heuristic.SolveScenario(cases_per_block, time_per_block, T, y_0);
        Route *route = new Route(input, y_0);
        solution.AddScenarioSolution(0, route, of);

#ifndef Silence
        cout << "[**] First Stage OF = " << of << endl;
#endif

        for (int s = 1; s <= S; s++) {
            y = vector<int>();
            Utils::GetSecondStageCosts(input, s - 1, y_0, cases_per_block);

            Graph *sg = input->getScenarioGraph(s - 1);
            ShortestPath *ssp = input->getScenarioSP(s - 1);
            BlockConnection *sbc = input->getScenarioBCon(s - 1);
            vector<int> sg_time_per_block = sg->getTimePerBlock();

            double scenario_of = input->getScenarioProbability(s - 1) *
                greedy_heuristic.SolveScenario(cases_per_block, sg_time_per_block, T, y, sg, sbc, ssp);
            Route *route = new Route(input, sg, s - 1, y);
            solution.AddScenarioSolution(s, route, scenario_of);
        }

#ifndef Silence
        cout << "[**] Stochastic Start Solution OF: " << solution.getOf() << endl;
#endif
        solution.setStartUB(solution.getOf());
        return solution;
    };
};

#endif
