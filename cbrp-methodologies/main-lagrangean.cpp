#include "src/classes/Input.hpp"
#include "src/heuristic/Lagrangean.hpp"
#include <string>

int main(int argc, const char *argv[]) {
    string file_graph = argv[1];
    string result_file = argv[2];
    bool use_preprocessing = bool(atoi(argv[3]));
    double lambda = 1.5;
    int improve_iters = 50;
    double reduction_factor = 0.95;
    int T = 1200;
    bool use_heuristic = bool(atoi(argv[4]));
    bool use_barrier_method = bool(atoi(argv[5]));
    int default_vel = 20, neblize_vel = 10;
    double alpha = 0.8;

    auto *input = new Input(file_graph, "", use_preprocessing, true, false, default_vel, neblize_vel, T, alpha);
    auto *lagrangean = new Lagrangean(input);
    lagrangean->lagrangean_relax(result_file, lambda, improve_iters, reduction_factor, use_heuristic, use_barrier_method);
    return 0;
}
