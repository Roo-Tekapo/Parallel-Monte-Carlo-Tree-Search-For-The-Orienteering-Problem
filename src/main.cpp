//to have a override run() function

#include "include/mcts_single_thread.hpp"
#include "orienteering_problem.hpp"
#include <iostream>

int main() {
    std::vector<Node> nodes = {
        {0, 0, 0, 0},
        {1, 2, 3, 5},
        {2, 4, 5, 10},
        // ...
    };
    Graph graph(nodes);
    MCTS mcts(graph, 100);
    std::vector<int> path = mcts.run();

    std::cout << "Best path: ";
    for (int id : path) std::cout << id << " ";
    std::cout << std::endl;
    return 0;
}
