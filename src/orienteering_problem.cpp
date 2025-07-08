#include "orienteering_problem.hpp"
#include <cmath>
#include <vector>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>

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

State State::copy() const {
    return State{path, cost, score};
}

Graph Graph::load_problem(const std::string& filename, double& Tmax, int& P) {
    std::ifstream infile(filename);
    if (!infile) throw std::runtime_error("Cannot open file: " + filename);

    std::string line;
    // Skip header lines until we find the line with Tmax and P
    while (std::getline(infile, line)) {
        std::istringstream iss(line);
        double tmax;
        int p;
        if (iss >> tmax >> p) {
            Tmax = tmax;
            P = p;
            break;
        }
    }

    std::vector<Node> nodes;
    int node_id = 0;
    while (std::getline(infile, line)) {
        std::istringstream iss(line);
        double x, y;
        int s;
        if (iss >> x >> y >> s) {
            nodes.push_back(Node{node_id++, x, y, s});
        }
    }
    return Graph(nodes);
}

// getDistance between two nodes
// define the state - copy - is_terminal - get_score - get_path
// available actions - do_available_actions

