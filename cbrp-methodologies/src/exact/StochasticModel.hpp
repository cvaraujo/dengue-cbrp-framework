//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_STOCHASTIC_MODEL_H
#define DPARP_STOCHASTIC_MODEL_H

#include "../classes/Parameters.hpp"
#include "../classes/Input.hpp"
#include "../classes/Solution.hpp"
#include <gurobi_c++.h>

using namespace lemon;
using namespace std;

class StochasticModel
{
  Input *input;
  GRBEnv env = GRBEnv();
  GRBModel model = GRBModel(env);
  vector<vector<GRBVar>> z, y;
  vector<vector<bool>> y_exists, z_exists;
  vector<vector<vector<GRBVar>>> x, t; // indexed as [r][i][j]
  int num_lazy_cuts = 0, num_frac_cuts = 0;

public:
  StochasticModel(Input *input)
  {
    if (input != nullptr)
      this->input = input;
    else
      exit(EXIT_FAILURE);
  }

  ~StochasticModel()
  {
    x.clear(), y.clear(), t.clear(), z.clear();
    model.terminate();
  }

  Solution getSolution();

  Solution Run(bool use_warm_start, string time_limit, string model, bool use_cuts);

  void solveExponential(string time_limit, bool frac_cut);

  void objectiveFunction();

  void createVariables();

  void initModel(string model);

  void zValue();

  void artificialNodes();

  void flowConservation();

  void maxAttending();

  void attendingPath();

  void timeConstraint();

  void compactTimeConstraint();

  void solveCompact(string time_limit);

  bool checkSolution();
};

#endif // DPARP_MODEL_H
