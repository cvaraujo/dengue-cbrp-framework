#include "LocalSearch.hpp"

/**
 * @brief 2-opt local search heuristic. Given a route, it removes two arcs and
 * reconnects the route in a different way, forming two new arcs.
 * @param route The route to be optimized
 * @param i First node to be swapped
 * @param j Second node to be swapped
 */
void LocalSearch::Run2Opt(int i, int j)
{
    // Graph *graph = input->getGraph();
    // vector<int> route = bestSolution->getRoute();
    // int route_size = route.size();

    // if (i > route_size || j > route_size)
    // {
    //     cout << "Invalid i or j" << endl;
    //     return;
    // }

    // int node_i = route[i], node_j = route[j];
    // int pred_i = route[i - 1], pred_j = route[j - 1];

    // Arc *old_arc_ii = graph->getArc(route[i - 1], route[i]),
    //     *old_arc_jj = graph->getArc(route[j - 1], route[j]),
    //     *new_arc_ij = graph->getArc(route[i - 1], route[j]),
    //     *new_arc_ji = graph->getArc(route[j - 1], route[i]);

    // cout << "Get arc from " << route[i - 1] << " to " << route[j] << endl;
    // cout << "Get arc from " << route[j - 1] << " to " << route[i] << endl;

    // if (new_arc_ij == nullptr || new_arc_ji == nullptr)
    // {
    //     cout << "[!] New arcs are null" << endl;
    //     return;
    // }

    // int new_length = (old_arc_ii->getLength() + old_arc_jj->getLength()) - (new_arc_ij->getLength() + new_arc_ji->getLength());

    // if (new_length > 0)
    // {
    //     int aux = route[i];
    //     route[i] = route[j];
    //     route[j] = aux;

    //     bestSolution->setRoute(route);
    //     bestSolution->setRouteTime(bestSolution->getRouteTime() - new_length);
    // }
}