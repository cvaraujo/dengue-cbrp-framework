//
// Created by carlos on 27/05/19.
//

#ifndef DPARP_BOOST_H
#define DPARP_BOOST_H

#include "../classes/Input.hpp"

using namespace boost;

struct SPPRC_Graph_Vert_Prop
{
    SPPRC_Graph_Vert_Prop(int n = 0, int l = 0) : num(n), time(l) {}
    int num;
    int time;
};

struct SPPRC_Graph_Arc_Prop
{
    SPPRC_Graph_Arc_Prop(int n = 0, float c = 0.0, int t = 0) : num(n), cost(c), time(t) {}
    int num;
    int time;
    float cost;
};

typedef adjacency_list<vecS, vecS, directedS, SPPRC_Graph_Vert_Prop, SPPRC_Graph_Arc_Prop> SPPRC_Graph;
typedef graph_traits<SPPRC_Graph>::vertex_descriptor vertex_descriptor;
typedef graph_traits<SPPRC_Graph>::edge_descriptor edge_descriptor;

class BoostLibrary
{
public:
    Input *input;
    SPPRC_Graph G;

    BoostLibrary(Input *input);

    void set_boost_graph();

    void update_arc_cost(int i, int j, double cost);

    pair<int, double> run_spprc(map<pair<int, int>, int> &x);

    ~BoostLibrary() = default;

    // void BoostLibrary::updateBoostArcCost(int i, int j, boostGraph G, double new_cost)
    // {
    //     edge_descriptor ed;
    //     bool found;

    //     boost::tie(ed, found) = boost::edge(i, j, G);

    //     if (found)
    //     {
    //         SPPRC_Graph_Arc_Prop &arc = get(edge_bundle, G)[ed];
    //         arc.cost = new_cost;
    //     }
    // }
};

#endif
