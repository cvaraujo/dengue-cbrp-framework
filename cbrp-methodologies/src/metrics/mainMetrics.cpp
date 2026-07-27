#include <sys/stat.h>
#include <string>
#include <chrono>
#include "../classes/Input.hpp"
#include "../exact/DeterministicModel.hpp"
#include "../exact/StochasticModel.hpp"

Solution solveDM(Input *input)
{
  DeterministicModel dm(input);
  dm.createVariables();
  dm.initModel("MTZ");
  dm.solveCompact("600");
  return dm.getSolution();
}

Solution solveSM(Input *input)
{
  StochasticModel sm(input);
  sm.createVariables();
  sm.initModel("MTZ");
  sm.solveCompact("600");
  return sm.getSolution();
}

Solution solveSMfromStartSol(Input *input, Solution start_sol, string result_file)
{
  StochasticModel sm(input);
  sm.createVariables();
  sm.initModel("MTZ");
  sm.setStartSolution(start_sol);

  sm.solveCompact("600");
  return sm.getSolution();
}

float getRealOfFromSolution(int s, vector<double> cases_fs, vector<double> cases_ss, Solution sol, float alpha)
{
  float of = 0.0;
  auto Y = sol.getY();

  // First Stage Solution
  for (auto b : Y[0])
    of += cases_fs[b] + alpha * cases_ss[b];

  // Second Stage Solution
  for (auto b : Y[s])
  {
    if (find(Y[0].begin(), Y[0].end(), b) == Y[0].end())
      of += float(cases_ss[b]);
    else
      of += (1.0 - alpha) * float(cases_ss[b]);
  }

  return of;
}

float WaitNSeeResults(Input *input, float alpha)
{
  Input *input1 = new Input(*input);
  Graph *g1 = new Graph(*input1->getGraph());

  float of = 0.0;

  // Reset scenarios from G1
  input1->setS(1);
  input1->setScenarios(vector<Scenario>(1));
  float probability = 1.0 / float(input->getS());

  for (int s = 0; s < input->getS(); s++)
  {
    Scenario scn = input->getScenario(s);
    scn.setProbability(1.0);
    input1->setScenario(0, scn);

    Solution sol = solveSM(input1);
    of += probability * getRealOfFromSolution(1, input->getGraph()->getCasesPerBlock(), input->getScenario(s)->getCases(), sol, alpha);
  }

  return of;
}

float ExpectationExpectedValueResults(Input *input, float alpha)
{
  Input *input1 = new Input(*input);
  Graph *g2 = new Graph(*input1->getGraph());
  Graph *g1 = input1->getGraph();
  float of = 0.0;

  // Reset scenarios from G1
  input1->setS(1);
  input1->setScenarios(vector<Scenario>(1));
  double probability = 1.0;

  // Construct the average Scenario
  vector<double> cases_per_block = vector<double>(g1->getB(), 0);
  for (int b = 0; b < g1->getB(); b++)
  {
    float avg_cases = 0.0;
    for (int s = 0; s < input->getS(); s++)
      avg_cases += input->getScenario(s)->getCasesPerBlock(b);
    cases_per_block[b] = avg_cases / float(input->getS());
  }

  // Put AVG Scenario in G1
  Scenario avg_scenario = Scenario(probability, cases_per_block);
  input1->setScenario(0, avg_scenario);

  // Get First Stage Solution
  Solution first_stage_sol = solveSM(input1);

  // Compute second stage solutions
  probability = 1.0 / float(input->getS());
  input1->setS(0);

  for (int s = 0; s < input->getS(); s++)
  {
    // Update cases in Scenario s
    Scenario scn = input->getScenario(s);
    g1->setCasesPerBlock(scn.getCases());
    bool all_zero = true;

    auto fs = first_stage_sol.getY()[0];

    for (int block : fs)
      g1->setCasesPerBlock(block, scn.getCasesPerBlock(block) * (1.0 - alpha));

    for (int b = 0; b < g1->getB(); b++)
      if (g1->getCasesPerBlock(b) > 0)
      {
        all_zero = false;
        break;
      }

    // Solve Second Stage
    Solution s2 = Solution();
    auto oldY = first_stage_sol.getY();

    if (!all_zero)
    {
      s2 = solveDM(input1);
      oldY[1] = s2.getY()[0];
    }
    else
      oldY[1] = vector<int>();

    first_stage_sol.setY(oldY);

    // Get Real Objective value
    of += probability * getRealOfFromSolution(1, g2->getCasesPerBlock(), input->getScenario(s)->getCases(), first_stage_sol, alpha);
  }

  return of;
}

