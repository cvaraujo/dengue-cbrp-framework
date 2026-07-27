#include "src/classes/Input.hpp"
#include "src/exact/StochasticModel.hpp"
#include "src/exact/StochasticModelWalk.hpp"
#include <string>

int main(int argc, const char *argv[]) {
    string file_graph = argv[1];
    string file_scenarios = argv[2];
    string result_file = argv[3];
    string model = argv[4];
    string model_type = argv[5];
    double alpha = atof(argv[6]);
    int T = 1200;
    bool use_preprocessing = bool(atoi(argv[7]));
    bool use_frac_cut = bool(atoi(argv[8]));
    bool use_warm_start = bool(atoi(argv[9]));
    bool is_mtz_walk = (model_type == "WALK" && model == "MTZ");
    int default_vel = 20, neblize_vel = 10;

    Input *input = new Input(file_graph, file_scenarios, use_preprocessing, true, is_mtz_walk, default_vel, neblize_vel, T, alpha);
    Solution sol;
    if (model_type == "TRAIL" || is_mtz_walk) {
        StochasticModel *sm = new StochasticModel(input);
        sol = sm->Run(use_warm_start, "120", model, use_frac_cut);
        delete sm;
    } else {
        StochasticModelWalk *sm = new StochasticModelWalk(input);
        sol = sm->Run(use_warm_start, "120", model, use_frac_cut);
        delete sm;
    }

    sol.WriteStochasticSolution(result_file);
    delete input;
    return 0;
}
