//
// Created by carlos on 06/07/21.
//

#include "StochasticModel.hpp"

class stochasticCyclecallback : public GRBCallback {

  public:
    double lastiter, lastnode;
    int numvars, cuts = 0, num_frac_cuts = 0, num_lazy_cuts = 0;
    bool frac_cut = false;
    vector<vector<vector<GRBVar>>> x; // x[r][i][j]
    vector<vector<GRBVar>> y;
    typedef ListDigraph G;
    typedef G::Arc Arc;
    typedef G::ArcIt ArcIt;
    typedef G::Node Node;
    typedef G::ArcMap<double> LengthMap;
    typedef G::NodeMap<bool> BoolNodeMap;
    Input *input;

    stochasticCyclecallback(Input *xinput, vector<vector<vector<GRBVar>>> xx, vector<vector<GRBVar>> yy, bool frac_cut) {
        lastiter = lastnode = 0;
        numvars = 0;
        x = xx;
        y = yy;
        input = xinput;
        this->frac_cut = frac_cut;
    }

  protected:
    void callback() {
        if (where == GRB_CB_MIPSOL) {
            try {
                bool is_feasible = true;

                for (int r = 0; r <= input->getS(); r++) {
                    Graph *graph = input->getGraphForStage(r);
                    int i, j, s, n = graph->getN();
                    vector<vector<int>> g = vector<vector<int>>(n + 2, vector<int>());
                    vector<bool> used_node = vector<bool>(n + 1);

                    for (i = 0; i <= n; i++) {
                        for (auto *arc : graph->getArcs(i)) {
                            if (getSolution(x[r][i][arc->getD()]) > 0.1) {
                                g[i].push_back(arc->getD());
                                used_node[i] = used_node[arc->getD()] = true;
                            }
                        }
                    }

                    vector<bool> visited(n + 1, false);
                    vector<int> node_connected_component = vector<int>(n + 1, -1);
                    vector<vector<int>> connected_component;
                    vector<vector<int_pair>> arcs_from_component;
                    int idx = 0;

                    for (i = n; i >= 0; i--) {
                        if (!used_node[i] || visited[i])
                            continue;

                        connected_component.push_back(vector<int>());
                        arcs_from_component.push_back(vector<int_pair>());

                        vector<int> stack;
                        stack.push_back(i);

                        while (!stack.empty()) {
                            s = stack.back();
                            stack.pop_back();

                            if (!visited[s]) {
                                connected_component[idx].push_back(s);
                                node_connected_component[s] = idx;
                                visited[s] = true;
                            }

                            for (auto k : g[s]) {
                                if (!visited[k])
                                    stack.push_back(k);
                                arcs_from_component[idx].push_back(make_pair(s, k));
                            }
                        }
                        idx++;
                    }

                    if (idx == 1)
                        continue;

                    is_feasible = false;

                    if (input->isTrail()) {
                        for (i = 1; i < (int)connected_component.size(); i++) {
                            vector<int> s_nodes = connected_component[i];
                            vector<int_pair> s_arcs = arcs_from_component[i];
                            GRBLinExpr in_arcs;
                            int num_in_nodes = s_nodes.size();

                            for (auto pair : s_arcs)
                                in_arcs += x[r][pair.first][pair.second];

                            addLazy(in_arcs <= num_in_nodes - 1);
                            num_lazy_cuts++;
                        }
                    } else {
                        for (i = 1; i < (int)connected_component.size(); i++) {
                            vector<int> s_nodes = connected_component[i];
                            vector<int_pair> s_arcs = arcs_from_component[i];
                            GRBLinExpr in_arcs, cut_arcs;
                            int num_in_nodes = s_nodes.size();

                            for (auto pair : s_arcs)
                                in_arcs += x[r][pair.first][pair.second];

                            for (int j = 0; j < n; j++)
                                if (node_connected_component[j] != i)
                                    for (auto arc : graph->getArcs(j))
                                        if (node_connected_component[arc->getD()] == i)
                                            cut_arcs += x[r][j][arc->getD()];

                            addLazy(in_arcs <= num_in_nodes - 1 + cut_arcs);
                            num_lazy_cuts++;
                        }
                    }
                }
                if (is_feasible)
                    return;
            } catch (GRBException e) {
                cout << "[LAZZY] Error number: " << e.getErrorCode() << endl;
                cout << e.getMessage() << endl;
            } catch (...) {
                cout << "Error during callback" << endl;
            }
        }

        else if (where == GRB_CB_MIPNODE) {
            try {
                if (!frac_cut)
                    return;

                int mipStatus = getIntInfo(GRB_CB_MIPNODE_STATUS);

                if (mipStatus == GRB_OPTIMAL) {
                    for (int r = 0; r <= input->getS(); r++) {
                        Graph *graph = input->getGraphForStage(r);
                        int i, j, n = graph->getN();

                        G flow_graph;
                        LengthMap capacity(flow_graph);
                        vector<Node> set_nodes = vector<Node>(n + 1);
                        vector<bool> used_node = vector<bool>(n, false);
                        vector<Arc> set_arcs;

                        for (i = 0; i <= n; i++)
                            set_nodes[i] = flow_graph.addNode();

                        for (i = 0; i <= n; i++) {
                            for (auto *arc : graph->getArcs(i)) {
                                j = arc->getD();

                                if (getNodeRel(x[r][i][j]) > 0) {
                                    set_arcs.push_back(flow_graph.addArc(set_nodes[i], set_nodes[j]));
                                    capacity[set_arcs[set_arcs.size() - 1]] = double(getNodeRel(x[r][i][j]));
                                    used_node[i] = used_node[j] = true;
                                }
                            }
                        }

                        double mincut_value;
                        for (i = 0; i < n; i++) {
                            if (!used_node[i])
                                continue;

                            Preflow<G, LengthMap> preflow(flow_graph, capacity, set_nodes[i], set_nodes[n]);
                            preflow.runMinCut();
                            mincut_value = preflow.flowValue();

                            if (mincut_value >= 1.0)
                                continue;

                            GRBLinExpr cut_arcs;
                            double cut_value = 0;

                            for (j = 0; j < n; j++) {
                                if (!preflow.minCut(set_nodes[j]))
                                    continue;

                                for (auto arc : graph->getArcs(j)) {
                                    int k = arc->getD();
                                    if (preflow.minCut(set_nodes[k]))
                                        continue;
                                    cut_arcs += x[r][j][k];
                                }
                            }

                            if (cut_arcs.size() > 0) {
                                addCut(cut_arcs >= cut_value);
                                num_frac_cuts++;
                            }
                        }
                    }
                }
            } catch (GRBException e) {
                cout << "[FRAC] Error number: " << e.getErrorCode() << endl;
                cout << e.getMessage() << endl;
            } catch (...) {
                cout << "Error during callback" << endl;
            }
        }
    }
};

