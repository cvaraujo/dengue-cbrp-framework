//
// Created by Carlos on 26/07/2024.
//
#include "Changes.hpp"
#include "Parameters.hpp"
#include "Route.hpp"
#include <cstdlib>
#include <utility>

#ifndef DPARP_SOLUTION_H
#define DPARP_SOLUTION_H

class Solution {

  private:
    double of = 0.0, UB = INF, runtime = 0.0, start_UB = 0.0;
    int time_used = 0, route_time = 0, num_lazy_cuts = 0, num_frac_cuts = 0, solver_nodes = 0;
    Input *input = nullptr;
    vector<vector<int>> y;
    vector<vector<int_pair>> x;
    vector<Route *> routes;
    vector<double> scenario_profit;

  public:
    Solution(double of, vector<vector<int>> y, vector<vector<int_pair>> x, Input *input) {
        this->of = of;
        this->y = std::move(y);
        this->x = std::move(x);
        this->input = input;
    }

    explicit Solution(Input *input) {
        this->input = input;
        int S = this->input->getS();
        this->y = vector<vector<int>>(S + 1, vector<int>());
        this->x = vector<vector<int_pair>>(S + 1, vector<int_pair>());
        this->routes = vector<Route *>(S + 1);
        this->scenario_profit = vector<double>(S + 1, 0.0);
    };

    Solution() {
        this->of = 0.0;
        this->y = vector<vector<int>>();
        this->x = vector<vector<int_pair>>();
    }

    // Deterministic Model Constructor
    Solution(Input *input, double of, double UB, double runtime, int route_time_used, int attend_time_used, int num_lazy_cuts, int num_frac_cuts, int solver_nodes, vector<vector<int>> y, vector<vector<int_pair>> x) {
#ifndef Silence
        cout << "[*] Creating new Deterministic Solution" << endl;
#endif
        this->input = input;
        this->of = of;
        this->UB = UB;
        this->runtime = runtime;
        this->route_time = route_time_used;
        this->time_used = attend_time_used;
        this->num_lazy_cuts = num_lazy_cuts;
        this->num_frac_cuts = num_frac_cuts;
        this->solver_nodes = solver_nodes;
        this->y = std::move(y);
        this->x = std::move(x);
        this->start_UB = UB;
    }

    // Stochastic Model Constructor
    Solution(Input *input, double of, double UB, double runtime, int time_used, int num_lazy_cuts, int num_frac_cuts, int solver_nodes, vector<vector<int>> y, vector<vector<int_pair>> x) {
#ifndef Silence
        cout << "[*] Creating new Stochastic Solution" << endl;
#endif
        this->input = input;
        this->of = of;
        this->UB = UB;
        this->runtime = runtime;
        this->time_used = time_used;
        this->num_lazy_cuts = num_lazy_cuts;
        this->num_frac_cuts = num_frac_cuts;
        this->solver_nodes = solver_nodes;
        this->y = std::move(y);
        this->x = std::move(x);
        this->start_UB = UB;
        if (y.size() > 0 && x.size() > 0) {
            this->routes = vector<Route *>(1);
            this->routes[0] = new Route(this->input, x[0], y[0]);
        }
    }

    ~Solution() {
        scenario_profit.clear();
        y.clear(), x.clear();
        for (Route *r : this->routes)
            delete r;
        routes.clear();
    }

    // Construtor de cópia (deep copy)
    Solution(const Solution &other) {
        if (this != &other) {
            this->of = other.of;
            this->UB = other.UB;
            this->runtime = other.runtime;
            this->time_used = other.time_used;
            this->route_time = other.route_time;
            this->num_lazy_cuts = other.num_lazy_cuts;
            this->num_frac_cuts = other.num_frac_cuts;
            this->solver_nodes = other.solver_nodes;
            this->y = other.y;
            this->x = other.x;
            this->scenario_profit = other.scenario_profit;
            this->input = other.input;
            this->start_UB = other.start_UB;

            for (Route *r : other.routes)
                routes.push_back(new Route(*r)); // Copia profunda
        }
    }

