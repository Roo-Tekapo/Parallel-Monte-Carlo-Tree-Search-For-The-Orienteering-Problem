# Quick Reference: Traditional vs No-End Orienteering

## Command-Line Usage

Add `--use-no-end` to any command to switch from Traditional to No-End orienteering:

```bash
# Traditional (default) - must reach END_NODE
python UCT/main.py --problem-file <file> --algorithm uct --max-iterations 10000

# No-End - maximize reward without end constraint
python UCT/main.py --problem-file <file> --algorithm uct --max-iterations 10000 --use-no-end
```

Works with all implementations: **UCT**, **Simple_WU**, **VL**

## Key Differences

| Aspect | Traditional | No-End |
|--------|------------|---------|
| **Goal** | Reach END_NODE with max reward | Maximize reward (any path) |
| **Terminal** | At END_NODE or stuck | Budget exhausted or stuck |
| **Flag** | (none - default) | `--use-no-end` |
| **Typical Reward** | Lower (constrained) | Higher (unconstrained) |
| **Budget Usage** | Partial (stops early) | Full (explores more) |
| **Path Ends At** | END_NODE | Any high-value node |

## Example Comparison

Problem: `grid_10x10_medium_30.txt` (121 nodes, budget 30.0)

**Traditional UCT:**
```bash
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000
```
Result: **345 reward**, 24 nodes, ends at node 1 (END_NODE)

**No-End UCT:**
```bash
python UCT/main.py --problem-file OP_Benchmark_Set/grid_sample/grid_10x10_medium_30.txt --algorithm uct --max-iterations 10000 --use-no-end
```
Result: **391 reward**, 28 nodes, ends at node 95 (best available)

**Improvement:** +13% reward by removing end constraint!

## When to Use Each

**Use Traditional When:**
- Benchmark datasets require END_NODE
- Real-world problem has fixed destination
- Comparing with published results

**Use No-End When:**
- Goal is pure reward maximization
- No required destination
- Exploring budget utilization
- Research on path optimization

## Implementation Note

Both variants use the **same MCTS/UCT algorithms**. Only the problem definition changes via the adapter pattern.

See `ORIENTEERING_VARIANT_GUIDE.md` for detailed documentation.
