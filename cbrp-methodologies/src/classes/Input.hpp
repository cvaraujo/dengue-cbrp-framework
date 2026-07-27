#ifndef DPARP_INPUT_H
#define DPARP_INPUT_H

#include "../common/BlockConnection.hpp"
#include "../common/ShortestPath.hpp"
#include "Graph.hpp"
#include "Scenario.hpp"

class Input {
  private:
    int S = 0;
    int T = 1200;
    int default_vel = 20;
    int neblize_vel = 10;
    double alpha = 0.8;
    bool preprocessing = false;
    bool is_trail = false;
    bool walk_mtz_model = false;
    Graph *graph = nullptr;
    ShortestPath *sp = nullptr;
    BlockConnection *bc = nullptr;
    vector<Scenario> scenarios;
    vector<double> first_stage_profit;
    vector<double> time_profit_proportion;
    vector<vector<vector<Arc *>>> arcs_in_path;
    vector<vector<int>> arc_length;
    // Per-scenario reduced graphs
    vector<Graph *> scenario_graphs;
    vector<ShortestPath *> scenario_sps;
    vector<BlockConnection *> scenario_bcs;
    // Simheuristic only
    vector<int> simheuristic_scenario_sequence;
    vector<int> simheuristic_block_incidences;
    vector<int> simheuristic_block_acc_cases;

  public:
    Input(Graph *graph, vector<Scenario> scenarios, ShortestPath *sp)
        : graph(graph)
        , scenarios(std::move(scenarios))
        , sp(sp) {}

    Input(const string &file_graph, const string &scenarios_graph, bool preprocessing,
          bool is_trail, bool walk_mtz_model, int default_vel, int neblize_vel,
          int T, double alpha);

    Input(const string &file_graph, const string &scenarios_graph, int default_vel,
          int nebulize_vel, int T, double alpha);

    explicit Input(Input *input)
        : S(input->S)
        , T(input->T)
        , default_vel(input->default_vel)
        , neblize_vel(input->neblize_vel)
        , alpha(input->alpha)
        , preprocessing(input->preprocessing)
        , is_trail(input->is_trail)
        , walk_mtz_model(input->walk_mtz_model)
        , graph(input->graph ? new Graph(*input->graph) : nullptr)
        , sp(input->sp ? new ShortestPath(*input->sp) : nullptr)
        , bc(input->bc ? new BlockConnection(*input->bc) : nullptr)
        , scenarios(input->scenarios)
        , first_stage_profit(input->first_stage_profit)
        , time_profit_proportion(input->time_profit_proportion)
        , arcs_in_path(input->arcs_in_path)
        , arc_length(input->arc_length)
        , simheuristic_scenario_sequence(input->simheuristic_scenario_sequence)
        , simheuristic_block_incidences(input->simheuristic_block_incidences)
        , simheuristic_block_acc_cases(input->simheuristic_block_acc_cases) {
        for (auto *sg : input->scenario_graphs)
            scenario_graphs.push_back(sg ? new Graph(*sg) : nullptr);
        for (auto *ssp : input->scenario_sps)
            scenario_sps.push_back(ssp ? new ShortestPath(*ssp) : nullptr);
        for (auto *sbc : input->scenario_bcs)
            scenario_bcs.push_back(sbc ? new BlockConnection(*sbc) : nullptr);
    }

    ~Input() {
        delete graph;
        delete sp;
        delete bc;
        for (auto *sg : scenario_graphs) delete sg;
        for (auto *ssp : scenario_sps) delete ssp;
        for (auto *sbc : scenario_bcs) delete sbc;
    }

    void updateFirstStageCases() {
        const int B = graph->getB();
        first_stage_profit.resize(B);
        time_profit_proportion.resize(B);

        for (int b = 0; b < B; ++b) {
            first_stage_profit[b] = graph->getCasesPerBlock(b);
            for (int s = 0; s < S; ++s) {
                first_stage_profit[b] += alpha * scenarios[s].getProbability() *
                                         scenarios[s].getCasesPerBlock(b);
            }
            time_profit_proportion[b] = first_stage_profit[b] > 0.0
                                            ? first_stage_profit[b] / static_cast<double>(getBlockTime(b))
                                            : 0.0;
        }
    }

    [[nodiscard]] double getFirstStageProfit(int b) const {
        return first_stage_profit[b];
    }

    [[nodiscard]] double getCasesFromScenarioBlock(int s, int b) const {
        return scenarios[s].getCasesPerBlock(b);
    }

    [[nodiscard]] const vector<double> &getCasesFromScenario(int s) const {
        return scenarios[s].getCases();
    }

    [[nodiscard]] double getSecondStageProfit(int s, int b) const {
        if (scenarios[s].getCasesPerBlock(b) <= 0.0)
            return 0.0;
        return alpha * scenarios[s].getProbability() * scenarios[s].getCasesPerBlock(b);
    }

    [[nodiscard]] double getScenarioProbability(int s) const {
        return scenarios[s].getProbability();
    }

    vector<int> getBlockConnectionRoute(const string &key) {
        return bc->getBlocksAttendPath(key);
    }

    int getBlockConnectionTime(const string &key) {
        return bc->getBlocksAttendCost(key);
    }

    vector<int> getBestOrderToAttendBlocks(const string &key) {
        return bc->getBestOrderToAttendBlocks(key);
    }

    bool isArcRoute(int i, int j) {
        if (arcs_in_path[i][j].empty())
            getArcTime(i, j);

        return arcs_in_path[i][j].size() > 1;
    }

