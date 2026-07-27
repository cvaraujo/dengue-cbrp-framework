//
// Created by carlos on 06/07/21.
//

#include "Lagrangean.hpp"
#include "gurobi_c.h"
#include <chrono>
#include <cstdio>

Lagrangean::Lagrangean(Input *input) {
    if (input != nullptr) {
        this->input = input;
        this->boost = new BoostLibrary(input);
        this->greedyHeuristic = new GreedyHeuristic(input);
    } else
        exit(EXIT_FAILURE);
}

pair<int, double> Lagrangean::runSolverERCSPP(map<pair<int, int>, int> &x) {
    Graph *graph = this->input->getGraph();
    int N = graph->getN(), o, d, i, j, k, b;
    int T = input->getT(), B = graph->getB();

    GRBEnv env = GRBEnv();
    env.set("LogFile", "MS_mip.log");
    env.start();

    GRBModel model = GRBModel(env);
    vector<vector<GRBVar>> X = vector<vector<GRBVar>>(N + 2, vector<GRBVar>(N + 2));
    vector<vector<GRBVar>> W = vector<vector<GRBVar>>(N + 2, vector<GRBVar>(N + 2));

    // Creating Variables
    for (o = 0; o <= N; o++) {
        for (auto *arc : graph->getArcs(o)) {
            d = arc->getD();
            X[o][d] = model.addVar(0.0, GRB_INFINITY, 0, GRB_INTEGER, "x_" + to_string(o) + "_" + to_string(d));
            W[o][d] = model.addVar(0.0, T, 0, GRB_CONTINUOUS, "w");
        }
    }

    // OF
    GRBLinExpr of;
    cout << "Multi Time: " << mult_time << endl;
    for (i = 0; i <= graph->getN(); i++) {
        for (auto arc : graph->getArcs(i)) {
            j = arc->getD();
            of += X[i][j] * (-1 * mult_time * arc->getLength());
        }
    }

    for (b = 0; b < B; b++) {
        cout << "Multi Conn: " << mult_conn[b] << endl;
        for (int i : graph->getNodesFromBlock(b)) {
            for (auto arc : graph->getArcs(i)) {
                j = arc->getD();
                of += X[i][j] * mult_conn[b];
            }
        }
    }

    model.setObjective(of, GRB_MAXIMIZE);
    model.update();

    // Sink/Depot constraint
    GRBLinExpr sink, target;
    for (int i = 0; i < N; i++) {
        sink += X[N][i];
        target += X[i][N];
    }

    model.addConstr(sink == 1, "sink_constraint");
    model.addConstr(target == 1, "target_constraint");
    cout << "[***] Contraint: dummy depot" << endl;

    // Flow Conservation Constraint
    for (i = 0; i < N; i++) {
        GRBLinExpr flow_out, flow_in;

        for (auto *arc : graph->getArcs(i)) {
            if (arc->getD() >= N)
                continue;
            flow_out += X[i][arc->getD()];
        }

        for (j = 0; j < N; j++) {
            for (auto *arc : graph->getArcs(j)) {
                if (arc->getD() == i)
                    flow_in += X[j][i];
            }
        }

        flow_out += X[i][N];
        flow_in += X[N][i];
        model.addConstr(flow_in - flow_out == 0, "flow_conservation_" + to_string(i));
    }
    cout << "[***] Constraint: Flow conservation" << endl;

    // Time Constraints
    for (i = 0; i <= N; i++) {
        if (i < N)
            model.addConstr(W[N][i] == 0);

        for (auto *arc : graph->getArcs(i)) {
            j = arc->getD();
            if (j >= N)
                continue;

            for (auto *arcl : graph->getArcs(j)) {
                k = arcl->getD();
                model.addConstr(W[j][k] >= W[i][j] + (X[i][j] * arc->getLength()) - ((2 - X[i][j] - X[j][k]) * T), "t_geq_" + to_string(i) + "_" + to_string(j) + "_" + to_string(k));
            }
        }
    }

    for (i = 0; i < N; i++)
        model.addConstr(W[i][N] <= T * X[i][N], "max_time_arrives_" + to_string(i));
    cout << "[***] Constraint: Time limit" << endl;

    X[N][0].set(GRB_DoubleAttr_Start, 1.0);
    X[0][N].set(GRB_DoubleAttr_Start, 1.0);

    // model.set("TimeLimit", "300");
    model.set("OutputFlag", "1");
    model.update();
    model.write("model.lp");
    model.optimize();

    int route_time = 0.0;
    for (i = 0; i <= graph->getN(); i++)
        for (auto arc : graph->getArcs(i))
            if (X[i][arc->getD()].get(GRB_DoubleAttr_X) > 0) {
                int ip = i;
                if (i == N)
                    ip = N + 1;
                int_pair p = make_pair(ip, arc->getD());
                route_time += arc->getLength();
                if (x.find(p) != x.end())
                    x[p]++;
                else
                    x[p] = 1;
            }

    return make_pair(route_time, model.get(GRB_DoubleAttr_ObjVal));
}

