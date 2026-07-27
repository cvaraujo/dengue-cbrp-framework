#ifndef MULTISTART_HPP
#define MULTISTART_HPP

#include "../../classes/Input.hpp"
#include "../../classes/Solution.hpp"
#include "../../heuristic/GreedyHeuristic.hpp"
#include "LocalSearch.hpp"
#include <algorithm>
#include <chrono>
#include <random>

enum StrategyType {
    PURE_CURRENT,
    SIM_ACC_CASES,
    SIM_INCIDENCE,
    FULL_COMBINED,
    BIASED_CURRENT,
    BIASED_FULL
};

struct CandidateResult {
    vector<int> blocks;
    double deterministic_of = 0.0;
    double stochastic_of = 0.0;
    double tiebreak_of = 0.0;
};

class MultiStart {
    Input *input;
    vector<double> cases_per_block_prop, sim_acc_cases_prop, sim_incidence_prop;
    static constexpr int DEFAULT_MAX_ITERATIONS = 30;

  private:
    void SaveCasesPerBlockProportions() {
        Graph *graph = input->getGraph();
        int B = graph->getB();
        vector<double> cases = graph->getCasesPerBlock();
        double total_cases = accumulate(cases.begin(), cases.end(), 0.0);
        if (total_cases <= 0.0)
            return;

        for (int b = 0; b < B; b++)
            cases_per_block_prop[b] = cases[b] / total_cases;
    }

    void SaveSimheuristicProportions() {
        Graph *graph = input->getGraph();
        int B = graph->getB();
        double total_acc_cases = 0.0, total_incidence = 0.0;

        for (int b = 0; b < B; b++) {
            total_acc_cases += input->getSimheuristicBlockAccCases(b);
            total_incidence += input->getSimheuristicBlockIncidence(b);
        }

        for (int b = 0; b < B; b++) {
            sim_acc_cases_prop[b] = (total_acc_cases > 0.0)
                                        ? input->getSimheuristicBlockAccCases(b) / total_acc_cases
                                        : 0.0;
            sim_incidence_prop[b] = (total_incidence > 0.0)
                                        ? input->getSimheuristicBlockIncidence(b) / total_incidence
                                        : 0.0;
        }
    }

    vector<StrategyType> GetActiveStrategies() {
        vector<StrategyType> strategies = {PURE_CURRENT};
        bool has_scenarios = input->getS() > 0;

        if (has_scenarios) {
            strategies.push_back(SIM_ACC_CASES);
            strategies.push_back(SIM_INCIDENCE);
            strategies.push_back(FULL_COMBINED);
        }

        strategies.push_back(BIASED_CURRENT);
        if (has_scenarios)
            strategies.push_back(BIASED_FULL);

        return strategies;
    }

    vector<double> BuildProfitVector(StrategyType strategy, int B, Graph *graph, mt19937 &gen) {
        vector<double> profit(B, 0.0);
        gamma_distribution<double> gamma_a(2.0, 1.0);
        gamma_distribution<double> gamma_b(5.0, 1.0);
        constexpr double PERTURBATION = 0.3;

        switch (strategy) {

        case PURE_CURRENT: {
            for (int b = 0; b < B; b++) {
                profit[b] = graph->getCasesPerBlock(b);
                if (profit[b] <= 0.0 && input->getS() > 0)
                    profit[b] = sim_acc_cases_prop[b] * 0.001;
            }
            break;
        }

        case SIM_ACC_CASES: {
            for (int b = 0; b < B; b++)
                profit[b] = sim_acc_cases_prop[b];
            break;
        }

        case SIM_INCIDENCE: {
            for (int b = 0; b < B; b++)
                profit[b] = sim_incidence_prop[b];
            break;
        }

        case FULL_COMBINED: {
            for (int b = 0; b < B; b++)
                profit[b] = graph->getCasesPerBlock(b) + sim_incidence_prop[b];
            break;
        }

        case BIASED_CURRENT: {
            vector<double> cpb = graph->getCasesPerBlock();
            double max_val = *max_element(cpb.begin(), cpb.end());
            double scale = PERTURBATION * max(max_val, 1.0);
            for (int b = 0; b < B; b++) {
                double xa = gamma_a(gen), xb = gamma_b(gen);
                double beta_sample = xa / (xa + xb);
                profit[b] = graph->getCasesPerBlock(b) + beta_sample * scale;
            }
            break;
        }

        case BIASED_FULL: {
            double max_val = 0.0;
            for (int b = 0; b < B; b++)
                max_val = max(max_val,
                              graph->getCasesPerBlock(b) + sim_incidence_prop[b]);
            double scale = PERTURBATION * max(max_val, 1.0);
            for (int b = 0; b < B; b++) {
                double xa = gamma_a(gen), xb = gamma_b(gen);
                double beta_sample = xa / (xa + xb);
                profit[b] = graph->getCasesPerBlock(b) + sim_incidence_prop[b] +
                            beta_sample * scale;
            }
            break;
        }
        }

        return profit;
    }

