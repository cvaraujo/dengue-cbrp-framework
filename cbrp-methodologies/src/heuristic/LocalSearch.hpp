//
// Created by carlos on 09/11/24.
//

#ifndef DPARP_LOCALSEARCH_H
#define DPARP_LOCALSEARCH_H

#include "../classes/Parameters.hpp"
#include "../classes/Input.hpp"
#include "../classes/Solution.hpp"
#include "../common/Knapsack.hpp"
#include "../common/BlockConnection.hpp"

class LocalSearch
{
    Input *input;
    Solution *bestSolution, *current_solution;

public:
    LocalSearch(Input *input, Solution *initial_solution)
    {
        this->input = input;
        this->bestSolution = initial_solution;
        this->current_solution = initial_solution;
    };

    ~LocalSearch() { delete bestSolution, current_solution; }

    Solution *getBestSolution() { return bestSolution; }

    void Run2Opt(int i, int j);
};

#endif
