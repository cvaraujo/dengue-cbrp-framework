#ifndef DPARP_SCENARIO_H
#define DPARP_SCENARIO_H

#include "Parameters.hpp"

class Scenario {
    double probability = 0.0;
    vector<double> cases_per_block;

  public:
    Scenario(double probability, vector<double> cases_per_block) {
        this->probability = probability;
        this->cases_per_block = std::move(cases_per_block);
    }

    Scenario() = default;

    void setCase2Block(int block, double cases) { this->cases_per_block[block] = cases; };

    [[nodiscard]] double getCasesPerBlock(int block) const {
        if (block < int(this->cases_per_block.size()))
            return this->cases_per_block[block];
        return 0.0;
    };

    void setCasesPerBlock(vector<double> cases) { this->cases_per_block = std::move(cases); };

    [[nodiscard]] const vector<double> &getCases() const { return cases_per_block; }

    [[nodiscard]] double getProbability() const { return this->probability; };

    void setProbability(double prob) { this->probability = prob; };
};

#endif
