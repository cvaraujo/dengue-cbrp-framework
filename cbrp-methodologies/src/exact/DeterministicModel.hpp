//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_DETERMINISTIC_MODEL_H
#define DPARP_DETERMINISTIC_MODEL_H

#include "../classes/Input.hpp"
#include "../classes/Solution.hpp"
#include <gurobi_c++.h>

using namespace lemon;

class DeterministicModel {
    Input *input;
    GRBEnv env;
    GRBModel model;
    vector<vector<GRBVar>> x, y, t;
    int num_lazy_cuts = 0, num_frac_cuts = 0;

  public:
    explicit DeterministicModel(Input *input)
        : input(nullptr)
        , env()
        , model(env) {
        if (input != nullptr)
            this->input = input;
        else
            exit(EXIT_FAILURE);
    }

    ~DeterministicModel() {
        x.clear();
        y.clear();
        t.clear();
        model.terminate();
    }

    Solution getSolution();

    Solution Run(bool use_warm_start, const string &time_limit, const string &useModel, bool use_cuts);

    void solveExponential(const string &time_limit, bool frac_cut);

    void objectiveFunction();

    void createVariables();

    void initModel(const string &useModel);

    void artificialNodes();

    void flowConservation();

    void maxAttending();

    void attendingPath();

    void timeConstraint();

    void compactTimeConstraint();

    void solveCompact(const string &time_limit);

    bool checkSolution();
};

#endif // DPARP_DETERMINISTIC_MODEL_H