pair<int, double> Lagrangean::runSHPRC(map<pair<int, int>, int> &x) {
    // Update arcs costs
    Graph *graph = input->getGraph();
    int i, j;
    double arc_cost;

    // Update arcs
    for (i = 0; i < graph->getN(); i++) {
        // Connectors multipliers
        double block_cost = 0.0;
        for (auto b : graph->getNode(i).second)
            block_cost += mult_conn[b];

        for (auto arc : graph->getArcs(i)) {
            j = arc->getD();
            arc_cost = (mult_time * arc->getLength() - block_cost);
            this->boost->update_arc_cost(i, j, arc_cost);
        }
    }

    return this->boost->run_spprc(x);
}

double Lagrangean::solve_ppl(map<pair<int, int>, int> &x, vector<int> &y) {
    Graph *graph = input->getGraph();
    double of = mult_time * T;

    pair<int, double> x_result = runSHPRC(x);
    // pair<int, double> x_result = runSolverERCSPP(x);
    double route_time = x_result.first, route_cost = x_result.second;

    if (route_cost >= numeric_limits<int>::max()) {
        cout << "[!!!] No feasible route!" << endl;
        return numeric_limits<int>::max();
    }

    // cout << "[*] Route Cost: " << route_cost << endl;
    // cout << "[*] Route Time: " << route_time << endl;
    this->curr_route_time = route_time;

    // Update Blocks profit
    vector<int> blocks, times, y_aux;
    vector<double> profit;
    for (int b = 0; b < graph->getB(); b++) {
        int time_block = graph->getTimePerBlock(b);
        double coef = graph->getCasesPerBlock(b) - mult_conn[b] - (mult_time * time_block);

        if (coef > 0) {
            blocks.push_back(b);
            profit.push_back(coef);
            times.push_back(time_block);
        }
    }

    double knapsack_cost = Knapsack::Run(y_aux, profit, times, T);

    for (auto b : y_aux) {
        auto it = blocks.begin();
        std::advance(it, b);
        y.push_back(*it);
    }

    // cout << "[*] PPL OF: " << (of + route_cost + knapsack_cost) << endl
    //      << "\t[-] OF: " << of << endl
    //      << "\t[-] Route Cost: " << route_cost << endl
    //      << "\t[-] Knapsack Cost: " << knapsack_cost << endl;
    // getchar();
    return of - route_cost + knapsack_cost;
}

