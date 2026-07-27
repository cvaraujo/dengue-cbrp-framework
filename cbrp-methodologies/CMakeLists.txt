cmake_minimum_required(VERSION 3.10)
project(cbrp)

# Configurações do compilador
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_BUILD_TYPE Release)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -DIL_STD -O3 -ffast-math -funroll-loops -march=native -DNDEBUG -DSilence")

# ==================
# Localizar Gurobi
# ==================
if(DEFINED ENV{GUROBI_HOME})
    set(GUROBI_HOME "$ENV{GUROBI_HOME}")
else()
    file(GLOB GUROBI_CANDIDATES "/opt/gurobi*/linux64")
    if(GUROBI_CANDIDATES)
        list(SORT GUROBI_CANDIDATES)
        list(GET GUROBI_CANDIDATES -1 GUROBI_HOME)
    endif()
endif()

if(NOT GUROBI_HOME)
    message(FATAL_ERROR "Gurobi não encontrado. Defina GUROBI_HOME ou instale em /opt/gurobi*/")
endif()

find_path(GUROBI_INCLUDE_DIR gurobi_c.h PATHS "${GUROBI_HOME}/include" NO_DEFAULT_PATH)
find_library(GUROBI_CXX_LIBRARY gurobi_c++ PATHS "${GUROBI_HOME}/lib" NO_DEFAULT_PATH)
file(GLOB GUROBI_C_LIBRARY "${GUROBI_HOME}/lib/libgurobi[0-9][0-9]*.so")
list(FILTER GUROBI_C_LIBRARY EXCLUDE REGEX "_light\\.so$")

if(NOT GUROBI_INCLUDE_DIR OR NOT GUROBI_CXX_LIBRARY OR NOT GUROBI_C_LIBRARY)
    message(FATAL_ERROR "Gurobi encontrado em ${GUROBI_HOME} mas headers/libs ausentes")
endif()
list(GET GUROBI_C_LIBRARY 0 GUROBI_C_LIBRARY)
message(STATUS "Gurobi encontrado: ${GUROBI_HOME}")
message(STATUS "  C lib:   ${GUROBI_C_LIBRARY}")
message(STATUS "  C++ lib: ${GUROBI_CXX_LIBRARY}")

# ==================
# Localizar Boost
# ==================
file(GLOB BOOST_CANDIDATES "/opt/boost_*")
if(BOOST_CANDIDATES)
    list(SORT BOOST_CANDIDATES)
    list(GET BOOST_CANDIDATES -1 BOOST_LOCAL)
    set(BOOST_ROOT "${BOOST_LOCAL}")
    set(BOOST_INCLUDEDIR "${BOOST_LOCAL}")
endif()
find_package(Boost REQUIRED)
message(STATUS "Boost encontrado: ${Boost_INCLUDE_DIRS}")

# ==================
# Localizar LEMON
# ==================
file(GLOB LEMON_CANDIDATES "/opt/lemon-*")
if(LEMON_CANDIDATES)
    list(SORT LEMON_CANDIDATES)
    list(GET LEMON_CANDIDATES -1 LEMON_ROOT)
endif()

find_path(LEMON_INCLUDE_DIR lemon/core.h PATHS "${LEMON_ROOT}" NO_DEFAULT_PATH)
find_library(LEMON_LIBRARY emon PATHS "${LEMON_ROOT}/lemon" NO_DEFAULT_PATH)

if(NOT LEMON_INCLUDE_DIR OR NOT LEMON_LIBRARY)
    message(FATAL_ERROR "LEMON não encontrado. Instale em /opt/lemon-*/")
endif()
message(STATUS "LEMON encontrado: ${LEMON_ROOT}")

# Diretórios de includes
include_directories(
    ${GUROBI_INCLUDE_DIR}
    ${Boost_INCLUDE_DIRS}
    ${LEMON_INCLUDE_DIR}
)

# Fontes comuns
set(SOURCES_MAIN
    src/classes/Arc.hpp
    src/classes/Parameters.hpp
    src/classes/Route.hpp
    src/classes/Route.cpp
    src/classes/Graph.hpp
    src/classes/Graph.cpp
    src/classes/Input.hpp
    src/classes/Input.cpp
    src/classes/Solution.hpp
    src/common/ShortestPath.hpp
    src/common/ShortestPath.cpp
    src/common/BlockConnection.hpp
    src/common/BlockConnection.cpp
    src/common/Knapsack.hpp
    src/common/BoostLibrary.hpp
    src/common/BoostLibrary.cpp
)

