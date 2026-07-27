//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_LAGRANGEAN_H
#define DPARP_LAGRANGEAN_H

#include "../classes/Input.hpp"
#include "../common/BoostLibrary.hpp"
#include "../common/Knapsack.hpp"
#include "../exact/DeterministicModelWalkBarrierMethod.hpp"
#include "GreedyHeuristic.hpp"
#include "gurobi_c++.h"
#include <vector>

class Lagrangean {
    Input *input;
    double mult_time, UB, LB, initial_LB, initial_UB;
    vector<double> mult_conn;
    int num_lazy_cuts, num_frac_cuts, T;
    bool is_feasible;
    double curr_route_time = 0.0, runtime = 0;
    BoostLibrary *boost;
    GreedyHeuristic *greedyHeuristic;

  public:
    explicit Lagrangean(Input *input);

    int lagrangean_relax(string output_file, double lambda, int improve_iters, double reduction_factor, bool use_heuristic, bool use_barrier_method);

    int bestAttendFromRoute(map<int_pair, int> &x, vector<int> &y);

    double solve_ppl(map<pair<int, int>, int> &x, vector<int> &y);

    pair<int, double> runSolverERCSPP(map<pair<int, int>, int> &x);

    pair<int, double> runSHPRC(map<int_pair, int> &x);

    void getGradientConnection(vector<double> &gradient_lambda, map<pair<int, int>, int> x, vector<int> y);

    int getGradientTime(const map<int_pair, int> &x, const vector<int> &y);

    double getNorm(vector<double> &gradient);

    bool isFeasible();

    int getOriginalObjValue(const vector<int> &y);

    void WriteSolution(string output_file, double lambda, int max_iters, int improve_iters, double reduction_factor, int iter) {
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "LB: " << this->LB << endl;
        output << "UB: " << this->UB << endl;
        output << "Initial_LB: " << this->initial_LB << endl;
        output << "Initial_UB: " << this->initial_UB << endl;
        output << "Lambda: " << lambda << endl;
        output << "Max_Iter: " << max_iters << endl;
        output << "Iterations: " << iter << endl;
        output << "Improve_Iter: " << improve_iters << endl;
        output << "Reduction_factor: " << reduction_factor << endl;
        output << "Runtime: " << this->runtime << endl;
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };
};

#endif // DPARP_MODEL_H
