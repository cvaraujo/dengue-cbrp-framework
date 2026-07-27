//
// Created by carlos on 06/07/21.
//

#ifndef DPARP_INCLUDE_H
#define DPARP_INCLUDE_H

using namespace std;

#include "string"
#include <algorithm>
#include <cstdlib>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <random>
#include <utility>
#include <vector>

#include <boost/config.hpp>

#ifdef BOOST_MSVC
#pragma warning(disable : 4267)
#endif

#include <boost/algorithm/string.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/graph_traits.hpp>
#include <boost/graph/r_c_shortest_paths.hpp>

#include <lemon/list_graph.h>
#include <lemon/preflow.h>

const int INF = INT_MAX;
const double EPS = 1e-8;

typedef pair<int, int> int_pair;
typedef pair<int, double> double_pair;

#endif // DPARP_INCLUDE_H
