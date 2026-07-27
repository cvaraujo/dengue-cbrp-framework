#include "src/classes/Input.hpp"
#include "src/heuristic/metaheuristics/SimulatedAnnealing.hpp"
#include "src/heuristic/stochastic/StartSolution.hpp"
#include <chrono>
#include <string>

int main(int argc, const char *argv[]) {
    random_device rd; // seed
    double temperature = 5.0, temperature_max = 500, alpha_sa = 1.25;
    int max_iters_sa = 100;
    string delta_type = "moderate";
    bool first_improve;
    string file_graph = argv[1];
    string file_scenarios = argv[2];
    string result_file = argv[3];
    double alpha = atof(argv[4]);
    int T = 1200;
    temperature = atof(argv[5]);
    temperature_max = atof(argv[6]);
    alpha_sa = atof(argv[7]);
    max_iters_sa = atoi(argv[8]);
    delta_type = argv[9];
    first_improve = atoi(argv[10]);
    bool use_preprocessing = atoi(argv[11]);
    int default_vel = 20, neblize_vel = 10;

    Input *input = new Input(file_graph, file_scenarios, use_preprocessing, false, false, default_vel, neblize_vel, T, alpha);
    Solution sol = StartSolution::CreateStartSolution(input);

    SimulatedAnnealing *sa = new SimulatedAnnealing(temperature, temperature_max, alpha_sa, max_iters_sa, delta_type, first_improve);
    auto start = std::chrono::high_resolution_clock::now();
    Solution *new_sol = sa->Run(input, sol, rd);
    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> duration = end - start;
    std::cout << "Execution time: " << duration.count() << " seconds\n";
    new_sol->setRuntime(duration.count());
    new_sol->WriteStochasticHeuristicSolution(result_file);

    delete new_sol;
    delete sa;
    delete input;
    return 0;
}
