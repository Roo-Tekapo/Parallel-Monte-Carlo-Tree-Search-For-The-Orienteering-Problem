// to contain the implementation of the MCTS algorithm for a single thread.
// functions for MCTS algorithm implementation    state, selection,expansion, simulation, backpropergation


// #include "mcts_single_thread.h"

#pragma once
#include "include/mcts_base.hpp"

class MCTS_ST : public MCTSBase {
public:
    void run() override;  // Implements the MCTS logic
};
