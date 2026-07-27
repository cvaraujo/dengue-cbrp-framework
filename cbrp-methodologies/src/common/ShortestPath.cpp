#include "ShortestPath.hpp"

int ShortestPath::SHPBetweenBlocks(int b1, int b2, set<int> &nodes) {
    auto nodes_from_b1 = graph->getNodesFromBlock(b1);
    auto nodes_from_b2 = graph->getNodesFromBlock(b2);

    if (nodes_from_b1.size() == 0 || nodes_from_b2.size() == 0)
        return INF;

    // Both blocks attended by the same node
    for (auto node : nodes_from_b1) {
        auto it = find(nodes_from_b2.begin(), nodes_from_b2.end(), node);
        if (it != nodes_from_b2.end()) {
            nodes.insert(node);
            return 0;
        }
    }

    int shortest_path = INF, value;
    vector<int> shp, path;

    for (int node : nodes_from_b1) {
        for (int node2 : nodes_from_b2) {
            path = vector<int>();
            value = ShortestPathST(node, node2, path);

            if (value < shortest_path)
                shortest_path = value, shp = path;
        }
    }

    if (shortest_path < INF) {
        for (int i : shp)
            nodes.insert(i);
        return shortest_path;
    }

    return INF;
}

int ShortestPath::ShortestPathST(int s, int t, vector<int> &path) {
    if (dist[s][t] == INF)
        return INF;

    if (s == t) {
        path.push_back(s);
        return 0;
    }
    if (!ij_path[s][t].empty()) {
        path = ij_path[s][t];
        return dist[s][t];
    }

    if (this->graph->getArc(s, t) != nullptr) {
        path = vector<int>{s, t};
        return dist[s][t];
    }

    int i = s, j = t;
    path = vector<int>();
    path.push_back(i);

    while (i != j) {
        i = next[i][j];
        path.push_back(i);
    }

    ij_path[s][t] = path;

    return dist[s][t];
}

int ShortestPath::ShortestPathST(int s, int t) {
    if (s >= dist.size() || t >= dist[s].size())
        return 0;

    if (dist[s][t] == INF)
        return INF;

    if (s == t) {
        return 0;
    }
    if (!ij_path[s][t].empty()) {
        return dist[s][t];
    }

    if (this->graph->getArc(s, t) != nullptr) {
        return dist[s][t];
    }

    int i = s, j = t;
    vector<int> path;
    path.push_back(i);

    while (i != j) {
        i = next[i][j];
        path.push_back(i);
    }

    ij_path[s][t] = path;

    return dist[s][t];
}

int ShortestPath::DijkstraLayeredDAG(vector<vector<Arc>> dag, int n, int s, int t, vector<int> &pred) {
    priority_queue<int_pair, vector<int_pair>, greater<>> pq;
    vector<int> distance(n, INF), predecessor(n, -1);

    pq.emplace(0, s);
    distance[s] = 0, predecessor[s] = s;

    while (!pq.empty()) {
        int u = pq.top().second;
        pq.pop();

        for (auto arc : dag[u]) {
            int v = arc.getD();

            if (distance[v] > distance[u] + arc.getLength()) {
                distance[v] = distance[u] + arc.getLength();
                predecessor[v] = u;
                pq.emplace(distance[v], v);
            }
        }
    }

    pred = predecessor;

    return distance[t];
}

void ShortestPath::allPairsShortestPath() {
    int N = graph->getN();
    dist = vector<vector<int>>(N, vector<int>(N, INF));
    next = vector<vector<int>>(N, vector<int>(N, -1));
    ij_path = vector<vector<vector<int>>>(N, vector<vector<int>>(N, vector<int>{}));

    // Initialize the next matrix
    for (int i = 0; i < N; i++) {
        dist[i][i] = 0, next[i][i] = i;
        for (auto arc : graph->getArcs(i)) {
            int j = arc->getD();
            if (j >= N)
                continue;

            dist[i][j] = arc->getLength(), dist[j][i] = arc->getLength();
            next[i][j] = j, next[j][i] = i;
        }
    }

    for (int k = 0; k < N; ++k) {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                if (dist[i][k] != INF && dist[k][j] != INF && dist[i][k] + dist[k][j] < dist[i][j]) {
                    dist[i][j] = dist[i][k] + dist[k][j];
                    next[i][j] = next[i][k];
                }
            }
        }
    }
}

vector<int> ShortestPath::getPath(int s, int t) {
    if (s >= ij_path.size() || t >= ij_path[s].size()) {
        return vector<int>();
    }

    if (!ij_path[s][t].empty()) {
        return ij_path[s][t];
    }

    if (graph->getArc(s, t) != nullptr) {
        ij_path[s][t] = vector<int>{s, t};
        return ij_path[s][t];
    }

    vector<int> path = {s};
    int v = s;
    while (v != t) {
        v = next[v][t];
        path.push_back(v);
    }
    ij_path[s][t] = path;
    return path;
}