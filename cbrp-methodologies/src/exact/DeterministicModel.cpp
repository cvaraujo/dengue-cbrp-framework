//
// Created by carlos on 06/07/21.
//

#include "DeterministicModel.hpp"
#include "gurobi_c.h"

class cyclecallback : public GRBCallback {

  public:
    double lastiter = 0, lastnode = 0;
    int numvars = 0, cuts = 0, num_frac_cuts = 0, num_lazy_cuts = 0;
    bool frac_cut = false;
    vector<vector<GRBVar>> x, y;
    typedef ListDigraph G;
    typedef G::Arc Arc;
    typedef G::ArcIt ArcIt;
    typedef G::Node Node;
    typedef G::ArcMap<double> LengthMap;
    typedef G::NodeMap<bool> BoolNodeMap;
    Input *input = nullptr;

    cyclecallback(Input *xinput, int xnumvars, const vector<vector<GRBVar>> &xx, const vector<vector<GRBVar>> &yy, bool frac_cut)
        : lastiter(0)
        , lastnode(0)
        , numvars(xnumvars)
        , x(xx)
        , y(yy)
        , input(xinput)
        , frac_cut(frac_cut) {
    }

  protected:
    void callback() override {
        if (where == GRB_CB_MIPSOL) {
            try {
                Graph *graph = input->getGraph();
                int n = graph->getN();

                vector<vector<int>> adj(n + 2);
                vector<bool> used_node(n + 1, false);

                // Efficient construction of adjacency and used node
                for (int i = 0; i <= n; ++i) {
                    for (const auto *arc : graph->getArcs(i)) {
                        int d = arc->getD();
                        if (getSolution(x[i][d]) > 0.1) {
                            adj[i].push_back(d);
                            used_node[i] = true;
                            used_node[d] = true;
                        }
                    }
                }

                vector<bool> visited(n + 1, false);
                vector<int> node_cc(n + 1, -1); // Component index for node
                vector<vector<int>> components;
                vector<vector<int_pair>> comp_arcs;

                // Non-recursive DFS for all components
                for (int i = n; i >= 0; --i) {
                    if (!used_node[i] || visited[i])
                        continue;

                    components.emplace_back();
                    comp_arcs.emplace_back();
                    int cc_idx = (int)components.size() - 1;
                    vector<int> stack{i};

                    while (!stack.empty()) {
                        int s = stack.back();
                        stack.pop_back();
                        if (visited[s])
                            continue;

                        visited[s] = true;
                        node_cc[s] = cc_idx;
                        components[cc_idx].push_back(s);

                        for (int k : adj[s]) {
                            comp_arcs[cc_idx].emplace_back(s, k);
                            if (!visited[k])
                                stack.push_back(k);
                        }
                    }
                }

                // If all nodes are in one connected component, solution is feasible
                if (components.size() <= 1)
                    return;

                num_lazy_cuts += (int)components.size() - 1;

                if (input->isTrail()) {
                    // Subtour elimination for each component except the largest (assume 0-th is the main one)
                    for (size_t ci = 1; ci < components.size(); ++ci) {
                        const auto &s_arcs = comp_arcs[ci];
                        int num_in_nodes = (int)components[ci].size();
                        GRBLinExpr in_arcs = 0;
                        for (const auto &pr : s_arcs)
                            in_arcs += x[pr.first][pr.second];

                        addLazy(in_arcs <= num_in_nodes - 1);
                    }
                } else {
                    for (size_t ci = 1; ci < components.size(); ++ci) {
                        const auto &s_arcs = comp_arcs[ci];
                        int num_in_nodes = (int)components[ci].size();
                        GRBLinExpr in_arcs = 0;
                        GRBLinExpr cut_arcs = 0;

                        for (const auto &pr : s_arcs)
                            in_arcs += x[pr.first][pr.second];

                        // Cut arcs: from outside to inside the component
                        for (int j = 0; j < n; ++j) {
                            if (node_cc[j] != (int)ci) {
                                for (const auto *arc : graph->getArcs(j)) {
                                    int d = arc->getD();
                                    if (node_cc[d] == (int)ci)
                                        cut_arcs += x[j][d];
                                }
                            }
                        }
                        addLazy(in_arcs <= num_in_nodes - 1 + cut_arcs);
                    }
                }
            } catch (const GRBException &e) {
                cout << "[LAZY] Error number: " << e.getErrorCode() << endl;
                cout << e.getMessage() << endl;
            } catch (...) {
                cout << "Error during callback" << endl;
            }
        } else if (where == GRB_CB_MIPNODE) {
            try {
                if (!frac_cut)
                    return;

                int mipStatus = getIntInfo(GRB_CB_MIPNODE_STATUS);

                if (mipStatus == GRB_OPTIMAL) {
                    Graph *graph = input->getGraph();
                    int n = graph->getN();

                    G flow_graph;
                    LengthMap capacity(flow_graph);
                    vector<Node> nodes(n + 1);
                    vector<bool> used_node(n + 1, false);

                    // Nodes and arcs for flow graph
                    for (int i = 0; i <= n; ++i)
                        nodes[i] = flow_graph.addNode();

                    for (int i = 0; i <= n; ++i) {
                        for (const auto *arc : graph->getArcs(i)) {
                            int j = arc->getD();
                            double val = getNodeRel(x[i][j]);
                            if (val > 0) {
                                Arc flow_arc = flow_graph.addArc(nodes[i], nodes[j]);
                                capacity[flow_arc] = val;
                                used_node[i] = true;
                                used_node[j] = true;
                            }
                        }
                    }

                    for (int i = 0; i < n; ++i) {
                        if (!used_node[i])
                            continue;

                        Preflow<G, LengthMap> preflow(flow_graph, capacity, nodes[i], nodes[n]);
                        preflow.runMinCut();

                        double mincut_value = preflow.flowValue();
                        if (mincut_value >= 1.0)
                            continue;

                        // Identify cut arcs from mincut
                        GRBLinExpr cut_arcs = 0;

                        for (int j = 0; j < n; ++j) {
                            if (!preflow.minCut(nodes[j]))
                                continue;
                            for (const auto *arc : graph->getArcs(j)) {
                                int k = arc->getD();
                                if (!preflow.minCut(nodes[k])) {
                                    cut_arcs += x[j][k];
                                }
                            }
                        }

                        if (cut_arcs.size() > 0) {
                            for (auto b : graph->getNode(i).second) {
                                addCut(cut_arcs >= y[i][b]);
                                ++num_frac_cuts;
                            }
                        }
                    }
                }
            } catch (const GRBException &e) {
                cout << "[FRAC] Error number: " << e.getErrorCode() << endl;
                cout << e.getMessage() << endl;
            } catch (...) {
                cout << "Error during callback" << endl;
            }
        }
    }
};

