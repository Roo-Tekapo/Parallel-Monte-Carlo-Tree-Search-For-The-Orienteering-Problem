

Command Line Usage:
python WU_UCT/main.py --problem-file OP_Benchmark_Set/set_64_1/set_64_1_80.txt --max-iterations 50000 --num-workers 4 --verbose

Testing
# Basic functionality test
python WU_UCT/test_wu_uct.py

# Full example with benchmarks
python WU_UCT/example_usage.py



in WU_UCT folder
Basic Usage:
python3 main.py --problem-file problem.txt

High-Quality Solution:
python3 main.py --problem-file problem.txt \
    --max-iterations 50000 \
    --max-depth 100 \
    --verbose

Fast Parallel Execution:
python3 main.py --problem-file problem.txt \
    --parallel \
    --num-workers 8 \
    --max-time 60 \
    --verbose

Constrained Problem:
python3 main.py --problem-file problem.txt \
    --max-edge-distance 4.0 \
    --max-iterations 20000 \
    --output-file solution.txt



python3 WU_UCT/main.py --problem-file OP_Benchmark_Set/set_64_1/set_64_1_80.txt --max-edge-distance 1.42 --parallel --verbose --output-file wu_output/solution.txt


python3 WU_UCT/main.py --problem-file OP_Benchmark_Set/sample/sample_30.txt --max-edge-distance 4 --parallel --verbose --output-file wu_output/sample30_output.txt