# Fontes dos modelos
set(SOURCES_DETERMINISTIC_MODEL
    src/exact/DeterministicModel.hpp
    src/exact/DeterministicModel.cpp
    src/exact/DeterministicModelWalk.hpp
    src/exact/DeterministicModelWalk.cpp
)

set(SOURCES_STOCHASTIC_MODEL
    src/exact/StochasticModel.hpp
    src/exact/StochasticModel.cpp
    src/exact/StochasticModelWalk.hpp
    src/exact/StochasticModelWalk.cpp
    main-stochastic-model.cpp
)

# Heurísticas e métodos adicionais
set(SOURCES_DETERMINISTIC_HEURISTIC
    src/heuristic/stochastic/StartSolution.hpp
    src/heuristic/GreedyHeuristic.hpp
    src/heuristic/GreedyHeuristic.cpp
    main-det-greedy-heuristic.cpp
)

set(SOURCES_DETERMINISTIC_GREEDY_HEURISTIC
    src/heuristic/GreedyHeuristic.hpp
    src/heuristic/GreedyHeuristic.cpp
    main-det-greedy-heuristic.cpp
)

set(SOURCES_DETERMINISTIC_LAGRANGEAN
    src/heuristic/stochastic/StartSolution.hpp
    src/heuristic/GreedyHeuristic.hpp
    src/heuristic/GreedyHeuristic.cpp
    src/exact/DeterministicModelWalkBarrierMethod.hpp
    src/exact/DeterministicModelWalkBarrierMethod.cpp
    src/heuristic/Lagrangean.hpp
    src/heuristic/Lagrangean.cpp
    main-lagrangean.cpp
)

set(SOURCES_STOCHASTIC_HEURISTIC
    src/heuristic/metaheuristics/SimulatedAnnealing.hpp
    src/heuristic/stochastic/Utils.hpp
    src/heuristic/stochastic/LocalSearch.hpp
    src/heuristic/stochastic/LocalSearch.cpp
    src/heuristic/stochastic/StartSolution.hpp
    src/heuristic/GreedyHeuristic.hpp
    src/heuristic/GreedyHeuristic.cpp
)

set(SOURCES_SIMHEURISTIC
    src/common/Postgree.hpp
    src/simheuristic/simheuristic.hpp
    main-simheuristic.cpp
)

# ======================
# Criação dos executáveis
# ======================

# Deterministic Model
add_executable(cbrp-det
    ${SOURCES_MAIN}
    ${SOURCES_DETERMINISTIC_MODEL}
    main-deterministic-model.cpp
)

# Stochastic Model
add_executable(cbrp-stoc
    ${SOURCES_MAIN}
    ${SOURCES_STOCHASTIC_MODEL}
)

# Deterministic Heuristic
add_executable(cbrp-det-heur
    ${SOURCES_MAIN}
    ${SOURCES_DETERMINISTIC_HEURISTIC}
)

add_executable(cbrp-det-greedy
    ${SOURCES_MAIN}
    ${SOURCES_DETERMINISTIC_GREEDY_HEURISTIC}
    main-det-greedy-heuristic.cpp
)

# Deterministic Lagrangean
add_executable(cbrp-det-lagr
    ${SOURCES_MAIN}
    ${SOURCES_DETERMINISTIC_MODEL}
    ${SOURCES_DETERMINISTIC_LAGRANGEAN}
)

# Stochastic Simulated Annealing
add_executable(cbrp-stoc-sa
    main-sa.cpp
    ${SOURCES_MAIN}
    ${SOURCES_STOCHASTIC_HEURISTIC}
)

# Simheuristic
add_executable(cbrp-simheur
    ${SOURCES_MAIN}
    ${SOURCES_STOCHASTIC_HEURISTIC}
    ${SOURCES_SIMHEURISTIC}
)


target_link_libraries(cbrp-det ${GUROBI_CXX_LIBRARY} ${GUROBI_C_LIBRARY} pthread m ${LEMON_LIBRARY})
target_link_libraries(cbrp-det-greedy ${GUROBI_CXX_LIBRARY} ${GUROBI_C_LIBRARY} pthread m ${LEMON_LIBRARY})
target_link_libraries(cbrp-stoc ${GUROBI_CXX_LIBRARY} ${GUROBI_C_LIBRARY} pthread m ${LEMON_LIBRARY})
target_link_libraries(cbrp-det-lagr ${GUROBI_CXX_LIBRARY} ${GUROBI_C_LIBRARY} pthread m ${LEMON_LIBRARY})

target_link_libraries(cbrp-det-heur pthread m)
target_link_libraries(cbrp-stoc-sa pthread m)
target_link_libraries(cbrp-simheur pthread m pqxx pq zmq)