Solution StochasticModel::Run(bool use_warm_start, string time_limit, string model, bool use_cuts) {
#ifndef Silence
    cout << "[*] Running Stochastic Trail Model" << endl;
#endif

    this->createVariables();
    this->initModel(model);

    if (model == "MTZ")
        this->solveCompact(time_limit);
    else if (model == "EXP")
        this->solveExponential(time_limit, use_cuts);
    else {
        cout << "[!] Model not found!" << endl;
        exit(EXIT_FAILURE);
    }

#ifndef Silence
    cout << "[***] Model solved!" << endl;
#endif
    return this->getSolution();
}

void StochasticModel::createVariables() {
    auto graph = this->input->getGraph();
    int o, d, b = graph->getB(), S = input->getS();
    try {
        env.set("LogFile", "MS_mip.log");
        env.start();

        x.resize(S + 1);
        t.resize(S + 1);
        y = vector<vector<GRBVar>>(b, vector<GRBVar>(S + 1));
        z = vector<vector<GRBVar>>(b, vector<GRBVar>(S + 1));
        y_exists = vector<vector<bool>>(b, vector<bool>(S + 1, false));
        z_exists = vector<vector<bool>>(b, vector<bool>(S + 1, false));

        for (int r = 0; r <= S; r++) {
            Graph *rg = input->getGraphForStage(r);
            int n = rg->getN();

            x[r] = vector<vector<GRBVar>>(n + 1, vector<GRBVar>(n + 1));
            t[r] = vector<vector<GRBVar>>(n + 1, vector<GRBVar>(n + 1));

            char name[40];
            for (o = 0; o <= n; o++) {
                for (auto *arc : rg->getArcs(o)) {
                    d = arc->getD();
                    sprintf(name, "x_%d_%d_%d", o, d, r);
                    x[r][o][d] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
                }
            }

            for (o = 0; o <= n; o++) {
                for (auto *arc : rg->getArcs(o)) {
                    d = arc->getD();
                    sprintf(name, "t_%d_%d_%d", o, d, r);
                    t[r][o][d] = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, name);
                }
            }

            if (r == 0) {
                for (int bl = 0; bl < b; bl++) {
                    sprintf(name, "y_%d_%d", bl, r);
                    y[bl][r] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
                    y_exists[bl][r] = true;
                }
            } else {
                bool use_reduced = input->hasScenarioGraphs();
                for (int bl = 0; bl < b; bl++) {
                    if (use_reduced && input->getScenario(r - 1)->getCasesPerBlock(bl) <= 0.0)
                        continue;
                    sprintf(name, "y_%d_%d", bl, r);
                    y[bl][r] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
                    y_exists[bl][r] = true;

                    sprintf(name, "z_%d_%d", bl, r);
                    z[bl][r] = model.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS, name);
                    z_exists[bl][r] = true;
                }
            }
        }

        model.update();
