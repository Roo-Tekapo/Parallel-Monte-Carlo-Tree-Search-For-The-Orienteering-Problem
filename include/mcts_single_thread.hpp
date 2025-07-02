#ifndef mcts_single_thread_hpp
#define mcts_single_thread_hpp

#include <vector>
#include "orienteering_problem.hpp"


class MCTS {
public:
    MCTS(const Graph& graph, int budget);
    std::vector<int> run();
private:
    int budget;
    const Graph& graph;
    // Add private helper methods for selection, expansion, simulation, backpropagation
};

#endif
