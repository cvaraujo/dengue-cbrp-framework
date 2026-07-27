#include "src/classes/Input.hpp"
#include "src/heuristic/GreedyHeuristic.hpp"
#include <string>

int main(int argc, const char *argv[]) {
    string file_graph = argv[1];
    string result_file = argv[2];
    bool use_preprocessing = bool(atoi(argv[3]));
    int T = 1200;
    int default_vel = 20, neblize_vel = 10;
    double alpha = 0.8;

    auto *input = new Input(file_graph, "", use_preprocessing, true, false, default_vel, neblize_vel, T, alpha);
    Graph *graph = input->getGraph();
    int B = graph->getB();
    vector<int> y_0 = vector<int>(), y = vector<int>();
    Solution solution = Solution(input);

    auto start_time = chrono::high_resolution_clock::now();
    // Solving the first stage problem
    GreedyHeuristic greedy_heuristic = GreedyHeuristic(input);

    vector<double> cases_per_block = vector<double>(B, 0);
    vector<int> time_per_block = graph->getTimePerBlock();

    for (int b = 0; b < B; b++)
        cases_per_block[b] = graph->getCasesPerBlock(b);

    // Solve first stage
    double of = greedy_heuristic.SolveScenario(cases_per_block, time_per_block, T, y_0);
    cout << "OF: " << of << endl;
    auto end_time = chrono::high_resolution_clock::now();
    auto duration = chrono::duration_cast<chrono::seconds>(end_time - start_time).count();
    cout << "Duration: " << duration << " seconds" << endl;

    auto route = new Route(input, y_0);
    solution.AddScenarioSolution(0, route, of);
    solution.setRuntime(duration);
    solution.WriteDeterministicFromRouteStructs(result_file);
    return 0;
}