int Lagrangean::bestAttendFromRoute(map<int_pair, int> &x, vector<int> &y) {
    Graph *graph = input->getGraph();
    set<int> route_blocks = graph->getBlocksFromRoute(x);
    vector<int> time, y_aux;
    vector<double> cases;
    int i, j, avail_time = this->input->getT();

    if (!route_blocks.size())
        return 0;

    // Get route time
    for (auto x_p : x) {
        int_pair p = x_p.first;
        int times_visited = x_p.second;

        i = p.first, j = p.second;
        if (i >= graph->getN() || j >= graph->getN())
            continue;

        auto arc = graph->getArc(i, j);
        avail_time -= (arc->getLength() * times_visited);
    }

    double of = 0;
    if (avail_time <= 1)
        return 0;

    // Get blocks to Knapsack
    vector<int> blocks, times;
    vector<double> profit;
    for (int b : route_blocks) {
        int time_block = graph->getTimePerBlock(b);
        double cases_pb = graph->getCasesPerBlock(b);
        if (cases_pb > 0) {
            blocks.push_back(b);
            profit.push_back(cases_pb);
            times.push_back(time_block);
        }
    }

    of = Knapsack::Run(y_aux, profit, times, avail_time);
    for (int b : y_aux) {
        auto it = route_blocks.begin();
        std::advance(it, b);
        y.push_back(*it);
    }

    // cout << "[*] Heuristic: " << of << ", With Time: " << avail_time << endl;
    // for (auto b : y)
    //   cout << "B" << b << ", ";
    // cout << endl;

    return of;
}

int Lagrangean::getOriginalObjValue(const vector<int> &y) {
    int profit = 0;
    Graph *graph = input->getGraph();
    for (int b : y)
        profit += int(graph->getCasesPerBlock(b));
    return profit;
}

int Lagrangean::getGradientTime(const map<int_pair, int> &x, const vector<int> &y) {
    Graph *graph = input->getGraph();
    int i, j;
    int gradient_time = input->getT();

    // Get route time
    for (auto x_p : x) {
        int_pair p = x_p.first;
        int times_visited = x_p.second;

        i = p.first, j = p.second;
        if (i >= graph->getN() || j >= graph->getN())
            continue;

        auto arc = graph->getArc(i, j);
        gradient_time -= (arc->getLength() * times_visited);
    }

    for (int b : y)
        gradient_time -= graph->getTimePerBlock(b);

    if (gradient_time < 0)
        is_feasible = false;

    return gradient_time;
}

void Lagrangean::getGradientConnection(vector<double> &gradient_lambda, map<int_pair, int> x, vector<int> y) {
    Graph *graph = input->getGraph();
    int b, B = graph->getB();
    map<pair<int, int>, bool> arc_used;

    for (auto arc : x) {
        int_pair a = arc.first;
        arc_used[a] = true;
    }

    for (b = 0; b < B; b++) {
        gradient_lambda[b] = 0.0;
        if (find(y.begin(), y.end(), b) != y.end())
            gradient_lambda[b] = -1.0;

        set<int> nodes = graph->getNodesFromBlock(b);

        for (int i : nodes) {
            for (auto arc : graph->getArcs(i)) {
                int_pair a = make_pair(i, arc->getD());
                if (arc_used[a])
                    gradient_lambda[b] += (double)(x[a]);
            }
        }

        if (gradient_lambda[b] < 0)
            is_feasible = false;
    }
}

double Lagrangean::getNorm(vector<double> &gradient) {
    Graph *graph = input->getGraph();
    int B = graph->getB();
    double sum = 0;

    for (int b = 0; b < B; b++) {
        if (gradient[b] != 0)
            sum += pow(gradient[b], 2);
    }
    return sqrt(sum);
}

bool Lagrangean::isFeasible() {
    if (is_feasible)
        return true;

    is_feasible = true;
    return false;
}

