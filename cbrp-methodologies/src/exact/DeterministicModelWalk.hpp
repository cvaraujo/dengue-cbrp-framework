//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_DETERMINISTIC_MODELWALK_H
#define DPARP_DETERMINISTIC_MODELWALK_H

#include "../classes/Parameters.hpp"
#include "../classes/Input.hpp"
#include "../classes/Solution.hpp"
#include <gurobi_c++.h>

using namespace lemon;

class DeterministicModelWalk
{
  Input *input;
  GRBEnv env = GRBEnv();
  GRBModel model = GRBModel(env);
  vector<vector<GRBVar>> x;
  vector<GRBVar> y;
  int num_lazy_cuts, num_frac_cuts;

public:
  DeterministicModelWalk(Input *input)
  {
    if (input != nullptr)
      this->input = input;
    else
      exit(EXIT_FAILURE);
  }

  ~DeterministicModelWalk()
  {
    x.clear(), y.clear();
    model.terminate();
  }

  Solution getSolution();

  Solution Run(bool use_warm_start, string time_limit, string model, bool use_cuts);

  void solveExponential(string time_limit, bool frac_cut);

  void objectiveFunction();

  void createVariables();

  void initModel(string model);

  void artificialNodes();

  void flowConservation();

  void attendingPath();

  void timeConstraint();

  bool checkSolution();
};

#endif // DPARP_MODEL_H