    int getArcTime(int i, int j) {
        const int N = graph->getN();
        if (i >= N || j >= N)
            return 0;

        if (arc_length[i][j] != -1)
            return arc_length[i][j];

        Arc *arc = graph->getArc(i, j);
        int length = 0;
        if (arc == nullptr) {
            vector<int> path;
            length = sp->ShortestPathST(i, j, path);

            // Store arcs in path
            arcs_in_path[i][j].reserve(path.size() - 1);
            for (size_t k = 0; k < path.size() - 1; ++k)
                arcs_in_path[i][j].push_back(graph->getArc(path[k], path[k + 1]));
        } else {
            length = arc->getLength();
        }

        arc_length[i][j] = length;
        return length;
    }

    [[nodiscard]] int getBlockTime(int b) const {
        return graph->getTimePerBlock(b);
    }

    void updateBlocksInGraph(map<int, int> positive_block_to_block,
                             set<int> set_of_used_nodes,
                             vector<vector<bool>> used_arcs);

    void reduceGraphToPositiveCases();

    void loadScenarios(const string &instance);

    void getSetOfNodesPreprocessing(set<int> &used_nodes,
                                    vector<vector<bool>> &used_arcs);

    void walkAdaptMTZModel();

    void filterMostDifferentScenarios(int new_s);

    void showScenarios() const {
        for (int i = 0; i < S; ++i) {
            cout << "Scenario " << i << ": " << scenarios[i].getProbability() << endl;
            const int B = graph->getB();
            for (int b = 0; b < B; ++b) {
                const double cases = scenarios[i].getCasesPerBlock(b);
                if (cases > 0.0)
                    cout << "  Block " << b << ": " << cases << " cases" << endl;
            }
        }
    }

    [[nodiscard]] double getTimeProfitProportion(int b) const {
        return time_profit_proportion[b];
    }

    void startSimheuristic() {
        const int B = graph->getB();
        simheuristic_block_acc_cases.assign(B, 0);
        simheuristic_block_incidences.assign(B, 0);
        simheuristic_scenario_sequence.clear();

        for (int b = 0; b < B; ++b) {
            const int cases = static_cast<int>(graph->getCasesPerBlock(b));
            if (cases > 0) {
                simheuristic_block_acc_cases[b] = cases;
                simheuristic_block_incidences[b] = 1;
            }
        }
    }

    void appendNewScenario(Scenario &scenario) {
        scenarios.push_back(scenario);

        const int B = graph->getB();
        // Update feedback from simulation
        for (int b = 0; b < B; ++b) {
            const int cases = static_cast<int>(scenario.getCasesPerBlock(b));

            if (cases > 0) {
                simheuristic_block_acc_cases[b] += cases;
                ++simheuristic_block_incidences[b];
            }
        }

        // Update vector to shuffle scenarios
        simheuristic_scenario_sequence.push_back(S);
        ++S;
    }

    [[nodiscard]] int getSimheuristicBlockAccCases(int b) const {
        return simheuristic_block_acc_cases[b];
    }

    [[nodiscard]] int getSimheuristicBlockIncidence(int b) const {
        return simheuristic_block_incidences[b];
    }

    [[nodiscard]] const vector<Scenario> &getScenarios() const {
        return scenarios;
    }

    [[nodiscard]] ShortestPath *getShortestPath() const {
        return sp;
    }

    void setShortestPath(ShortestPath *new_sp) {
        sp = new_sp;
    }

    [[nodiscard]] double getAlpha() const {
        return alpha;
    }

    void setAlpha(double new_alpha) {
        alpha = new_alpha;
    }

    [[nodiscard]] Graph *getGraph() const {
        return graph;
    }

    void setGraph(Graph *new_graph) {
        graph = new_graph;
    }

    void setScenarios(vector<Scenario> new_scenarios) {
        scenarios = std::move(new_scenarios);
    }

    [[nodiscard]] Scenario *getScenario(int i) {
        return &scenarios[i];
    }

    void setScenario(int i, Scenario scenario) {
        scenarios[i] = std::move(scenario);
    }

    [[nodiscard]] int getS() const {
        return S;
    }

    void setS(int new_s) {
        S = new_s;
    }

    [[nodiscard]] int getT() const {
        return T;
    }

    void setT(int new_t) {
        T = new_t;
    }

    [[nodiscard]] bool isPreprocessing() const {
        return preprocessing;
    }

    [[nodiscard]] bool isTrail() const {
        return is_trail;
    }

    [[nodiscard]] bool isWalkMtzGraph() const {
        return walk_mtz_model;
    }

    void setBlockConnection(BlockConnection *new_bc) {
        bc = new_bc;
    }

    [[nodiscard]] BlockConnection *getBlockConnection() const {
        return bc;
    }

    bool isNodeInPositiveValidBlock(int node);

    void createScenarioGraphs();

    [[nodiscard]] Graph *getScenarioGraph(int s) const {
        if (scenario_graphs.empty()) return graph;
        return scenario_graphs[s];
    }

    [[nodiscard]] Graph *getGraphForStage(int r) const {
        if (r == 0 || scenario_graphs.empty()) return graph;
        return scenario_graphs[r - 1];
    }

    [[nodiscard]] ShortestPath *getScenarioSP(int s) const {
        if (scenario_sps.empty()) return sp;
        return scenario_sps[s];
    }

    [[nodiscard]] BlockConnection *getScenarioBCon(int s) const {
        if (scenario_bcs.empty()) return bc;
        return scenario_bcs[s];
    }

    [[nodiscard]] bool hasScenarioGraphs() const {
        return !scenario_graphs.empty();
    }
};

#endif