    // Operador de atribuição (deep copy)
    Solution &operator=(const Solution &other) {
        if (this != &other) {
            // Libera as rotas existentes
            for (Route *r : routes)
                delete r;
            routes.clear();

            this->of = other.of;
            this->UB = other.UB;
            this->runtime = other.runtime;
            this->time_used = other.time_used;
            this->route_time = other.route_time;
            this->num_lazy_cuts = other.num_lazy_cuts;
            this->num_frac_cuts = other.num_frac_cuts;
            this->solver_nodes = other.solver_nodes;
            this->y = other.y;
            this->x = other.x;
            this->scenario_profit = other.scenario_profit;
            this->input = other.input;
            this->start_UB = other.start_UB;

            // Copia profunda das rotas
            for (Route *r : other.routes)
                routes.push_back(new Route(*r));
        }
        return *this;
    }

    void setStartUB(double ub) { this->start_UB = ub; };

    void WriteDeterministicSolution(const string &output_file) {
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "LB: " << this->of << endl;
        output << "UB: " << this->UB << endl;
        output << "Gurobi_Nodes: " << this->solver_nodes << endl;
        output << "Lazy_cuts: " << this->num_lazy_cuts << endl;
        output << "Frac_cuts: " << this->num_frac_cuts << endl;
        output << "Runtime: " << this->runtime << endl;
        output << "Route_Time: " << this->route_time << endl;
        output << "Attend_Time: " << this->time_used << endl;

        output << "X: ";
        for (auto [o, d] : this->x[0])
            output << o << "-" << d << ",";
        output << "\nY: ";
        for (auto b : this->y[0])
            output << b << ",";
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };

    void WriteDeterministicFromRouteStructs(const string &output_file) {
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "LB: " << this->of << endl;
        output << "UB: " << this->UB << endl;
        output << "Runtime: " << this->runtime << endl;
        output << "Route_Time: " << this->getRouteFromScenario(0)->getTimeRoute() << endl;
        output << "Attend_Time: " << this->getRouteFromScenario(0)->getTimeAttBlocks() << endl;
        output << "X: ";
        for (int i = 0; i < this->getRouteFromScenario(0)->getRoute().size() - 1; i++) {
            output << this->getRouteFromScenario(0)->getRoute()[i] << "-" << this->getRouteFromScenario(0)->getRoute()[i + 1] << ",";
        }
        output << "\nY: ";
        for (auto b : this->getRouteFromScenario(0)->getSequenceOfAttendingBlocks())
            output << b << ",";
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };

    void WriteStochasticSolution(const string &output_file) {
#ifndef Silence
        cout << "[*] Writing Stochastic Solution" << endl;
#endif
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "S: " << this->input->getS() << endl;
        output << "Alpha: " << this->input->getAlpha() << endl;
        output << "LB: " << this->of << endl;
        output << "UB: " << this->UB << endl;
        output << "Gurobi_Nodes: " << this->solver_nodes << endl;
        output << "Lazy_cuts: " << this->num_lazy_cuts << endl;
        output << "Frac_cuts: " << this->num_frac_cuts << endl;
        output << "Runtime: " << this->runtime << endl;

        if (this->x.size() > 0 && this->y.size() > 0) {
            for (int s = 0; s <= this->input->getS(); s++) {
                output << "Scenario " << s << ": " << endl;
                output << "X: ";
                for (auto [o, d] : this->x[s])
                    output << o << "-" << d << ",";
                output << "\nY: ";
                for (auto b : this->y[s])
                    output << b << ",";
                output << "\n";
            }
        }
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };

    void WriteSolution(const string &output_file) {
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "S: " << this->input->getS() << endl;
        output << "Alpha: " << this->input->getAlpha() << endl;
        output << "LB: " << this->of << endl;
        output << "Start_UB: " << this->start_UB << endl;
        output << "UB: " << this->UB << endl;
        output << "Gurobi_Nodes: " << this->solver_nodes << endl;
        output << "Lazy_cuts: " << this->num_lazy_cuts << endl;
        output << "Frac_cuts: " << this->num_frac_cuts << endl;
        output << "Runtime: " << this->runtime << endl;

        // output << "X: ";
        // for (auto [o, d] : this->x[0])
        //     output << o << " -> " << d << ", ";
        // output << "\nY: ";
        // for (auto b : this->y[0])
        //     output << b << ", ";
        // output << "\nRoute_Time: " << route->getTimeRoute() << "\nAttend_Time: " << route->getTimeAttBlocks() << endl;
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };

