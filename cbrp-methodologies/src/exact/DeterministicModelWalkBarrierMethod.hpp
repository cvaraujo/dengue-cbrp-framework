//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_DETERMINISTIC_MODELWALK_BARRIER_METHOD_H
#define DPARP_DETERMINISTIC_MODELWALK_BARRIER_METHOD_H

#include "../classes/Input.hpp"
#include "../classes/Parameters.hpp"
#include "../classes/Solution.hpp"
#include <gurobi_c++.h>

using namespace lemon;

class DeterministicModelWalkBarrier {
    Input *input;
    GRBEnv env = GRBEnv();
    GRBModel model = GRBModel(env);
    vector<vector<GRBVar>> x;
    vector<GRBVar> y;
    int num_lazy_cuts = 0, num_frac_cuts = 0;

  public:
    explicit DeterministicModelWalkBarrier(Input *input) {
        if (input != nullptr)
            this->input = input;
        else
            exit(EXIT_FAILURE);
    }

    ~DeterministicModelWalkBarrier() {
        x.clear(), y.clear();
        model.terminate();
    }

    Solution getSolution();

    void Run(bool use_warm_start, string time_limit, string model, bool use_cuts);

    void solveExponential(string time_limit, bool frac_cut);

    void objectiveFunction();

    void createVariables();

    void initModel(string model);

    void artificialNodes();

    void flowConservation();

    void attendingPath();

    void timeConstraint();

    void compactTimeConstraint();

    double getMultipliers(vector<double> &multipliers);
};

#endif // DPARP_MODEL_H
