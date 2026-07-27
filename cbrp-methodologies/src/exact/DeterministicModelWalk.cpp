//
// Created by carlos on 06/07/21.
//

#include "DeterministicModelWalk.hpp"
#include "gurobi_c.h"

class cyclecallbackWalk : public GRBCallback {

  public:
    double lastiter, lastnode;
    int numvars, cuts = 0, num_frac_cuts = 0, num_lazy_cuts = 0;
    bool frac_cut = false;
    vector<vector<GRBVar>> x;
    vector<GRBVar> y;
    typedef ListDigraph G;
    typedef G::Arc Arc;
    typedef G::ArcIt ArcIt;
    typedef G::Node Node;
    typedef G::ArcMap<double> LengthMap;
    typedef G::NodeMap<bool> BoolNodeMap;
    Input *input;

    cyclecallbackWalk(Input *xinput, int xnumvars, vector<vector<GRBVar>> xx, vector<GRBVar> yy, bool frac_cut) {
        lastiter = lastnode = 0;
        numvars = xnumvars;
        x = xx;
        y = yy;
        input = xinput;
        frac_cut = frac_cut;
    }

  protected:
    void callback() {
        if (where == GRB_CB_MIPSOL) {
            try {
                bool is_feasible = true;
                Graph *graph = input->getGraph();

                int i, j, s, N = graph->getN();
                vector<vector<int>> g = vector<vector<int>>(N + 2, vector<int>());
                vector<bool> used_node = vector<bool>(N + 1);

                // Create graph G'
                for (i = 0; i <= N; i++) {
                    for (auto *arc : graph->getArcs(i)) {
                        if (getSolution(x[i][arc->getD()]) > 0.1) {
                            g[i].push_back(arc->getD());
                            used_node[i] = used_node[arc->getD()] = true;
                        }
                    }
                }

                vector<bool> visited(N + 1, false);
                vector<int> node_connected_component = vector<int>(N + 1, -1);
                vector<vector<int>> connected_component;
                vector<vector<int_pair>> arcs_from_component;
                int idx = 0;

                // DFS
                for (i = N; i >= 0; i--) {
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

                // Feasible solution
                if (idx == 1)
                    return;

                // Need Cuts
                is_feasible = false;

                for (i = 1; i < connected_component.size(); i++) {
                    vector<int> s_nodes = connected_component[i];
                    vector<int_pair> s_arcs = arcs_from_component[i];
                    GRBLinExpr cut_arcs;

                    // Arcs in the cut S
                    for (int j = 0; j < N; j++)
                        if (node_connected_component[j] != i)
                            for (auto arc : graph->getArcs(j))
                                if (node_connected_component[arc->getD()] == i)
                                    cut_arcs += x[j][arc->getD()];

                    for (int org_1 : s_nodes) {
                        for (int org_2 : s_nodes) {
                            if (org_1 == org_2)
                                continue;

                            for (auto a_p : graph->getArcs(org_1)) {
                                for (auto a_pp : graph->getArcs(org_2)) {
                                    addLazy(cut_arcs >= x[org_1][a_p->getD()] + x[org_2][a_pp->getD()] - 1);
                                    num_lazy_cuts++;
                                }
                            }
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
        } else if (where == GRB_CB_MIPNODE) {
            try {
                if (!frac_cut)
                    return;

                int mipStatus = getIntInfo(GRB_CB_MIPNODE_STATUS);

                if (mipStatus == GRB_OPTIMAL) {
                    Graph *graph = input->getGraph();
                    int i, j, u, v, n = graph->getN();

                    // Basic structures to use Lemon
                    G flow_graph;
                    LengthMap capacity(flow_graph);
                    vector<Node> set_nodes = vector<Node>(n + 1);
                    vector<bool> used_node = vector<bool>(n, false);
                    vector<Arc> set_arcs;

                    // Create the node set
                    for (i = 0; i <= n; i++)
                        set_nodes[i] = flow_graph.addNode();

                    // Create the edge set
                    for (i = 0; i <= n; i++) {
                        for (auto *arc : graph->getArcs(i)) {
                            j = arc->getD();

                            if (getNodeRel(x[i][j]) > 0) {
                                set_arcs.push_back(flow_graph.addArc(set_nodes[i], set_nodes[j]));
                                capacity[set_arcs[set_arcs.size() - 1]] = double(getNodeRel(x[i][j]));
                                used_node[i] = used_node[j] = true;
                            }
                        }
                    }

                    // Init necessary structures
                    double mincut_value;
                    for (i = 0; i < n; i++) {
                        // If there is no arc using this node, ignore it
                        if (!used_node[i])
                            continue;

                        // Lemon MaxFlow instance
                        Preflow<G, LengthMap> preflow(flow_graph, capacity, set_nodes[i], set_nodes[n]);
                        preflow.runMinCut();
                        mincut_value = preflow.flowValue();

                        if (mincut_value >= 1.0)
                            continue;

                        // Create basic variables
                        GRBLinExpr cut_arcs;
                        double cut_value = 0;

                        // Get cut arcs
                        for (j = 0; j < n; j++) {
                            if (!preflow.minCut(set_nodes[j]))
                                continue;

                            for (auto arc : graph->getArcs(j)) {
                                int k = arc->getD();

                                if (preflow.minCut(set_nodes[k]))
                                    continue;

                                cut_arcs += x[j][k];
                            }
                        }

                        if (cut_arcs.size() > 0) {
                            addCut(cut_arcs >= cut_value);
                            num_frac_cuts++;
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

Solution DeterministicModelWalk::Run(bool use_warm_start, string time_limit, string model, bool use_cuts) {
    this->createVariables();
    this->initModel(model);
    this->solveExponential(time_limit, use_cuts);

    // this->checkSolution();

    return this->getSolution();
}

void DeterministicModelWalk::createVariables() {
    Graph *graph = this->input->getGraph();
    int o, d, k, n = graph->getN(), m = graph->getM(), b = graph->getB();

    try {
        env.set("LogFile", "MS_mip.log");
        env.start();

        x = vector<vector<GRBVar>>(n + 1, vector<GRBVar>(n + 1));
        y = vector<GRBVar>(b);

        // X
        char name[40];
        for (o = 0; o <= n; o++) {
            for (auto *arc : graph->getArcs(o)) {
                d = arc->getD();
                sprintf(name, "x_%d_%d", o, d);
                x[o][d] = model.addVar(0.0, b - 1, 0, GRB_INTEGER, name);
            }
        }
        // Y
        for (int bl = 0; bl < b; bl++) {
            sprintf(name, "y_%d", bl);
            y[bl] = model.addVar(0.0, 1.0, 0, GRB_BINARY, name);
        }

        model.update();
#ifndef Silence
        cout << "[*] Create variables" << endl;
#endif
    } catch (GRBException &ex) {
        cout << ex.getMessage() << endl;
        cout << ex.getErrorCode() << endl;
        exit(EXIT_FAILURE);
    }
}

void DeterministicModelWalk::initModel(string model) {
#ifndef Silence
    cout << "[***] Creating " << model << " model!" << endl;
#endif

    objectiveFunction(), artificialNodes();
    flowConservation(), attendingPath(), timeConstraint();

    this->model.update();

#ifndef Silence
    cout << "[***] Constraints and objective function created!" << endl;
#endif
}

void DeterministicModelWalk::objectiveFunction() {
    GRBLinExpr objective;
    auto graph = input->getGraph();
    int B = graph->getB();

    for (int b = 0; b < B; b++)
        objective += (y[b] * graph->getCasesPerBlock(b));

    model.setObjective(objective, GRB_MAXIMIZE);
    model.update();

#ifndef Silence
    cout << "[***] Obj. Function: Maximize profit" << endl;
#endif
}

void DeterministicModelWalk::artificialNodes() {
    int n = this->input->getGraph()->getN();
    GRBLinExpr sink, target;

    for (int i = 0; i < n; i++) {
        sink += x[n][i];
        target += x[i][n];
    }

    model.addConstr(sink == 1, "sink_constraint");
    model.addConstr(target == 1, "target_constraint");

#ifndef Silence
    cout << "[***] Contraint: dummy depot" << endl;
#endif
}

void DeterministicModelWalk::flowConservation() {
    auto graph = input->getGraph();
    int i, j, n = graph->getN();

    for (i = 0; i < n; i++) {
        GRBLinExpr flow_out, flow_in;

        for (auto *arc : graph->getArcs(i)) {
            if (arc->getD() >= n)
                continue;
            flow_out += x[i][arc->getD()];
        }

        for (j = 0; j < n; j++) {
            for (auto *arc : graph->getArcs(j)) {
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

void DeterministicModelWalk::attendingPath() {
    auto graph = input->getGraph();
    int j, b, N = graph->getN(), B = graph->getB();

    for (b = 0; b < B; b++) {
        GRBLinExpr served = 0;
        for (auto i : graph->getNodesFromBlock(b)) {
            for (auto *arc : graph->getArcs(i))
                served += x[i][arc->getD()];
        }
        model.addConstr(served >= y[b], "att_path_" + to_string(b));
    }

#ifndef Silence
    cout << "[***] Constraint: Include node in path" << endl;
#endif
}

void DeterministicModelWalk::timeConstraint() {
    auto graph = input->getGraph();
    int i, j, N = graph->getN(), B = graph->getB();

    GRBLinExpr arcTravel;
    for (i = 0; i < N; i++)
        for (auto *arc : graph->getArcs(i))
            arcTravel += x[i][arc->getD()] * arc->getLength();

    GRBLinExpr blockTravel;
    for (int b = 0; b < B; b++)
        blockTravel += y[b] * graph->getTimePerBlock(b);

    model.addConstr(blockTravel + arcTravel <= input->getT(), "max_time");

#ifndef Silence
    cout << "[***] Constraint: Time limit" << endl;
#endif
}

void DeterministicModelWalk::solveExponential(string time_limit, bool frac_cut) {
    try {
        auto graph = input->getGraph();
        model.set("TimeLimit", time_limit);
        model.set(GRB_DoubleParam_Heuristics, 1.0);
        model.set(GRB_IntParam_LazyConstraints, 1);
        cyclecallbackWalk cb = cyclecallbackWalk(input, graph->getN(), x, y, frac_cut);
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
        num_lazy_cuts = cb.num_lazy_cuts, num_frac_cuts = cb.num_frac_cuts;
    } catch (GRBException &ex) {
        cout << ex.getMessage() << endl;
    }
}

Solution DeterministicModelWalk::getSolution() {
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
    int time_used = 0;

    vector<vector<int>> yout(1);
    vector<vector<int_pair>> xout(1);

    int route_time_used = 0;
    int attend_time_used = 0;
    for (int i = 0; i <= graph->getN(); ++i) {
        for (const auto *arc : graph->getArcs(i)) {
            double time_used_arc = this->x[i][arc->getD()].get(GRB_DoubleAttr_X);
            if (time_used_arc > 0.5) {
                xout[0].emplace_back(i, arc->getD());
                route_time_used += int(time_used_arc * arc->getLength());
            }
        }
    }
    for (int b = 0; b < graph->getB(); b++) {
        if (this->y[b].get(GRB_DoubleAttr_X) > 0.5) {
            yout[0].push_back(b);
            attend_time_used += graph->getTimePerBlock(b);
        }
    }

    Solution solution(this->input, of, UB, runtime, route_time_used, attend_time_used, lazy_cuts, frac_cuts, gurobi_nodes, yout, xout);
    return solution;
}

bool DeterministicModelWalk::checkSolution() {
    auto graph = input->getGraph();
    int max_time = input->getT();
    int n = graph->getN();

    // Check connectivity
    vector<vector<bool>> used_arc = vector<vector<bool>>(n + 1, vector<bool>(n + 1, false));

    int start_node = n, i, j, s, target;
    bool find_next = true;
    float time = 0, insecticide = 0;

    vector<bool> visited(n + 1, false);
    vector<int> conn_comp = vector<int>(n + 1, -1);
    vector<vector<int>> conn = vector<vector<int>>(n + 1, vector<int>());
    // DFS
    deque<int> stack;
    stack.push_back(n);

    while (!stack.empty()) {
        s = stack.front();
        stack.pop_front();

        for (auto *arc : graph->getArcs(s)) {
            j = arc->getD();
            if (x[s][j].get(GRB_DoubleAttr_X) > 0.5) {
                used_arc[s][j] = true;

                if (!visited[j]) {
                    stack.push_back(j);
                    visited[j] = true;
                }
            }
        }
    }

    // Check visiting
    for (int b = 0; b < graph->getB(); b++) {
        if (y[b].get(GRB_DoubleAttr_X) > 0.5) {
            time += graph->getTimePerBlock(b);
            bool was_visited = false;

            for (auto i : graph->getNodesFromBlock(b)) {
                if (visited[i]) {
                    was_visited = true;
                    break;
                }
            }

            if (!was_visited) {
                cout << "[!!!] Not visited node!" << endl;
                cout << i << endl;
                return false;
            }
        }
    }

    for (i = 0; i <= n; i++) {
        for (auto *arc : graph->getArcs(i)) {
            if (x[i][arc->getD()].get(GRB_DoubleAttr_X) > 0.8) {
                time += arc->getLength();
                if (!used_arc[i][arc->getD()]) {
                    cout << "[!!!] Not used arc!" << endl;
                    cout << i << " " << arc->getD() << endl;
                    return false;
                }
            }
        }
    }

    if (time > max_time) {
        cout << "T: " << time << " <= " << max_time << endl;
        cout << "[!!!] Resource limitation error!" << endl;
        return false;
    }

#ifndef Silence
    cout << "[***] Instance ok!!!" << endl;
#endif
    return true;
}