Solution DeterministicModel::Run(bool use_warm_start, const string &time_limit, const string &useModel, bool use_cuts) {
    this->createVariables();
    this->initModel(useModel);

    if (useModel == "MTZ")
        this->solveCompact(time_limit);
    else if (useModel == "EXP")
        this->solveExponential(time_limit, use_cuts);
    else {
        cout << "[!] Model not found!" << endl;
        exit(EXIT_FAILURE);
    }

    this->checkSolution();

    return this->getSolution();
}

void DeterministicModel::createVariables() {
    Graph *graph = this->input->getGraph();
    int o, d, n = graph->getN(), b = graph->getB();

    try {
        env.set("LogFile", "MS_mip.log");
        env.start();

        x = vector<vector<GRBVar>>(n + 1, vector<GRBVar>(n + 1));
        y = vector<vector<GRBVar>>(n, vector<GRBVar>(b));
        t = vector<vector<GRBVar>>(n + 1, vector<GRBVar>(n + 1));

        // X
        char name[40];
        for (o = 0; o <= n; ++o) {
            for (const auto *arc : graph->getArcs(o)) {
                d = arc->getD();
                sprintf(name, "x_%d_%d", o, d);
                x[o][d] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
            }
        }
        // Y
        for (int i = 0; i < n; ++i) {
            o = graph->getNodes()[i].first;
            for (auto bl : graph->getNode(i).second) {
                sprintf(name, "y_%d_%d", o, bl);
                y[o][bl] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
            }
        }

        // T
        for (o = 0; o <= n; ++o) {
            for (const auto *arc : graph->getArcs(o)) {
                d = arc->getD();
                sprintf(name, "t_%d_%d", o, d);
                t[o][d] = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, name);
            }
        }

        model.update();
#ifndef Silence
        cout << "[*] Create variables" << endl;
#endif
    } catch (const GRBException &ex) {
        cout << ex.getMessage() << endl;
        cout << ex.getErrorCode() << endl;
        exit(EXIT_FAILURE);
    }
}

void DeterministicModel::initModel(const string &useModel) {
#ifndef Silence
    cout << "[***] Creating " << useModel << " model!" << endl;
#endif

    objectiveFunction();
    artificialNodes();
    flowConservation();
    maxAttending();
    attendingPath();
    timeConstraint();
    if (useModel == "MTZ")
        compactTimeConstraint();

    this->model.update();

#ifndef Silence
    cout << "[***] Constraints and objective function created!" << endl;
#endif
}

void DeterministicModel::objectiveFunction() {
    GRBLinExpr objective;
    auto graph = input->getGraph();
    int n = graph->getN();

    for (int i = 0; i < n; ++i) {
        int j = graph->getNode(i).first;
        for (auto b : graph->getNode(i).second) {
            objective += y[j][b] * graph->getCasesPerBlock(b);
        }
    }

    model.setObjective(objective, GRB_MAXIMIZE);
    model.update();

#ifndef Silence
    cout << "[***] Obj. Function: Maximize profit" << endl;
#endif
}

