//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_STOCHASTIC_MODEL_WALK_H
#define DPARP_STOCHASTIC_MODEL_WALK_H

#include "../classes/Parameters.hpp"
#include "../classes/Input.hpp"
#include "../classes/Solution.hpp"
#include <gurobi_c++.h>

using namespace lemon;

class StochasticModelWalk
{
  Input *input;
  GRBEnv env = GRBEnv();
  GRBModel model = GRBModel(env);
  vector<vector<vector<GRBVar>>> x; // indexed as [r][i][j]
  vector<vector<GRBVar>> y, z;
  vector<vector<bool>> y_exists, z_exists;
  int num_lazy_cuts, num_frac_cuts;

public:
  StochasticModelWalk(Input *input)
  {
    if (input != nullptr)
      this->input = input;
    else
      exit(EXIT_FAILURE);
  }

  ~StochasticModelWalk()
  {
    x.clear(), y.clear();
    model.terminate();
  }

  Solution getSolution();

  Solution Run(bool use_warm_start, string time_limit, string model, bool use_cuts);

  void solveExponential(string time_limit, bool frac_cut);

  void objectiveFunction();

  void zValue();

  void createVariables();

  void initModel(string model);

  void artificialNodes();

  void flowConservation();

  void attendingPath();

  void timeConstraint();

  bool checkSolution();
};

#endif // DPARP_MODEL_H
