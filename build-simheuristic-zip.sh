#!/bin/bash
set -e

CBRP_SRC="/Users/pedro/Documents/Mestrado/Pesquisa/Simulador-Otimizador/dengue-cbrp-framework/cbrp-methodologies"
OUTPUT_DIR="/Users/pedro/Documents/Mestrado/Pesquisa/Simulador-Otimizador/dengue-cbrp-framework/external-libs"
ZIP_NAME="cbrp-simheuristic.zip"
STAGING_DIR=$(mktemp -d)
TARGET="$STAGING_DIR/cbrp-simheuristic"

if [ ! -d "$CBRP_SRC" ]; then
    echo "ERROR: Source directory $CBRP_SRC does not exist"
    exit 1
fi

echo "Creating staging directory at $TARGET..."
mkdir -p "$TARGET/src"

echo "Copying source files..."
cp "$CBRP_SRC/main-simheuristic.cpp" "$TARGET/"
cp "$CBRP_SRC/README.md" "$TARGET/" 2>/dev/null || true

cp -r "$CBRP_SRC/src/classes" "$TARGET/src/"
cp -r "$CBRP_SRC/src/common" "$TARGET/src/"
cp -r "$CBRP_SRC/src/heuristic" "$TARGET/src/"
cp -r "$CBRP_SRC/src/simheuristic" "$TARGET/src/"

echo "Generating Docker-specific CMakeLists.txt (cbrp-simheur only, no Gurobi)..."
cat > "$TARGET/CMakeLists.txt" << 'CMAKE_EOF'
cmake_minimum_required(VERSION 3.10)
project(cbrp)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_BUILD_TYPE Release)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -DIL_STD -O3 -ffast-math -funroll-loops -march=native -DNDEBUG -DSilence")

# Boost
file(GLOB BOOST_CANDIDATES "/opt/boost_*")
if(BOOST_CANDIDATES)
    list(SORT BOOST_CANDIDATES)
    list(GET BOOST_CANDIDATES -1 BOOST_LOCAL)
    set(BOOST_ROOT "${BOOST_LOCAL}")
    set(BOOST_INCLUDEDIR "${BOOST_LOCAL}")
endif()
find_package(Boost REQUIRED)

# LEMON
file(GLOB LEMON_CANDIDATES "/opt/lemon-*")
if(LEMON_CANDIDATES)
    list(SORT LEMON_CANDIDATES)
    list(GET LEMON_CANDIDATES -1 LEMON_ROOT)
endif()
find_path(LEMON_INCLUDE_DIR lemon/core.h PATHS "${LEMON_ROOT}" NO_DEFAULT_PATH)
find_library(LEMON_LIBRARY emon PATHS "${LEMON_ROOT}/lemon" NO_DEFAULT_PATH)
if(NOT LEMON_INCLUDE_DIR OR NOT LEMON_LIBRARY)
    message(FATAL_ERROR "LEMON not found. Install in /opt/lemon-*/")
endif()

include_directories(${Boost_INCLUDE_DIRS} ${LEMON_INCLUDE_DIR})

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

add_executable(cbrp-simheur
    ${SOURCES_MAIN}
    ${SOURCES_STOCHASTIC_HEURISTIC}
    ${SOURCES_SIMHEURISTIC}
)

target_link_libraries(cbrp-simheur pthread m pqxx pq zmq)
CMAKE_EOF

echo "Creating zip..."
mkdir -p "$OUTPUT_DIR"
cd "$STAGING_DIR"
rm -f "$OUTPUT_DIR/$ZIP_NAME"
zip -r "$OUTPUT_DIR/$ZIP_NAME" cbrp-simheuristic/

echo "Cleaning up..."
rm -rf "$STAGING_DIR"

echo "Done! Created $OUTPUT_DIR/$ZIP_NAME"
echo "Contents:"
unzip -l "$OUTPUT_DIR/$ZIP_NAME" | tail -5