void DeterministicModel::artificialNodes() {
    int n = this->input->getGraph()->getN();
    GRBLinExpr sink = 0, target = 0;

    for (int i = 0; i < n; ++i) {
        sink += x[n][i];
        target += x[i][n];
    }

    model.addConstr(sink == 1, "sink_constraint");
    model.addConstr(target == 1, "target_constraint");

#ifndef Silence
    cout << "[***] Contraint: dummy depot" << endl;
#endif
}

void DeterministicModel::flowConservation() {
    auto graph = input->getGraph();
    int n = graph->getN();

    for (int i = 0; i < n; ++i) {
        GRBLinExpr flow_out = 0, flow_in = 0;

        for (const auto *arc : graph->getArcs(i)) {
            int d = arc->getD();
            if (d >= n)
                continue;
            flow_out += x[i][d];
        }

        for (int j = 0; j < n; ++j) {
            for (const auto *arc : graph->getArcs(j)) {
                if (arc->getD() == i)
                    flow_in += x[j][i];
            }
        }

        flow_out += x[i][n];
        flow_in += x[n][i];
        model.addConstr(flow_in - flow_out == 0, "flow_conservation_" + to_string(i));
    }

#ifndef Silence
    cout << "[***] Constraint: Flow conservation" << endl;
#endif
}

void DeterministicModel::maxAttending() {
    auto graph = input->getGraph();
    int b = graph->getB();

    for (int bl = 0; bl < b; ++bl) {
        GRBLinExpr maxServ = 0;
        for (auto i : graph->getNodesFromBlock(bl))
            maxServ += y[i][bl];

        model.addConstr(maxServ <= 1, "max_service_block_" + to_string(bl));
    }

#ifndef Silence
    cout << "[***] Constraint: Serve each block at most once" << endl;
#endif
}

void DeterministicModel::attendingPath() {
    auto graph = input->getGraph();
    int n = graph->getN(), b = graph->getB();

    for (int bl = 0; bl < b; ++bl) {
        for (auto i : graph->getNodesFromBlock(bl)) {
            GRBLinExpr served = 0;
            for (const auto *arc : graph->getArcs(i))
                served += x[i][arc->getD()];

            model.addConstr(served >= y[i][bl], "att_path_" + to_string(i) + "_" + to_string(bl));
        }
    }

#ifndef Silence
    cout << "[***] Constraint: Include node in path" << endl;
#endif
}

void DeterministicModel::timeConstraint() {
    auto graph = input->getGraph();
    int n = graph->getN();

    GRBLinExpr arcTravel = 0, blockTravel = 0;
    for (int i = 0; i < n; ++i) {
        for (const auto *arc : graph->getArcs(i)) {
            int j = arc->getD();
            arcTravel += x[i][j] * arc->getLength();
        }

        for (auto b : graph->getNode(i).second)
            if (b != -1)
                blockTravel += y[i][b] * graph->getTimePerBlock(b);
    }
    model.addConstr(blockTravel + arcTravel <= input->getT(), "max_time");

#ifndef Silence
    cout << "[***] Constraint: Time limit" << endl;
#endif
}

void DeterministicModel::compactTimeConstraint() {
    auto graph = input->getGraph();
    int n = graph->getN();

    for (int i = 0; i <= n; ++i) {
        if (i < n)
            model.addConstr(t[n][i] == 0);

        for (const auto *arc : graph->getArcs(i)) {
            int j = arc->getD();
            if (j >= n)
                continue;

            for (const auto *arcl : graph->getArcs(j)) {
                int k = arcl->getD();
                model.addConstr(
                    t[j][k] >= t[i][j] + (arc->getLength() * x[i][j]) - ((2 - x[i][j] - x[j][k]) * input->getT()),
                    "t_geq_" + to_string(i) + "_" + to_string(j) + "_" + to_string(k));
            }
        }
    }
    for (int i = 0; i < n; ++i) {
        model.addConstr(t[i][n] <= x[i][n] * input->getT(), "max_time");
    }

#ifndef Silence
    cout << "[***] Constraint: Time limit" << endl;
#endif
}

void DeterministicModel::solveCompact(const string &time_limit) {
    try {
        model.set("TimeLimit", time_limit);
        model.set("SoftMemLimit", "60");
        model.set("OutputFlag", "0");
        model.update();
#ifndef Silence
        model.set("OutputFlag", "1");
        model.update();
#endif
        // model.computeIIS();
        model.write("model.lp");
        model.optimize();
    } catch (const GRBException &ex) {
        cout << ex.getMessage() << endl;
    }
}

