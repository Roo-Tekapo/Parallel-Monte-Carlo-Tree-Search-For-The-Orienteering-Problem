#ifndef orienteering_problem_hpp
#define orienteering_problem_hpp

#include <vector>
#include <unordered_map>

struct Node {
    int id;
    double x, y;
    int score;
};

class Graph {
public:
    explicit Graph(const std::vector<Node>& nodes);
    double getDistance(int id1, int id2) const;
    const std::vector<Node>& getNodes() const;
private:
    std::vector<Node> nodes;
    std::unordered_map<int, std::unordered_map<int, double>> distanceCache;
};

#endif