#ifndef Silence
        cout << "Create variables" << endl;
#endif
    } catch (GRBException &ex) {
        cout << ex.getMessage() << endl;
        cout << ex.getErrorCode() << endl;
        exit(EXIT_FAILURE);
    }
}

void StochasticModel::initModel(string model) {
#ifndef Silence
    cout << "[***] Creating " << model << " model!" << endl;
#endif

    objectiveFunction();
    zValue(), artificialNodes(), flowConservation();
    timeConstraint(), attendingPath();

    if (model == "MTZ")
        compactTimeConstraint();

    this->model.update();

#ifndef Silence
    cout << "[***] Constraints and objective function created!" << endl;
#endif
}

void StochasticModel::objectiveFunction() {
    auto graph = this->input->getGraph();
    GRBLinExpr objective;
    int S = input->getS(), B = graph->getB();

    for (int b = 0; b < B; b++) {
        double expr = 0;
        for (int s = 0; s < S; s++)
            expr += input->getScenario(s)->getProbability() * input->getAlpha() * input->getScenario(s)->getCasesPerBlock(b);

        objective += (y[b][0] * (graph->getCasesPerBlock(b) + expr));
    }

    for (int s = 0; s < S; s++) {
        GRBLinExpr expr;
        for (int b = 0; b < B; b++)
            if (z_exists[b][s + 1])
                expr += z[b][s + 1];

        objective += input->getScenario(s)->getProbability() * expr;
    }

    model.setObjective(objective, GRB_MAXIMIZE);
    model.update();

#ifndef Silence
    cout << "[***] Obj. Function: Maximize profit" << endl;
#endif
}

void StochasticModel::zValue() {
    auto graph = this->input->getGraph();
    int B = graph->getB();

    for (int s = 1; s <= input->getS(); s++) {
        vector<double> cases = input->getScenario(s - 1)->getCases();

        for (int b = 0; b < B; b++) {
            if (!z_exists[b][s])
                continue;
            model.addConstr(z[b][s] <= y[b][s] * ((1 - input->getAlpha()) * cases[b]) + (1 - y[b][0]) * input->getAlpha() * cases[b], "max_z_profit");
            model.addConstr(z[b][s] <= y[b][s] * cases[b], "z_bigm_profit");
        }
    }
    model.update();
#ifndef Silence
    cout << "[***] Constraint: z value" << endl;
#endif
}

void StochasticModel::artificialNodes() {
    for (int s = 0; s <= input->getS(); s++) {
        Graph *rg = input->getGraphForStage(s);
        int n = rg->getN();
        GRBLinExpr sink, target;

        for (int i = 0; i < n; i++) {
            sink += x[s][n][i];
            target += x[s][i][n];
        }

        model.addConstr(sink == 1, "sink_constraint_" + to_string(s));
        model.addConstr(target == 1, "target_constraint_" + to_string(s));
    }
#ifndef Silence
    cout << "[***] Contraint: dummy depot" << endl;
#endif
}