int Lagrangean::lagrangean_relax(string output_file, double lambda, int improve_iters, double reduction_factor, bool use_heuristic, bool use_barrier_method) {
    Graph *graph = input->getGraph();
    int progress = 0, iter = 0, N = graph->getN(), B = graph->getB(), max_iter = 5000;
    double theta_time, norm_time, theta_conn, norm_conn, obj_ppl, original_obj, heuristic_obj;
    double backup_lambda = lambda;
    this->T = input->getT();
    is_feasible = true;

    vector<double> gradient_conn = vector<double>(B, 0.0);
    double gradient_time = 0.0;

    mult_conn = vector<double>(B, 0.0);
    mult_time = 0.0;
    UB = 0, LB = 0;

    auto start = std::chrono::high_resolution_clock::now();
    for (int b = 0; b < B; b++)
        UB += graph->getCasesPerBlock(b);

    vector<int> y_heu;
    vector<int_pair> x_heu;

    if (use_heuristic) {
        LB = greedyHeuristic->SolveScenario(graph->getCasesPerBlock(), graph->getTimePerBlock(), T, y_heu);
    }

    this->initial_LB = LB;
    this->initial_UB = UB;

    obj_ppl = UB;
    if (use_barrier_method) {
        auto *bm = new DeterministicModelWalkBarrier(input);
        bm->Run(false, "3600", "EXP", false);
        mult_time = bm->getMultipliers(mult_conn);
    }

    auto end = chrono::high_resolution_clock::now();
    auto elapsed = duration_cast<chrono::seconds>(end - start);

    while (iter < max_iter && elapsed.count() < 1800) {
        map<int_pair, int> x;
        vector<int> y, y_aux;

        if (iter >= 0)
            obj_ppl = solve_ppl(x, y);
        else {
            y = y_heu;
            for (auto p : x_heu) {
                int i = p.first, j = p.second;
                if (i == N) {
                    i = N + 1;
                    x[make_pair(i, j)] = 1;
                } else {
                    if (x.find(p) != x.end())
                        x[p]++;
                    else
                        x[p] = 1;
                }
            }
        }

        if (obj_ppl < numeric_limits<int>::max()) {

            gradient_time = getGradientTime(x, y);
            getGradientConnection(gradient_conn, x, y);
            if (obj_ppl < UB) {
                UB = obj_ppl;
                progress = 0;
            } else {
                progress++;
                if (progress == improve_iters) {
                    lambda *= reduction_factor;
                    progress = 0;
                }
            }

            original_obj = getOriginalObjValue(y);
            heuristic_obj = bestAttendFromRoute(x, y_aux);
            bool feasible = isFeasible();

            if ((feasible && original_obj > LB) || heuristic_obj > LB) {
                LB = heuristic_obj;
                if (feasible)
                    LB = max(original_obj, heuristic_obj);
            }

            if ((UB - LB) < 1) {
                cout << "[!!!] Found optimal solution!" << endl
                     << "(Feasible) Lower Bound = " << LB << ", (Relaxed) Upper Bound = " << UB << endl;
                break;
            }

            norm_conn = getNorm(gradient_conn);
            norm_time = sqrt(pow(gradient_time, 2));

            if (norm_time == 0)
                theta_time = 0;
            else
                theta_time = lambda * (double(obj_ppl - LB) / pow(norm_time, 2));

            if (norm_conn == 0)
                theta_conn = 0;
            else
                theta_conn = lambda * (double(obj_ppl - LB) / pow(norm_conn, 2));

            for (int b = 0; b < B; b++) {
                mult_conn[b] = max(0.0, mult_conn[b] - (gradient_conn[b] * theta_conn));
            }

            mult_time = max(0.0, mult_time - (gradient_time * theta_time));
        } else
            break;
        iter++;
        end = chrono::high_resolution_clock::now();
        elapsed = duration_cast<chrono::seconds>(end - start);
        cout << "LB: " << LB << ", UB: " << UB << ", Lambda: " << lambda << endl;
    }

    end = chrono::high_resolution_clock::now();
    elapsed = duration_cast<chrono::seconds>(end - start);
    this->runtime = elapsed.count();

    this->WriteSolution(output_file, backup_lambda, max_iter, improve_iters, reduction_factor, iter);
    // cout << "[!!!] (Feasible) Lower Bound = " << LB << ", (Relaxed) Upper Bound = " << UB << endl;
    return LB;
}
