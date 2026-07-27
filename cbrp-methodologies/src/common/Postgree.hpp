//
// Created by Carlos on 25/05/2025.
//

#ifndef SCBRP_POSTGREE_H
#define SCBRP_POSTGREE_H

#include "../classes//Solution.hpp"
#include "../classes/Parameters.hpp"
#include "pqxx/pqxx"
#include <unordered_map>

class DataAccess {

    unique_ptr<pqxx::connection> conn;

  public:
    explicit DataAccess() {
        try {
            this->conn = std::make_unique<pqxx::connection>("dbname=dengue-propagation user=postgres password=postgres host=localhost port=5432");

            if (conn->is_open()) {
                std::cout << "Connected to database: " << conn->dbname() << "\n";
            } else {
                throw std::runtime_error("Can't open database");
            }
        } catch (const std::exception &e) {
            std::cerr << "Connection failed: " << e.what() << "\n";
            throw;
        }
    };

    ~DataAccess() {
        if (conn && conn->is_open()) {
            conn.reset();
            std::cout << "Disconnected.\n";
        }
    }

    std::unordered_map<int, std::unordered_map<int, double>> GetCasesFromScenarios(const int exec_id) {
        try {
            if (!conn->is_open()) {
                this->conn = std::make_unique<pqxx::connection>("dbname=dengue-propagation user=postgres password=postgres host=localhost port=5432");
            }

            pqxx::work txn(*conn);
            pqxx::result result = txn.exec_params(
                "SELECT living_place, simulation_id FROM metrics_infected_people WHERE execution_id = $1",
                exec_id);

            std::unordered_map<int, std::unordered_map<int, double>> scenario_block_cases;
            for (const auto &row : result) {
                int living_place = row["living_place"].as<int>();
                int simulation_id = row["simulation_id"].as<int>();

                if (scenario_block_cases.find(simulation_id) == scenario_block_cases.end()) {
                    scenario_block_cases[simulation_id] = std::unordered_map<int, double>();
                }

                if (scenario_block_cases[simulation_id].find(living_place) == scenario_block_cases[simulation_id].end()) {
                    scenario_block_cases[simulation_id][living_place] = 0;
                }

                scenario_block_cases[simulation_id][living_place] += 1;
            }

            txn.commit();
            return scenario_block_cases;

        } catch (const std::exception &e) {
            std::cerr << "Error getting cases from scenarios: " << e.what() << "\n";
            return {};
        }
    }

    void InsertSolutionIntoDatabase(int id, Solution *solution) {
        pqxx::work txn(*conn);

        double of = solution->getOf();
        string blocks;
        for (int b : solution->getRouteFromScenario(0)->getSequenceOfAttendingBlocks()) {
            blocks += to_string(b) + ",";
        }

        pqxx::result result = txn.exec_params(
            "INSERT INTO blocks_to_nebulize (solution_id, blocks, deterministic_of, stochastic_of) VALUES ($1, $2, $3, $4)",
            id, blocks, of, of);
        txn.commit();
    }
};

#endif // SCBRP_POSTGREE_H