void StochasticModel::flowConservation() {
    for (int s = 0; s <= input->getS(); s++) {
        Graph *rg = input->getGraphForStage(s);
        int n = rg->getN();

        for (int i = 0; i < n; i++) {
            GRBLinExpr flow_out, flow_in;

            for (auto *arc : rg->getArcs(i)) {
                if (arc->getD() >= n)
                    continue;
                flow_out += x[s][i][arc->getD()];
            }

            for (int j = 0; j < n; j++) {
                for (auto *arc : rg->getArcs(j)) {
                    if (arc->getD() == i)
                        flow_in += x[s][j][i];
                }
            }

            flow_out += x[s][i][n];
            flow_in += x[s][n][i];
            model.addConstr(flow_in - flow_out == 0, "flow_conservation_" + to_string(s) + "_" + to_string(i));
        }
    }
#ifndef Silence
    cout << "[***] Constraint: Flow conservation" << endl;
#endif
}

void StochasticModel::attendingPath() {
    int B = input->getGraph()->getB();

    for (int s = 0; s <= input->getS(); s++) {
        Graph *rg = input->getGraphForStage(s);

        for (int bl = 0; bl < B; bl++) {
            if (!y_exists[bl][s])
                continue;

            GRBLinExpr served;
            for (auto i : rg->getNodesFromBlock(bl))
                for (auto *arc : rg->getArcs(i))
                    served += x[s][i][arc->getD()];

            model.addConstr(served >= y[bl][s], "att_path_" + to_string(s) + "_" + to_string(bl));
        }
    }

#ifndef Silence
    cout << "[***] Constraint: Include node in path" << endl;
#endif
}

void StochasticModel::timeConstraint() {
    int B = input->getGraph()->getB();

    for (int s = 0; s <= input->getS(); s++) {
        Graph *rg = input->getGraphForStage(s);
        int n = rg->getN();
        GRBLinExpr arcTravel, blockTravel;

        for (int i = 0; i < n; i++) {
            for (auto *arc : rg->getArcs(i)) {
                int j = arc->getD();
                arcTravel += x[s][i][j] * arc->getLength();
            }
        }

        for (int b = 0; b < B; b++)
            if (y_exists[b][s])
                blockTravel += y[b][s] * rg->getTimePerBlock(b);

        model.addConstr(arcTravel + blockTravel <= input->getT(), "max_time_" + to_string(s));
    }

#ifndef Silence
    cout << "[***] Constraint: time limit" << endl;
#endif
}

void StochasticModel::compactTimeConstraint() {
    for (int s = 0; s <= input->getS(); s++) {
        Graph *rg = input->getGraphForStage(s);
        int n = rg->getN();

        for (int i = 0; i <= n; i++) {
            if (i < n)
                model.addConstr(t[s][n][i] == 0);

            for (auto *arc : rg->getArcs(i)) {
                int j = arc->getD();
                if (j >= n)
                    continue;

                for (auto *arcl : rg->getArcs(j)) {
                    int k = arcl->getD();
                    model.addConstr(t[s][j][k] >= t[s][i][j] - (2 - x[s][i][j] - x[s][j][k]) * input->getT() + arc->getLength() * x[s][i][j],
                                    "t_geq_" + to_string(s) + "_" + to_string(i) + "_" + to_string(j) + "_" + to_string(k));
                }
            }
        }

        int n2 = rg->getN();
        for (int i = 0; i < n2; i++)
            model.addConstr(t[s][i][n2] <= x[s][i][n2] * input->getT(), "max_time_mtz_" + to_string(s) + "_" + to_string(i));
    }
#ifndef Silence
    cout << "[***] Constraint: Time limit" << endl;
#endif
}

void StochasticModel::solveCompact(string time_limit) {
    try {
        model.set("TimeLimit", time_limit);
        model.set("SoftMemLimit", "60");
        model.set("OutputFlag", "0");
        model.update();
#ifndef Silence
        model.set("OutputFlag", "1");
        model.update();
#endif
        model.write("model.lp");
        model.optimize();
    } catch (GRBException &ex) {
        cout << ex.getMessage() << endl;
    }
}

void StochasticModel::solveExponential(string time_limit, bool frac_cut) {
    try {
        model.set("TimeLimit", time_limit);
        model.set(GRB_DoubleParam_Heuristics, 1.0);
        model.set(GRB_IntParam_LazyConstraints, 1);
        stochasticCyclecallback cb = stochasticCyclecallback(input, x, y, frac_cut);
        model.setCallback(&cb);
        model.set("OutputFlag", "0");
        model.update();

#ifndef Silence
        model.set("OutputFlag", "1");
        model.update();
#endif

        model.write("model.lp");
        model.optimize();

        num_lazy_cuts = cb.num_lazy_cuts, num_frac_cuts = cb.num_frac_cuts;
    } catch (GRBException &ex) {
        cout << ex.getMessage() << endl;
    }
}

