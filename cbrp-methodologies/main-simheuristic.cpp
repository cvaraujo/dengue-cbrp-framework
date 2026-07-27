#include "src/classes/Input.hpp"
#include "src/simheuristic/simheuristic.hpp"
#include <string>

int main(int argc, const char *argv[]) {
    string file_graph = argv[1];
    int T = atoi(argv[2]);
    double alpha = atof(argv[3]);
    string conn_address = argv[4];
    int default_vel = 20, neblize_vel = 10;

    auto *input = new Input(file_graph, "", default_vel, neblize_vel, T, alpha);
    Simheuristic simHeu = Simheuristic(input, conn_address);
    simHeu.Run();
}
