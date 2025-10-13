#!/bin/bash
# Quick batch runner for key set_1000_1 budget values
# Run this from the UCT directory

echo "Running UCT on key set_1000_1 datasets..."

# Array of budget values to test for 1000-node dataset
budgets=(80 100 120 140 160)

for budget in "${budgets[@]}"; do
    echo ""
    echo "========================================"
    echo "Running UCT on budget $budget"
    echo "========================================"
    
    python3 main.py \
        --problem-file "../OP_Benchmark_Set/set_1000_1/set_1000_1_${budget}.txt" \
        --algorithm uct \
        --max-iterations 10000 \
        --verbose \
        --output-file "uct-output/single_thread_set1000_${budget}_10k.txt"
    
    echo "Completed budget $budget"
done

echo ""
echo "All UCT runs completed!"
echo "Results saved in uct-output/ directory"