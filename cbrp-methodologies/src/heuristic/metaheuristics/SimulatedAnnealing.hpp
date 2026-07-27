//
// Created by carlos on 23/04/25
//

#ifndef DPARP_STOCHASTIC_SA_H
#define DPARP_STOCHASTIC_SA_H

#include "../../classes/Input.hpp"
#include "../../classes/Parameters.hpp"
#include "../../classes/Solution.hpp"
#include "../stochastic/LocalSearch.hpp"

class SimulatedAnnealing {

  private:
    double temperature = 5.0, temperature_max = 500, alpha = 1.25;
    int max_iterations = 100;
    string delta_type = "moderate";
    bool first_improve = true;

  public:
    SimulatedAnnealing() = default;

    SimulatedAnnealing(double temperature, double temperature_max, double alpha, int max_iterations, const string &delta_type, bool first_improve) {
        this->temperature = temperature;
        this->temperature_max = temperature_max;
        this->alpha = alpha;
        this->max_iterations = max_iterations;
        this->delta_type = delta_type;
        this->first_improve = first_improve;
    }

    Solution *Run(Input *input, const Solution &solution, random_device &rd) {
        mt19937 gen(rd()); // Mersenne Twister RNG
        uniform_real_distribution<> dis(0.0, 1.0);

        Solution *best_solution = new Solution(solution);
        Solution *current_solution = new Solution(solution);
        LocalSearch *ls = new LocalSearch(input, current_solution);

        Change best_change, curr_change;
        double delta, ap;
        vector<pair<int, int_pair>> curr_swaps, best_swaps;
        double best_of = best_solution->getOf();
        bool best_sol_improved;

        while (temperature < temperature_max) {
            best_sol_improved = false;
            for (int i = 0; i < max_iterations; i++) {
                curr_change = ls->RunDefaultPerturbation(true);
                if (ChangeUtils::isEmpty(curr_change))
                    continue;

                delta = curr_change.delta;
                ap = delta != 0 ? exp((delta * temperature) / best_of) : 0.0;

                // cout << "[*] Delta: " << delta << ", AP: " << ap << endl;
                if (delta > 0 || dis(gen) < ap)
                    current_solution->ApplyChanges(curr_change);

                if (best_solution->getOf() < current_solution->getOf()) {
                    delete best_solution;
                    best_solution = new Solution(*current_solution);
                    best_of = best_solution->getOf();
                    best_sol_improved = true;
                }

                // cout << "[*] Temperature: " << temperature << ", Temp. Max: " << temperature_max << endl;
                // cout << "\t[*] Iteration: " << i << ", BestSol: " << best_solution->getOf() << ", CurrSol: " << current_solution->getOf() << endl;
                // cout << "\t[*] Checking the OF from CurrSol:" << endl;
                double real_of = current_solution->ComputeCurrentSolutionOF();

                if ((current_solution->getOf() - real_of) > EPS) {
                    cout << "\t[!] Difference in the OF: " << real_of << " != " << current_solution->getOf() << endl;
                    exit(EXIT_FAILURE);
                    // getchar();
                }
            }
            if (best_sol_improved) {
                LocalSearch::ImproveSecondStageRoutes(input, best_solution, true);
                delete current_solution;
                current_solution = new Solution(*best_solution);
                ls->setSolution(current_solution);
            } else
                LocalSearch::ImproveSecondStageRoutes(input, current_solution, true);

            // cout << "[*] Checking the best Solution:" << endl;
            best_solution->CheckSolution();
            // cout << "[*] Checking the current Solution:" << endl;
            current_solution->CheckSolution();
            temperature *= alpha;
        }

        ls->PostProcessing(*best_solution);
        delete ls;
        delete current_solution;
        return best_solution;
    };
};

#endif