    static void PerturbProfitVector(vector<double> &profit, mt19937 &gen, double intensity) {
        if (intensity <= 0.0)
            return;
        double max_val = *max_element(profit.begin(), profit.end());
        double additive_base = intensity * 0.05 * max(max_val, 1.0);
        normal_distribution<double> mult_noise(0.0, intensity);
        uniform_real_distribution<double> add_noise(0.0, additive_base);
        for (auto &p : profit)
            p = p * exp(mult_noise(gen)) + add_noise(gen);
    }

    static bool IsBetterCandidate(const CandidateResult &a, const CandidateResult &b) {
        if (a.stochastic_of != b.stochastic_of)
            return a.stochastic_of > b.stochastic_of;
        if (a.tiebreak_of != b.tiebreak_of)
            return a.tiebreak_of > b.tiebreak_of;
        return a.deterministic_of > b.deterministic_of;
    }

    static CandidateResult BuildAndEvaluateSolution(Input *input, vector<double> &profit, const vector<int> &time_per_block, int T, int B, mt19937 &gen) {
        GreedyHeuristic greedy(input);
        vector<int> y;
        y.reserve(B);

        auto g0 = std::chrono::steady_clock::now();
        greedy.SolveScenario(profit, time_per_block, T, y);
        auto g1 = std::chrono::steady_clock::now();
        long greedy_ms = std::chrono::duration_cast<std::chrono::milliseconds>(g1 - g0).count();
        if (greedy_ms > 100)
            std::cout << "    [B&E] Greedy: " << greedy_ms << "ms blocks=" << y.size() << std::endl
                      << std::flush;

        if (y.empty())
            return {};

        auto *route = new Route(input, y);
        auto ls0 = std::chrono::steady_clock::now();
        LocalSearch::RunLocalSearch(input, route, profit);
        auto ls1 = std::chrono::steady_clock::now();
        long ls_ms = std::chrono::duration_cast<std::chrono::milliseconds>(ls1 - ls0).count();
        if (ls_ms > 100)
            std::cout << "    [B&E] LocalSearch: " << ls_ms << "ms" << std::endl
                      << std::flush;

        vector<int> final_blocks = route->getSequenceOfAttendingBlocks();
        Graph *graph = input->getGraph();
        int S = input->getS();
        double alpha = input->getAlpha();
        double det_of = 0.0, stoch_of = 0.0, tiebreak_of = 0.0;

        vector<int> sampled_scenarios;
        if (S > 0) {
            int sample_size = max(1, static_cast<int>(S * 0.3));
            vector<int> all_scenarios(S);
            iota(all_scenarios.begin(), all_scenarios.end(), 0);
            shuffle(all_scenarios.begin(), all_scenarios.end(), gen);
            sampled_scenarios.assign(all_scenarios.begin(), all_scenarios.begin() + sample_size);
        }

        for (int b : final_blocks) {
            double real_cases = graph->getCasesPerBlock(b);
            det_of += real_cases;

            double avg_scenario_cases = 0.0;
            if (!sampled_scenarios.empty()) {
                for (int s : sampled_scenarios)
                    avg_scenario_cases += input->getCasesFromScenarioBlock(s, b);
                avg_scenario_cases /= static_cast<double>(sampled_scenarios.size());
            }
            stoch_of += real_cases + alpha * avg_scenario_cases;

            if (real_cases <= 0.0) {
                for (int s : sampled_scenarios)
                    tiebreak_of += input->getCasesFromScenarioBlock(s, b);
            }
        }

        delete route;
        return {final_blocks, det_of, stoch_of, tiebreak_of};
    }