    void WriteStochasticHeuristicSolution(const string &output_file) {
        ofstream output;
        output.open(output_file);
        Graph *graph = this->input->getGraph();

        output << "N: " << graph->getN() << endl;
        output << "M: " << graph->getM() << endl;
        output << "B: " << graph->getB() << endl;
        output << "S: " << this->input->getS() << endl;
        output << "Alpha: " << this->input->getAlpha() << endl;
        output << "Start_UB: " << this->start_UB << endl;
        output << "LB: " << this->of << endl;
        output << "Runtime: " << this->runtime << endl;

        if (this->x.size() > 0 && this->y.size() > 0) {
            for (int s = 0; s <= this->input->getS(); s++) {
                output << "Scenario " << s << ": " << endl;
                output << "X: ";
                auto route = this->getRouteFromScenario(s);
                auto x_route = route->getRoute();
                for (int i = 0; i < x_route.size() - 1; i++) {
                    output << x_route[i] << "-" << x_route[i + 1] << ",";
                }
                output << "\nY: ";
                auto y_route = route->getSequenceOfAttendingBlocks();
                for (auto b : y_route)
                    output << b << ",";

                output << "\nRoute_Time: " << route->getTimeRoute() << endl;
                output << "Attend_Time: " << route->getTimeAttBlocks() << endl;
            }
        }
        output.close();
#ifndef Silence
        cout << "[*] Solution writed!" << endl;
#endif
    };

    void AddScenarioSolution(int s, vector<int_pair> x, vector<int> y, double profit) {
        if (routes.empty()) {
            int S = this->input->getS();
            this->y = vector<vector<int>>(S + 1, vector<int>());
            this->x = vector<vector<int_pair>>(S + 1, vector<int_pair>());
            this->routes = vector<Route *>(S + 1);
            this->scenario_profit = vector<double>(S + 1, 0.0);
        }

        this->routes[s] = new Route(this->input, x, y);
        this->x[s] = x, this->y[s] = y;
        this->scenario_profit[s] = profit;
        this->route_time = this->routes[s]->getTimeRoute();
        this->time_used = this->routes[s]->getTimeAttBlocks();
    };

    void AddScenarioSolution(int s, Route *route, double profit) {
        this->routes[s] = route;
        this->y[s] = route->getSequenceOfAttendingBlocks();
        this->scenario_profit[s] = profit;
        this->of += profit;
    };

    void AppendScenarioSolution(Route *route, double profit) {
        this->routes.push_back(route);
        this->y.push_back(route->getSequenceOfAttendingBlocks());
        this->scenario_profit.push_back(profit);
        this->of += profit;
    };

    void ReplaceScenarioSolution(int s, vector<int_pair> x, vector<int> y, Route *route) {
        this->routes[s] = route;
        this->x[s] = std::move(x), this->y[s] = std::move(y);
    };

    void ScenarioBlockSwapWithoutOF(int s, int b1, int b2) {
        this->y[s].erase(find(this->y[s].begin(), this->y[s].end(), b1));
        this->y[s].push_back(b2);
        this->routes[s]->SwapInRouteBlocks(b1, b2);
    };

    void ScenarioBlockSwap(int s, int b1, int b2, double delta) {
        this->y[s].erase(find(this->y[s].begin(), this->y[s].end(), b1));
        this->y[s].push_back(b2);
        this->routes[s]->SwapInRouteBlocks(b1, b2);
        this->of += delta;
    };

    void ApplySwaps(vector<pair<int, int_pair>> &swaps, double delta) {
        for (auto swap : swaps) {
            int s = swap.first;
            int_pair blocks = swap.second;
            int b1 = blocks.first, b2 = blocks.second;
            this->routes[s]->SwapInRouteBlocks(b1, b2);
        }
        this->of += delta;
    }