float StochasticModelResults(Input *input, float alpha, bool start_from_sol, Solution start_solution)
{
  // Get First Stage Solution
  int S = input->getS();
  float probability = 1.0 / float(S), of = 0.0;
  Solution sol = solveSM(input);

  for (int s = 0; s < S; s++)
    of += probability * getRealOfFromSolution(s + 1, input->getGraph()->getCasesPerBlock(), input->getScenario(s)->getCases(), sol, alpha);
  return of;
}

float DeterministicModelResults(Input *input, float alpha)
{
  Input *input1 = new Input(*input);
  Graph *g1 = input1->getGraph();
  Graph *g2 = new Graph(*input1->getGraph());
  input1->setS(0);

  float of = 0.0;
  float probability = 1.0 / float(input->getS());

  Solution fs = solveDM(input1);

  for (int s = 0; s < input->getS(); s++)
  {
    // Update cases in Scenario s
    Scenario scn = input->getScenario(s);

    g1->setCasesPerBlock(scn.getCases());
    bool all_zero = true;

    auto Y = fs.getY()[0];
    for (auto block : Y)
      g1->setCasesPerBlock(block, scn.getCasesPerBlock(block) * (1.0 - alpha));

    for (int b = 0; b < g1->getB(); b++)
    {
      if (g1->getCasesPerBlock(b) > 0)
      {
        all_zero = false;
        break;
      }
    }

    // Solve Second Stage
    Solution s2 = Solution();
    auto oldY = fs.getY();

    if (!all_zero)
    {
      s2 = solveDM(input1);
      oldY.push_back(s2.getY()[0]);
    }
    else
      oldY.push_back(vector<int>());

    s2.setY(oldY);

    // Get Real Objective value
    of += probability * getRealOfFromSolution(1, g2->getCasesPerBlock(), input->getScenario(s)->getCases(), s2, alpha);
  }

  return of;
}

int main(int argc, const char *argv[])
{
  string file_graph = "/home/araujo/Documents/cbrp-methodologies/tests/instances-random/graph-limoeiro-300-random-5.txt";
  string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/tests/instances-random/scenarios-limoeiro-300-random-5.txt";
  // string file_graph = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-graph.txt";
  // string file_scenarios = "/home/araujo/Documents/cbrp-methodologies/instances/test/test-scenarios.txt";
  int default_vel = 20, neblize_vel = 10, T = 3000;
  double alpha = 0.8;
  bool use_preprocessing = true, is_trail = true, block_2_block_graph = false;

  Input *input = new Input(file_graph, file_scenarios, use_preprocessing, is_trail, block_2_block_graph, default_vel, neblize_vel, T, alpha);
  cout << "Input constructed Successfully!" << endl;

  Input *inpEEV = new Input(*input);
  inpEEV->setGraph(new Graph(*input->getGraph()));

  Input *inpWS = new Input(*input);
  inpWS->setGraph(new Graph(*input->getGraph()));

  float sm = StochasticModelResults(input, alpha, false, Solution());
  float ws = WaitNSeeResults(inpWS, alpha);
  float ev = ExpectationExpectedValueResults(inpEEV, alpha);
  float dt = DeterministicModelResults(new Input(*input), alpha);

  cout << "DT: " << dt << ", EEV: " << ev << ", " << "RP: " << sm << ", WS: " << ws << endl;

  // // File name
  // std::string filename = "analysis.txt";

  // // Open the file in append mode
  // std::ofstream file;
  // file.open(filename, std::ios::app);

  // // Check if the file is open
  // if (!file.is_open())
  // {
  //   std::cerr << "Failed to open the file." << std::endl;
  //   return 1;
  // }

  // // Write to the file
  // file << "DT: " << dt << " EEV: " << ev << " " << "RP: " << sm << " WS: " << ws << std::endl;

  // // Close the file
  // file.close();
  return 0;
}