  public:
    explicit MultiStart(Input *input) {
        this->input = input;
        int B = input->getGraph()->getB();
        cases_per_block_prop = vector<double>(B, 0.0);
        sim_acc_cases_prop = vector<double>(B, 0.0);
        sim_incidence_prop = vector<double>(B, 0.0);
    }

    ~MultiStart() = default;

    Solution *GenerateNewSolution(const string &objective_type, int max_iterations = DEFAULT_MAX_ITERATIONS) {
        Graph *graph = input->getGraph();
        int T = input->getT(), B = graph->getB();
        vector<int> time_per_block = graph->getTimePerBlock();

        std::cout << "[MultiStart] S=" << input->getS() << " B=" << B << " T=" << T
                  << " max_iter=" << max_iterations << std::endl
                  << std::flush;

        SaveCasesPerBlockProportions();
        if (input->getS() > 0)
            SaveSimheuristicProportions();

        vector<StrategyType> strategies = GetActiveStrategies();
        int num_strategies = static_cast<int>(strategies.size());
        std::cout << "[MultiStart] Strategies: " << num_strategies << std::endl
                  << std::flush;
        random_device rd;
        mt19937 gen(rd());

        CandidateResult best_candidate;
        int best_iter = -1;
        int iter_count = 0;
        int total_iters = max(max_iterations, num_strategies);

        // Phase 1: one unperturbed baseline per strategy
        for (int i = 0; i < num_strategies; i++, iter_count++) {
            std::cout << "[MultiStart] Baseline " << i << "/" << num_strategies
                      << " type=" << strategies[i] << " ..." << std::flush;
            auto t0 = std::chrono::steady_clock::now();

            vector<double> profit = BuildProfitVector(strategies[i], B, graph, gen);
            auto candidate = BuildAndEvaluateSolution(input, profit, time_per_block, T, B, gen);

            auto t1 = std::chrono::steady_clock::now();
            std::cout << " " << std::chrono::duration_cast<std::chrono::milliseconds>(t1 - t0).count() << "ms"
                      << " blocks=" << candidate.blocks.size()
                      << " stoch_of=" << candidate.stochastic_of
                      << " det_of=" << candidate.deterministic_of << std::endl
                      << std::flush;

            if (!candidate.blocks.empty() &&
                (best_iter == -1 || IsBetterCandidate(candidate, best_candidate))) {
                best_candidate = candidate;
                best_iter = iter_count;
            }
        }

        // Phase 2: perturbed random iterations for diversity
        int remaining = total_iters - num_strategies;
        if (remaining > 0) {
            std::cout << "[MultiStart] Phase 2: " << remaining << " perturbed iterations" << std::endl
                      << std::flush;

            uniform_int_distribution<int> strat_dist(0, num_strategies - 1);
            uniform_real_distribution<double> intensity_dist(0.15, 0.80);

            for (int r = 0; r < remaining; r++, iter_count++) {
                StrategyType strategy = strategies[strat_dist(gen)];
                double intensity = intensity_dist(gen);

                vector<double> profit = BuildProfitVector(strategy, B, graph, gen);
                PerturbProfitVector(profit, gen, intensity);

                auto candidate = BuildAndEvaluateSolution(input, profit, time_per_block, T, B, gen);

                if (!candidate.blocks.empty() &&
                    (best_iter == -1 || IsBetterCandidate(candidate, best_candidate))) {
                    best_candidate = candidate;
                    best_iter = iter_count;
                    std::cout << "[MultiStart] New best at iter " << iter_count
                              << " strategy=" << strategy << " intensity=" << intensity
                              << " stoch_of=" << candidate.stochastic_of
                              << " det_of=" << candidate.deterministic_of << std::endl
                              << std::flush;
                }
            }
        }

        std::cout << "[MultiStart] Done. Best at iter " << best_iter
                  << " stoch_of=" << best_candidate.stochastic_of
                  << " det_of=" << best_candidate.deterministic_of
                  << " blocks=" << best_candidate.blocks.size() << std::endl
                  << std::flush;

        if (best_iter == -1)
            return new Solution(input);

        auto *solution = new Solution(input);
        auto *route = new Route(input, best_candidate.blocks);
        solution->AddScenarioSolution(0, route, best_candidate.deterministic_of);
        return solution;
    };
};

#endif
