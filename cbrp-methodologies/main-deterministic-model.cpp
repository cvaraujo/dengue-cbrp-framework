#include "src/classes/Input.hpp"
#include "src/exact/DeterministicModel.hpp"
#include "src/exact/DeterministicModelWalk.hpp"
#include <string>

int main(int argc, const char *argv[]) {
    string file_graph = argv[1];
    string model = argv[2];
    string result_file = argv[3];
    string model_type = argv[4];
    int T = 1200;
    bool use_preprocessing = bool(atoi(argv[5]));
    bool use_frac_cut = bool(atoi(argv[6]));
    bool use_warm_start = bool(atoi(argv[7]));
    bool is_mtz_walk = (model_type == "WALK" && model == "MTZ");
    int default_vel = 20, neblize_vel = 10;
    double alpha = 0.8;

    auto *input = new Input(file_graph, "", use_preprocessing, true, is_mtz_walk, default_vel, neblize_vel, T, alpha);
    Solution sol;
    if (model_type == "TRAIL" || is_mtz_walk) {
        cout << "Running Deterministic Model Trail" << endl;
        auto *dm = new DeterministicModel(input);
        sol = dm->Run(use_warm_start, "3600", model, use_frac_cut);
    } else {
        cout << "Running Deterministic Model Walk" << endl;
        auto *dm = new DeterministicModelWalk(input);
        sol = dm->Run(use_warm_start, "3600", model, use_frac_cut);
    }

    sol.WriteDeterministicSolution(result_file);
    return 0;
}
