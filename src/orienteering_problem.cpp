#include "orienteering_problem.hpp"
#include <cmath>
#include <vector>

Graph::Graph(const std::vector<Node>& nodes) : nodes(nodes) {}

double Graph::getDistance(int id1, int id2) const {
    const Node& a = nodes[id1];
    const Node& b = nodes[id2];
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    return std::sqrt(dx * dx + dy * dy);
}

const std::vector<Node>& Graph::getNodes() const {
    return nodes;
}