Solution StochasticModel::getSolution() {
    auto graph = input->getGraph();
    double of = 0.0;
    try {
        of = model.get(GRB_DoubleAttr_ObjVal);
    } catch (GRBException &ex) {
        of = 0.0;
    }

    double UB = model.get(GRB_DoubleAttr_ObjBound);
    double runtime = model.get(GRB_DoubleAttr_Runtime);
    int gurobi_nodes = model.get(GRB_DoubleAttr_NodeCount);
    int num_lazy_cuts = this->num_lazy_cuts;
    int num_frac_cuts = this->num_frac_cuts;
    int time_used = 0;
    int B = graph->getB();

    vector<vector<int>> y;
    vector<vector<int_pair>> x;

    try {
        for (int s = 0; s <= input->getS(); s++) {
            y.emplace_back(), x.emplace_back();
            Graph *rg = input->getGraphForStage(s);

            for (int i = 0; i <= rg->getN(); i++) {
                for (auto *arc : rg->getArcs(i))
                    if (this->x[s][i][arc->getD()].get(GRB_DoubleAttr_X) > 0.5) {
                        x[s].emplace_back(i, arc->getD());
                        time_used += arc->getLength();
                    }
            }

            for (int b = 0; b < B; b++)
                if (y_exists[b][s] && this->y[b][s].get(GRB_DoubleAttr_X) > 0.5) {
                    y[s].emplace_back(b);
                    time_used += graph->getTimePerBlock(b);
                }
        }
    } catch (GRBException &ex) {
        y = vector<vector<int>>();
        x = vector<vector<int_pair>>();
    }

    Solution solution = Solution(this->input, of, UB, runtime, time_used, num_lazy_cuts, num_frac_cuts, gurobi_nodes, y, x);
    return solution;
}

bool StochasticModel::checkSolution() {
    int max_time = input->getT();
    int S = input->getS();
    int B = input->getGraph()->getB();

    for (int r = 0; r <= S; r++) {
        Graph *rg = input->getGraphForStage(r);
        int n = rg->getN();
        vector<vector<bool>> used_arc = vector<vector<bool>>(n + 1, vector<bool>(n + 1, false));

        int i, j, s;
        float time = 0;

        vector<bool> visited(n + 1, false);

        deque<int> stack;
        stack.push_back(n);

        while (!stack.empty()) {
            s = stack.front();
            stack.pop_front();

            for (auto *arc : rg->getArcs(s)) {
                j = arc->getD();
                if (x[r][s][j].get(GRB_DoubleAttr_X) > 0.5) {
                    used_arc[s][j] = true;

                    if (!visited[j]) {
                        stack.push_back(j);
                        visited[j] = true;
                    }
                }
            }
        }

        for (i = 0; i <= n; i++) {
            for (auto *arc : rg->getArcs(i)) {
                if (x[r][i][arc->getD()].get(GRB_DoubleAttr_X) > 0.8) {
                    time += arc->getLength();
                    if (!used_arc[i][arc->getD()]) {
                        cout << "[!!!] Not used arc!" << endl;
                        cout << i << " " << arc->getD() << endl;
                        return false;
                    }
                }
            }
        }

        for (int b = 0; b < B; b++) {
            if (!y_exists[b][r])
                continue;
            if (y[b][r].get(GRB_DoubleAttr_X) > 0.5) {
                time += rg->getTimePerBlock(b);

                bool is_node_in_path = false;
                for (auto j : rg->getNodesFromBlock(b)) {
                    if (visited[j]) {
                        is_node_in_path = true;
                        break;
                    }
                }
                if (!is_node_in_path) {
                    cout << "[!!!] Not visited node!" << endl;
                    return false;
                }
            }
        }

        if (time > max_time) {
            cout << "T: " << time << " <= " << max_time << endl;
            cout << "[!!!] Resource limitation error!" << endl;
            return false;
        }
    }

#ifndef Silence
    cout << "[***] Instance ok!!!" << endl;
#endif
    return true;
}