    void ApplyChanges(const Change &change) {
        // cout << "[!] Applying changes" << endl;
        if (!ChangeUtils::isEmpty(change)) {
            if (ChangeUtils::hasDeletions(change)) {
                ApplyRemovals(change.deletions);
            }
            if (ChangeUtils::hasInsertions(change)) {
                ApplyInsertions(change.insertions);
            }
            if (ChangeUtils::hasSwaps(change)) {
                ApplySwaps(change.swaps);
            }

            this->of += change.delta;
        }
    }

    void ApplyRemovals(const vector<int_pair> &removals) {
        for (auto &[scenario, block] : removals) {
            // cout << "\t[*] ScenarioRemove " << scenario << ": " << block << endl;
            this->routes[scenario]->RemoveBlockFromRoute(block);
        }
    }

    void ApplyInsertions(const vector<int_pair> &insertions) {
        for (auto &[scenario, block] : insertions) {
            // cout << "\t[*] ScenarioInsert " << scenario << ": " << block << endl;
            this->routes[scenario]->AddBlockToRoute(block, true);
        }
    }

    void ApplySwaps(const vector<pair<int, int_pair>> &swaps) {
        for (auto &[scenario, blocks] : swaps) {
            int to_remove = blocks.first, to_insert = blocks.second;
            // cout << "\t[*] ScenarioSwap " << scenario << ": " << to_remove << " -> " << to_insert << endl;
            this->routes[scenario]->GeneralSwapBlocks(to_remove, to_insert);
        }
    }

    double ComputeCurrentSolutionOF() {
        double curr_of = 0.0;
        Graph *graph = input->getGraph();
        vector<double> cases_per_block = graph->getCasesPerBlock();
        vector<bool> attended_first_stage = vector<bool>(graph->getB(), false);

        for (auto b : this->routes[0]->getSequenceOfAttendingBlocks()) {
            attended_first_stage[b] = true;
            curr_of += input->getFirstStageProfit(b);
        }

        for (int s = 0; s < input->getS(); s++) {
            Scenario *scn = input->getScenario(s);
            for (auto b : this->routes[s + 1]->getSequenceOfAttendingBlocks()) {
                if (attended_first_stage[b])
                    curr_of += scn->getProbability() * (1.0 - input->getAlpha()) * scn->getCasesPerBlock(b);
                else
                    curr_of += scn->getProbability() * scn->getCasesPerBlock(b);
            }
        }
        return curr_of;
    }

    void CheckSolution() {
        for (int s = 0; s <= input->getS(); s++) {
            if (!this->routes[s]->CheckSolution()) {
                cout << "[!] CheckSolution failed at route index " << s << " (scenario " << s - 1 << ")" << endl;
            }
        }
        if (abs(this->of - this->ComputeCurrentSolutionOF()) > EPS) {
            cout << "[!] OF mismatch: " << this->of << " != " << this->ComputeCurrentSolutionOF() << endl;
            exit(EXIT_FAILURE);
        }
    }

    double getScenarioProfit(int s) { return this->scenario_profit[s]; }

    void setScenarioProfit(int s, double profit) { this->scenario_profit[s] = profit; }

    void updateScenarioProfit(int s, double profit) { this->scenario_profit[s] += profit; }

    int getS() { return (input != nullptr) ? input->getS() : 0; }

    Graph *getGraph() { return input->getGraph(); }

    vector<Route *> getRoutes() { return this->routes; }

    void setRoute(Route *route, int s) { this->routes[s] = route; }

    Route *getRouteFromScenario(int s) { return this->routes[s]; }

    [[nodiscard]] double getOf() const { return of; }

    void setOf(double of) { this->of = of; }

    double getUB() { return UB; }

    void setUB(double UB) { this->UB = UB; }

    double getRuntime() { return runtime; }

    void setRuntime(double runtime) { this->runtime = runtime; }

    vector<int> getYFromScenario(int s) { return y[s]; }

    vector<int_pair> getXFromScenario(int s) { return x[s]; }

    vector<vector<int>> getY() { return y; }

    void setY(vector<vector<int>> y) { this->y = y; }

    vector<vector<int_pair>> getX() { return x; }

    void setX(vector<vector<int_pair>> x) { this->x = x; }

    void addAttendedToY(int s, int block) { this->y[s].push_back(block); }

    void addArcToX(int s, int o, int d) { this->x[s].push_back(make_pair(o, d)); }
};

#endif