void DeterministicModel::solveExponential(const string &time_limit, bool frac_cut) {
    try {
        auto graph = input->getGraph();
        model.set("TimeLimit", time_limit);
        model.set(GRB_DoubleParam_Heuristics, 1.0);
        model.set(GRB_IntParam_LazyConstraints, 1);
        cyclecallback cb(input, graph->getN(), x, y, frac_cut);
        model.setCallback(&cb);
        model.set("OutputFlag", "0");
        model.update();

#ifndef Silence
        model.set("OutputFlag", "1");
        model.update();
#endif

        model.write("model.lp");
        model.optimize();

        // Save the number of cuts
        num_lazy_cuts = cb.num_lazy_cuts;
        num_frac_cuts = cb.num_frac_cuts;
    } catch (const GRBException &ex) {
        cout << ex.getMessage() << endl;
    }
}

Solution DeterministicModel::getSolution() {
    auto graph = input->getGraph();
    double of = 0.0;
    try {
        of = model.get(GRB_DoubleAttr_ObjVal);
    } catch (const GRBException &ex) {
        of = 0.0;
    }

    double UB = model.get(GRB_DoubleAttr_ObjBound);
    double runtime = model.get(GRB_DoubleAttr_Runtime);
    int gurobi_nodes = model.get(GRB_DoubleAttr_NodeCount);
    int lazy_cuts = this->num_lazy_cuts;
    int frac_cuts = this->num_frac_cuts;

    vector<vector<int>> yout(1);
    vector<vector<int_pair>> xout(1);

    int route_time_used = 0;
    int attend_time_used = 0;
    for (int i = 0; i <= graph->getN(); ++i) {
        for (const auto *arc : graph->getArcs(i))
            if (this->x[i][arc->getD()].get(GRB_DoubleAttr_X) > 0.5) {
                xout[0].emplace_back(i, arc->getD());
                route_time_used += arc->getLength();
            }

        for (int b : graph->getNode(i).second)
            if (this->y[i][b].get(GRB_DoubleAttr_X) > 0.5) {
                yout[0].push_back(b);
                attend_time_used += graph->getTimePerBlock(b);
            }
    }

    Solution solution(this->input, of, UB, runtime, route_time_used, attend_time_used, lazy_cuts, frac_cuts, gurobi_nodes, yout, xout);

    return solution;
}

bool DeterministicModel::checkSolution() {
    constexpr double TOLERANCE = 0.5;

    auto *graph = input->getGraph();
    const int max_time = input->getT();
    const int n = graph->getN();

    // Track visited nodes and used arcs during traversal
    vector<bool> visited(n + 1, false);
    vector<vector<bool>> used_arc(n + 1, vector<bool>(n + 1, false));

    // BFS traversal starting from depot (node n)
    deque<int> queue;
    queue.push_back(n);
    visited[n] = true;

    while (!queue.empty()) {
        const int current_node = queue.front();
        queue.pop_front();

        for (const auto *arc : graph->getArcs(current_node)) {
            const int destination = arc->getD();
            const double arc_value = x[current_node][destination].get(GRB_DoubleAttr_X);

            if (arc_value > TOLERANCE) {
                used_arc[current_node][destination] = true;

                if (!visited[destination]) {
                    queue.push_back(destination);
                    visited[destination] = true;
                }
            }
        }
    }

    // Validate solution consistency and calculate total time
    double total_time = 0.0;

    for (int node = 0; node <= n; ++node) {
        // Check if nodes with assigned blocks are reachable
        for (const auto &block : graph->getNode(node).second) {
            const double block_value = y[node][block].get(GRB_DoubleAttr_X);

            if (block_value > TOLERANCE) {
                total_time += graph->getTimePerBlock(block);

                if (!visited[node]) {
                    cout << "[!!!] Error: Node " << node
                         << " has assigned block " << block
                         << " but is not visited in the route" << endl;
                    return false;
                }
            }
        }

        // Check if used arcs are in the traversal path
        for (const auto *arc : graph->getArcs(node)) {
            const int destination = arc->getD();
            const double arc_value = x[node][destination].get(GRB_DoubleAttr_X);

            if (arc_value > TOLERANCE) {
                total_time += arc->getLength();

                if (!used_arc[node][destination]) {
                    cout << "[!!!] Error: Arc (" << node << " -> " << destination
                         << ") is used but not in traversal path" << endl;
                    return false;
                }
            }
        }
    }

    // Validate time constraint
    if (total_time > max_time) {
        cout << "[!!!] Error: Time constraint violated!" << endl;
        cout << "     Total time: " << total_time << " > Max time: " << max_time << endl;
        return false;
    }

#ifndef Silence
    cout << "[***] Solution validation passed!" << endl;
    cout << "     Total time used: " << total_time << " / " << max_time << endl;
#endif

    return true;
}
