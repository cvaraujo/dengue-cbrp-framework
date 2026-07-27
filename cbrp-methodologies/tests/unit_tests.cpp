#include "../src/classes/Graph.hpp"
#include "../src/classes/Input.hpp"
#include "../src/common/BlockConnection.hpp"
#include "../src/common/Knapsack.hpp"
#include "../src/exact/DeterministicModel.hpp"
#include "../src/exact/StochasticModel.hpp"
#include "../src/heuristic/GreedyHeuristic.hpp"
/*
#define BOOST_TEST_MODULE your_test_module
#include <boost/test/included/unit_test.hpp>

BOOST_AUTO_TEST_CASE(testGraph)
{
  Graph graph("/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-graph.txt", 20, 10);

  // Basics
  BOOST_TEST(graph.getB() == 3);
  BOOST_TEST(graph.getN() == 3);
  BOOST_TEST(graph.getM() == 6);

  // Nodes from block
  set<int> nodes_0{0, 1, 2}, nodes_1{2}, nodes_2{2};
  BOOST_TEST(graph.getNodesFromBlock(0) == nodes_0);
  BOOST_TEST(graph.getNodesFromBlock(1) == nodes_1);
  BOOST_TEST(graph.getNodesFromBlock(2) == nodes_2);

  // Blocks from route
  set<int> blocks{0, 1, 2};
  BOOST_TEST(graph.getBlocksFromRoute({make_pair(3, 2), make_pair(2, 3)}) == blocks);

  // Arcs
  Arc *arc1 = graph.getArc(0, 1);
  Arc *arc2 = graph.getArc(3, 4);
  BOOST_TEST(arc1->getO() == 0);
  BOOST_TEST(arc1->getD() == 1);
  BOOST_TEST(arc2 == nullptr);

  // Cases per block
  BOOST_TEST(graph.getCasesPerBlock(0) == 20);
  BOOST_TEST(graph.getCasesPerBlock(1) == 10);
  BOOST_TEST(graph.getCasesPerBlock(2) == 0);

  // Time per block
  BOOST_TEST(graph.getTimePerBlock(0) == 180);
  BOOST_TEST(graph.getTimePerBlock(1) == 0);
  BOOST_TEST(graph.getTimePerBlock(2) == 0);
}

BOOST_AUTO_TEST_CASE(testKnapsack)
{
  vector<double> cases{1, 2, 3, 4};
  vector<int> time{5, 2, 3, 4}, y;
  int MT = 5;

  double result = Knapsack::Run(y, cases, time, MT);
  vector<int> correct{2, 1};

  BOOST_TEST(result == 5);
  BOOST_TEST(y == correct);
}

BOOST_AUTO_TEST_CASE(testInput)
{
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 1200;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  // Basics
  BOOST_TEST(input->getAlpha() == alpha);
  BOOST_TEST(input->getT() == T);
  BOOST_TEST(input->getS() == 4);

  // Scenarios
  vector<double> cases_0{10, 21, 100};
  vector<double> cases_1{10, 21, 0};
  BOOST_TEST(input->getScenario(0).getCases() == cases_0);
  BOOST_TEST(input->getScenario(1).getCases() == cases_1);
  BOOST_TEST(input->getScenario(0).getProbability() == 0.25);
}

BOOST_AUTO_TEST_CASE(testShortestPath)
{
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 1200;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  ShortestPath *sp = input->getShortestPath();

  // Shortest path ST
  vector<int> path;
  int cost = sp->ShortestPathST(0, 2, path);
  vector<int> correct_path{0, 2};

  BOOST_TEST(cost == 30);
  BOOST_TEST(path == correct_path);

  // Djikstra layered DAG
  vector<int> pred;
  vector<vector<Arc>> dag;
  dag.push_back(vector<Arc>({Arc{0, 1, 0, 0}, Arc{0, 2, 0, 0}}));
  dag.push_back(vector<Arc>({Arc{1, 3, 10, 0}}));
  dag.push_back(vector<Arc>({Arc{2, 3, 10, 0}}));
  dag.push_back(vector<Arc>({Arc{3, 4, 0, 0}}));
  dag.push_back(vector<Arc>());

  correct_path = {0, 0, 0, 1, 3};
  cost = sp->DijkstraLayeredDAG(dag, 5, 0, 4, pred);

  BOOST_TEST(cost == 10);
  BOOST_TEST(pred == correct_path);

  //
  set<int> nodes;
  map<int, map<int, bool>> arcs;
  cost = sp->SHPBetweenBlocks(2, 0, nodes, arcs);
  set<int> correct_nodes{0};

  BOOST_TEST(cost == 0);
  BOOST_TEST(arcs.empty());

  BOOST_TEST(nodes == correct_nodes);
}

BOOST_AUTO_TEST_CASE(testBlockConnection)
{
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/tests/test_instance/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 1200;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  BlockConnection *bc = input->getBlockConnection();

  // Static function
  vector<int> a{1, 2, 3, 4};
  string correct = "1234";
  string wrong = "123";
  string result = bc->GenerateStringFromIntVector(a);

  BOOST_TEST(result == correct);
  BOOST_TEST(result != wrong);

  // Heuristic Block Connection
  string key = "012";
  vector<int> blocks = {0, 1, 2};
  vector<int> corect_path = {1, 0, 1};
  int cost = bc->HeuristicBlockConnection(input->getGraph(), input->getShortestPath(), blocks, key);

  BOOST_TEST(cost == 0);
  BOOST_TEST(bc->getBlocksAttendCost(key) == 0);
  BOOST_TEST(bc->getBlocksAttendPath(key) == corect_path);
}

BOOST_AUTO_TEST_CASE(testDeterministicModelCompact)
{
  cout << "Deterministic Model Compact" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  DeterministicModel *dm = new DeterministicModel(input);
  Solution sol = dm->Run(false, "60", "MTZ", false);

  sol.WriteSolution("result_deterministic_mtz.txt");

  BOOST_TEST(sol.getOf() == 80);
}

BOOST_AUTO_TEST_CASE(testDeterministicModelExp)
{
  cout << "Deterministic Model Exponential" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 1000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  DeterministicModel *dm = new DeterministicModel(input);
  Solution sol = dm->Run(false, "60", "EXP", false);

  sol.WriteSolution("result_deterministic_exp.txt");

  BOOST_TEST(sol.getOf() == 68);
}

BOOST_AUTO_TEST_CASE(testDeterministicModelExpFrac)
{
  cout << "Deterministic Model Exponential Frac. Cuts" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  DeterministicModel *dm = new DeterministicModel(input);
  Solution sol = dm->Run(false, "60", "EXP", true);

  sol.WriteSolution("result_deterministic_exp_frac.txt");

  BOOST_TEST(sol.getOf() == 80);
}

BOOST_AUTO_TEST_CASE(testStochasticModelCompact)
{
  cout << "Stochastic Model Compact" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  StochasticModel *sm = new StochasticModel(input);
  Solution sol = sm->Run(false, "60", "MTZ", false, Solution());

  sol.WriteSolution("result_stochastic_mtz.txt");

  BOOST_TEST(sol.getOf() == 241);
}

BOOST_AUTO_TEST_CASE(testStochasticModelExp)
{
  cout << "Stochastic Model Exponential" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  StochasticModel *sm = new StochasticModel(input);
  Solution sol = sm->Run(false, "60", "EXP", false, Solution());

  sol.WriteSolution("result_stochastic_mtz.txt");

  BOOST_TEST(sol.getOf() == 241);
}

BOOST_AUTO_TEST_CASE(testStochasticModelExpFrac)
{
  cout << "Stochastic Model Exponential Frac. Cuts" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  StochasticModel *sm = new StochasticModel(input);
  Solution sol = sm->Run(false, "60", "EXP", true, Solution());

  sol.WriteSolution("result_stochastic_mtz.txt");

  BOOST_TEST(sol.getOf() == 241);
}

BOOST_AUTO_TEST_CASE(checkStochasticModels)
{
  cout << "Stochastic Model Exponential Frac. Cuts" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/alto-santo-200-1.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/scenarios-alto-santo-200-1.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  StochasticModel *sm = new StochasticModel(input);
  StochasticModel *sm2 = new StochasticModel(input);
  StochasticModel *sm3 = new StochasticModel(input);

  Solution sol = sm->Run(false, "600", "MTZ", false, Solution());
  Solution sol2 = sm2->Run(false, "600", "EXP", false, Solution());
  Solution sol3 = sm3->Run(false, "600", "EXP", true, Solution());

  sol.WriteSolution("result_stochastic_mtz.txt");
  sol2.WriteSolution("result_stochastic_exp.txt");
  sol3.WriteSolution("result_stochastic_exp_frac.txt");

  cout << sol.getOf() << ", " << sol2.getOf() << ", " << sol3.getOf() << endl;

  BOOST_TEST(round(sol.getOf()) == round(sol2.getOf()));
  BOOST_TEST(round(sol3.getOf()) == round(sol2.getOf()));
}

BOOST_AUTO_TEST_CASE(testGreedyHeuristicFullTime)
{
  cout << "[!] Stochastic Greedy Heuristic" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 12000;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  GreedyHeuristic *gh = new GreedyHeuristic(input);
  vector<vector<int_pair>> x;
  vector<vector<int_pair>> y;
  double of = gh->Run(0.01, 1000, false, x, y);

  BOOST_TEST(round(of) == round(241));
}

BOOST_AUTO_TEST_CASE(testGreedyHeuristicAvg)
{
  cout << "[!] Stochastic Greedy Heuristic" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 600;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  GreedyHeuristic *gh = new GreedyHeuristic(input);
  vector<vector<int_pair>> x;
  vector<vector<int_pair>> y;
  double of = gh->Run(0.01, 1000, true, x, y);

  BOOST_TEST(round(of) == round(196.45000000000005));
}

BOOST_AUTO_TEST_CASE(testDeterministicModels)
{
  cout << "Stochastic Model Exponential Frac. Cuts" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "";
  int graph_adapt = 1, default_vel = 20, neblize_vel = 10, T = 600;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  DeterministicModel *sm = new DeterministicModel(input);
  DeterministicModel *sm2 = new DeterministicModel(input);
  DeterministicModel *sm3 = new DeterministicModel(input);

  Solution sol = sm->Run(false, "600", "MTZ", false);
  sol.WriteSolution("result_deterministic_mtz.txt");

  Solution sol2 = sm2->Run(false, "600", "EXP", false);
  sol2.WriteSolution("result_deterministic_exp.txt");

  Solution sol3 = sm3->Run(false, "600", "EXP", true);
  sol2.WriteSolution("result_deterministic_exp_frac.txt");

  cout << sol.getOf() << ", " << sol2.getOf() << ", " << sol3.getOf() << endl;

  BOOST_TEST(round(sol.getOf()) == round(sol2.getOf()));
  BOOST_TEST(round(sol3.getOf()) == round(sol2.getOf()));
}

BOOST_AUTO_TEST_CASE(testStochasticModelCompact)
{
  cout << "Stochastic Model Exponential Frac. Cuts" << endl;
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/alto-santo-200-1.txt";
  //  /home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/scenarios-alto-santo-300-1.txt
  // string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/scenarios-alto-santo-200-1.txt";
  int graph_adapt = 0, default_vel = 20, neblize_vel = 10, T = 600;
  double alpha = 0.8;

  Input *input = new Input(file_graph, file_scenarios, graph_adapt, default_vel, neblize_vel, T, alpha);

  GreedyHeuristic *gh = new GreedyHeuristic(input);
  // StochasticModel *sm = new StochasticModel(input);
  // StochasticModel *sm2 = new StochasticModel(input);
  // StochasticModel *sm3 = new StochasticModel(input);

  Solution g_sol = gh->Run(0.01, 50, false);

  cout << g_sol.getOf() << endl;
  // Solution sol = sm->Run(true, "120", "MTZ", false, g_sol);
  // sol.WriteSolution("result_stochastic_mtz.txt");

  // Solution sol2 = sm2->Run(true, "120", "EXP", false, g_sol);
  // sol2.WriteSolution("result_stochastic_exp.txt");

  // Solution sol3 = sm3->Run(true, "120", "EXP", true, g_sol);
  // sol3.WriteSolution("result_stochastic_exp_frac.txt");

  // cout << g_sol.getOf() << " <= " << sol.getOf() << ", " << sol2.getOf() << ", " << sol3.getOf() << endl;

  // BOOST_TEST(round(sol.getOf()) == round(sol2.getOf()));
  // BOOST_TEST(round(sol3.getOf()) == round(sol2.getOf()));
}

BOOST_AUTO_TEST_CASE(testWalkAdaptMTZModel)
{
  cout << "[*] Testing walkAdaptMTZModel function" << endl;

  // Test 1: Graph with all positive blocks
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int default_vel = 20, neblize_vel = 10, T = 1200;
  double alpha = 0.8;
  bool use_preprocessing = false, is_trail = true, walk_mtz_model = true;

  Input *input = new Input(file_graph, file_scenarios, use_preprocessing, is_trail,
                          walk_mtz_model, default_vel, neblize_vel, T, alpha);

  Graph *graph = input->getGraph();

  // Validate basic properties
  int N = graph->getN();
  int M = graph->getM();
  int B = graph->getB();

  cout << "[*] After walkAdaptMTZModel: N=" << N << ", M=" << M << ", B=" << B << endl;

  // Test 1: All nodes should have sequential IDs from 0 to N-1
  for (int i = 0; i < N; ++i) {
    auto node = graph->getNode(i);
    BOOST_TEST(node.first == i); // Node ID should match index
    BOOST_TEST(!node.second.empty() || i == N); // Should belong to at least one block (except depot)
  }

  // Test 2: All blocks should have sequential IDs from 0 to B-1
  for (int b = 0; b < B; ++b) {
    BOOST_TEST(graph->getCasesPerBlock(b) > 0.0); // All blocks should have positive cases
    BOOST_TEST(graph->getTimePerBlock(b) >= 0); // All blocks should have valid time
    BOOST_TEST(!graph->getNodesFromBlock(b).empty()); // Each block should have at least one node
  }

  // Test 3: Graph should be complete (all pairs connected except self-loops)
  int expected_arcs = N * (N - 1); // Complete graph without self-loops
  int actual_arcs = 0;

  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      if (i != j) {
        Arc *arc = graph->getArc(i, j);
        if (arc != nullptr) {
          actual_arcs++;
          // Test 4: Arc properties are valid
          BOOST_TEST(arc->getO() == i);
          BOOST_TEST(arc->getD() == j);
          BOOST_TEST(arc->getLength() >= 0);
          BOOST_TEST(arc->getLength() < INF);
        }
      }
    }
  }

  cout << "[*] Expected arcs (complete): " << expected_arcs << ", Actual: " << actual_arcs << endl;
  BOOST_TEST(actual_arcs == expected_arcs);

  // Test 5: Scenarios should be updated with new block mapping
  for (int s = 0; s < input->getS(); ++s) {
    const auto &scenario_cases = input->getCasesFromScenario(s);
    BOOST_TEST(scenario_cases.size() == static_cast<size_t>(B));

    // Check that scenario cases are consistent
    for (int b = 0; b < B; ++b) {
      BOOST_TEST(scenario_cases[b] >= 0.0);
    }
  }

  // Test 6: Block-to-node mapping consistency
  for (int b = 0; b < B; ++b) {
    const auto &nodes_in_block = graph->getNodesFromBlock(b);
    for (int node : nodes_in_block) {
      BOOST_TEST(node >= 0);
      BOOST_TEST(node < N);

      // Verify that node actually contains this block
      const auto &node_blocks = graph->getNode(node).second;
      BOOST_TEST(node_blocks.find(b) != node_blocks.end());
    }
  }

  // Test 7: ShortestPath should work correctly on new graph
  ShortestPath *sp = input->getShortestPath();
  BOOST_TEST(sp != nullptr);

  for (int i = 0; i < N; ++i) {
    for (int j = 0; j < N; ++j) {
      if (i != j) {
        int dist = sp->ShortestPathST(i, j);
        BOOST_TEST(dist >= 0);
        BOOST_TEST(dist < INF);
      }
    }
  }

  // Test 8: BlockConnection should work correctly
  BlockConnection *bc = input->getBlockConnection();
  BOOST_TEST(bc != nullptr);

  vector<vector<int>> b2b_cost = bc->getBlock2BlockCost();
  BOOST_TEST(b2b_cost.size() == static_cast<size_t>(B));

  cout << "[*] All walkAdaptMTZModel tests passed!" << endl;

  delete input;
}

BOOST_AUTO_TEST_CASE(testWalkAdaptMTZModelConsistency)
{
  cout << "[*] Testing walkAdaptMTZModel graph transformation consistency" << endl;

  // Create two inputs: one without walk_mtz_model and one with
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int default_vel = 20, neblize_vel = 10, T = 1200;
  double alpha = 0.8;

  // Without walk adaptation
  Input *input_original = new Input(file_graph, file_scenarios, false, true,
                                    false, default_vel, neblize_vel, T, alpha);

  // With walk adaptation
  Input *input_adapted = new Input(file_graph, file_scenarios, false, true,
                                   true, default_vel, neblize_vel, T, alpha);

  Graph *graph_orig = input_original->getGraph();
  Graph *graph_adap = input_adapted->getGraph();

  int N_orig = graph_orig->getN();
  int N_adap = graph_adap->getN();
  int B_orig = graph_orig->getB();
  int B_adap = graph_adap->getB();

  cout << "[*] Original: N=" << N_orig << ", B=" << B_orig << endl;
  cout << "[*] Adapted: N=" << N_adap << ", B=" << B_adap << endl;

  // Test: Number of blocks should be same or reduced (only positive blocks kept)
  BOOST_TEST(B_adap <= B_orig);

  // Test: Number of nodes should be same or reduced (only nodes in positive blocks kept)
  BOOST_TEST(N_adap <= N_orig);

  // Test: Total cases should be preserved (sum of all block cases)
  double total_cases_orig = 0.0, total_cases_adap = 0.0;

  for (int b = 0; b < B_orig; ++b) {
    if (graph_orig->getCasesPerBlock(b) > 0.0) {
      total_cases_orig += graph_orig->getCasesPerBlock(b);
    }
  }

  for (int b = 0; b < B_adap; ++b) {
    total_cases_adap += graph_adap->getCasesPerBlock(b);
  }

  cout << "[*] Total cases - Original: " << total_cases_orig << ", Adapted: " << total_cases_adap << endl;
  BOOST_TEST(abs(total_cases_orig - total_cases_adap) < 0.01); // Should be equal

  // Test: Adapted graph should be complete
  int expected_complete = N_adap * (N_adap - 1);
  int actual_arcs = 0;

  for (int i = 0; i < N_adap; ++i) {
    actual_arcs += static_cast<int>(graph_adap->getArcs(i).size());
  }

  cout << "[*] Complete graph check - Expected: " << expected_complete << ", Actual: " << actual_arcs << endl;
  BOOST_TEST(actual_arcs >= expected_complete); // Should have at least complete graph arcs

  // Test: Distances in adapted graph should be valid shortest paths
  ShortestPath *sp_orig = input_original->getShortestPath();
  ShortestPath *sp_adap = input_adapted->getShortestPath();

  // Sample a few node pairs to verify distances
  for (int i = 0; i < min(3, N_adap); ++i) {
    for (int j = 0; j < min(3, N_adap); ++j) {
      if (i != j) {
        int dist_adap = sp_adap->ShortestPathST(i, j);
        BOOST_TEST(dist_adap >= 0);
        BOOST_TEST(dist_adap < INF);
      }
    }
  }

  cout << "[*] All consistency tests passed!" << endl;

  delete input_original;
  delete input_adapted;
}
*/
int main(int argc, const char *argv[]) {
    // string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/alto-santo-300-1.txt";
    // string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/simulated-alto-santo/scenarios-alto-santo-300-1.txt";
    string file_graph = "/home/araujo/Documents/cbrp-methodologies/tests/instances-random/graph-limoeiro-random.txt";
    string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/tests/instances-random/scenarios-limoeiro-random.txt";

    // string file_scenarios = "";
    int default_vel = 20, neblize_vel = 10, T = 400;
    double alpha = 0.8;
    bool use_preprocessing = false, is_trail = true, walk_mtz_graph = false;

    Input *input = new Input(file_graph, file_scenarios, use_preprocessing, is_trail, walk_mtz_graph, default_vel, neblize_vel, T, alpha);
    DeterministicModel *dm = new DeterministicModel(input);
    Solution sol = dm->Run(false, "120", "EXP", false);
    // sol.WriteSolution("result_stochastic_exp.txt");
    // for (auto scn : input->getScenarios())
    // {
    //   cout << "Scenario: " << scn.getProbability() << endl;
    //   for (int b = 0; b < input->getGraph()->getB(); b++)
    //   {
    //     if (scn.getCasesPerBlock(b) > 0)
    //     {
    //       cout << b << ": " << scn.getCasesPerBlock(b) << endl;
    //     }
    //   }
    // }
    // input->getGraph()->ShowGraph();

    // GreedyHeuristic *gh = new GreedyHeuristic(input);
    // StochasticModel *sm = new StochasticModel(input);
    // // StochasticModel *sm2 = new StochasticModel(input);
    // // StochasticModel *sm3 = new StochasticModel(input);
    // Solution g_sol = gh->Run(0.01, 50, false);

    // cout << g_sol.getOf() << endl;
    // Solution sol = sm->Run(true, "120", "MTZ", false, g_sol);
    // sol.WriteSolution("result_stochastic_mtz.txt");

    // // Solution sol2 = sm2->Run(true, "120", "EXP", false, g_sol);
    // // sol2.WriteSolution("result_stochastic_exp.txt");

    // // Solution sol3 = sm3->Run(true, "120", "EXP", true, g_sol);
    // // sol3.WriteSolution("result_stochastic_exp_frac.txt");

    // cout << g_sol.getOf() << " <= " << sol.getOf() << endl; //<< ", " << sol2.getOf() << ", " << sol3.getOf() << endl;
    return 0;
}
