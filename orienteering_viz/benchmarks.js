/**
 * Parallel MCTS Orienteering Problem Visualizer
 * Benchmark Sets Catalog, File Parser, and Synthetic Generator
 */

// ==========================================
// 1. BENCHMARK TEXT PARSER
// ==========================================

function parseBenchmarkText(text, filename = "custom_benchmark.txt") {
  if (!text || typeof text !== 'string') {
    throw new Error("Invalid benchmark data: empty or not a string");
  }

  const lines = text
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l.length > 0 && !l.startsWith('#') && !l.startsWith('//'));

  if (lines.length < 3) {
    throw new Error("Benchmark file must contain at least a budget line and 2 nodes (Start and End)");
  }

  // First line: Budget and optionally vehicle count / node count
  const firstLineTokens = lines[0].split(/[\s,]+/).filter(Boolean);
  const budget = parseFloat(firstLineTokens[0]);
  if (isNaN(budget) || budget <= 0) {
    throw new Error(`Invalid budget value on first line: "${lines[0]}"`);
  }

  const nodes = [];
  let minX = Infinity, maxX = -Infinity;
  let minY = Infinity, maxY = -Infinity;
  let maxScore = 0;
  let totalScore = 0;

  for (let i = 1; i < lines.length; i++) {
    const tokens = lines[i].split(/[\s,]+/).filter(Boolean);
    if (tokens.length < 3) continue;

    const x = parseFloat(tokens[0]);
    const y = parseFloat(tokens[1]);
    const score = parseFloat(tokens[2]);

    if (isNaN(x) || isNaN(y) || isNaN(score)) {
      continue;
    }

    const id = nodes.length;
    nodes.push({ id, x, y, score });

    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;

    if (score > maxScore) maxScore = score;
    totalScore += score;
  }

  if (nodes.length < 2) {
    throw new Error("Could not parse at least 2 valid nodes from benchmark");
  }

  // Derive display name from filename
  const cleanName = filename.replace(/\.[^/.]+$/, "").replace(/_/g, " ");

  return {
    name: cleanName,
    filename: filename,
    budget: budget,
    nodes: nodes,
    numNodes: nodes.length,
    startNode: 0,
    endNode: 1,
    bounds: { minX, maxX, minY, maxY },
    maxScore: maxScore,
    totalScore: totalScore
  };
}

// ==========================================
// 2. EMBEDDED BENCHMARK INSTANCES
// ==========================================

// Raw node templates for standard benchmark families:
// 1. Sample 6 Small (Ideal for stepping and full tree inspection)
const SAMPLE_6_NODES = [
  [0, 0, 0],     // 0: Start
  [12, 8, 0],    // 1: End
  [3, 2, 5],     // 2
  [4, 1, 7],     // 3
  [6, 4, 8],     // 4
  [9, 2, 6]      // 5
];

// 2. Sample 30 Nodes
const SAMPLE_30_NODES = [
  [0, 0, 0], [17, 14, 15], [12, 8, 0], [3, 2, 5], [4, 1, 7],
  [6, 4, 8], [9, 2, 6], [6, 3, 10], [8, 6, 9], [15, 12, 12],
  [2, 9, 8], [11, 5, 6], [7, 8, 11], [14, 3, 9], [5, 7, 4],
  [13, 10, 7], [1, 6, 13], [10, 1, 5], [16, 7, 8], [8, 11, 6],
  [3, 5, 9], [17, 9, 10], [9, 8, 7], [12, 2, 11], [6, 9, 5],
  [14, 6, 8], [4, 8, 12], [11, 3, 6], [18, 5, 9], [7, 10, 4],
  [15, 4, 10]
];

// 3. Tsiligirides Problem 1 (32 Nodes)
const TSILIGIRIDES_1_NODES = [
  [10.5, 14.4, 0], [11.2, 14.1, 0], [18, 15.9, 10], [18.3, 13.3, 10],
  [16.5, 9.3, 10], [15.4, 11, 10], [14.9, 13.2, 5], [16.3, 13.3, 5],
  [16.4, 17.8, 5], [15, 17.9, 5], [16.1, 19.6, 10], [15.7, 20.6, 10],
  [13.2, 20.1, 10], [14.3, 15.3, 5], [14, 5.1, 10], [11.4, 6.7, 15],
  [8.3, 5, 15], [7.9, 9.8, 10], [11.4, 12, 5], [11.2, 17.6, 5],
  [10.1, 18.7, 5], [11.7, 20.3, 10], [10.2, 22.1, 10], [9.7, 23.8, 10],
  [10.1, 26.4, 15], [7.4, 24, 15], [8.2, 19.9, 15], [8.7, 17.7, 10],
  [8.9, 13.6, 10], [5.6, 11.1, 10], [4.9, 18.9, 10], [7.3, 18.8, 10]
];

// 4. Set 64 (64 Nodes)
const SET_64_1_NODES = [
  [0.000, -7.000, 0], [0.000, 7.000, 0], [-1.000, -6.000, 6], [1.000, -6.000, 6],
  [-2.000, -5.000, 12], [0.000, -5.000, 6], [2.000, -5.000, 12], [-3.000, -4.000, 18],
  [-1.000, -4.000, 12], [1.000, -4.000, 12], [3.000, -4.000, 18], [-4.000, -3.000, 24],
  [-2.000, -3.000, 18], [0.000, -3.000, 12], [2.000, -3.000, 18], [4.000, -3.000, 24],
  [-5.000, -2.000, 30], [-3.000, -2.000, 24], [-1.000, -2.000, 18], [1.000, -2.000, 18],
  [3.000, -2.000, 24], [5.000, -2.000, 30], [-6.000, -1.000, 36], [-4.000, -1.000, 30],
  [-2.000, -1.000, 24], [0.000, -1.000, 18], [2.000, -1.000, 24], [4.000, -1.000, 30],
  [6.000, -1.000, 36], [-7.000, 0.000, 42], [-5.000, 0.000, 36], [-3.000, 0.000, 30],
  [-1.000, 0.000, 24], [1.000, 0.000, 24], [3.000, 0.000, 30], [5.000, 0.000, 36],
  [7.000, 0.000, 42], [-6.000, 1.000, 36], [-4.000, 1.000, 30], [-2.000, 1.000, 24],
  [0.000, 1.000, 18], [2.000, 1.000, 24], [4.000, 1.000, 30], [6.000, 1.000, 36],
  [-5.000, 2.000, 30], [-3.000, 2.000, 24], [-1.000, 2.000, 18], [1.000, 2.000, 18],
  [3.000, 2.000, 24], [5.000, 2.000, 30], [-4.000, 3.000, 24], [-2.000, 3.000, 18],
  [0.000, 3.000, 12], [2.000, 3.000, 18], [4.000, 3.000, 24], [-3.000, 4.000, 18],
  [-1.000, 4.000, 12], [1.000, 4.000, 12], [3.000, 4.000, 18], [-2.000, 5.000, 12],
  [0.000, 5.000, 6], [2.000, 5.000, 12], [-1.000, 6.000, 6], [1.000, 6.000, 6]
];

// 5. Set 100 (100 Nodes)
const SET_100_1_NODES = [
  [0.000, -5.000, 0], [0.000, 5.000, 0], [-1.078, -3.424, 24], [-4.483, -1.090, 24],
  [-3.475, 2.248, 24], [3.393, -4.551, 30], [5.664, 5.697, 42], [2.267, 4.601, 30],
  [-1.214, -4.519, 30], [0.056, 1.142, 6], [1.089, 0.074, 6], [3.327, -5.694, 36],
  [-3.381, -3.435, 30], [1.076, 3.370, 24], [3.418, 5.590, 36], [-2.255, 3.488, 24],
  [-4.478, 2.296, 30], [-3.492, -5.733, 36], [4.555, 4.588, 36], [1.144, 2.318, 18],
  [0.022, -1.205, 12], [-3.339, 5.735, 36], [0.053, 0.008, 0], [2.215, 2.198, 18],
  [-2.319, 1.085, 18], [5.688, -4.494, 42], [-5.775, 1.076, 36], [5.596, -0.063, 30],
  [5.681, -2.201, 36], [-3.434, -2.330, 24], [-4.576, -5.749, 42], [2.186, -2.246, 18],
  [-1.037, -1.130, 12], [-2.292, 4.488, 30], [-2.241, -1.157, 18], [-3.488, -4.588, 30],
  [-1.183, 3.436, 24], [4.644, -5.613, 42], [-5.696, -1.230, 30], [-5.650, 2.281, 36],
  [-1.100, 2.279, 18], [2.218, -1.055, 18], [-2.330, -3.319, 24], [-3.474, 1.182, 24],
  [-5.619, 5.720, 42], [-0.096, 3.494, 18], [4.475, 5.639, 42], [3.454, -3.373, 30],
  [-1.042, 0.072, 6], [-4.598, 5.638, 42], [-5.652, -5.775, 42], [-5.633, -3.373, 36],
  [1.124, 5.684, 30], [-1.214, 4.531, 30], [3.392, 2.228, 24], [4.497, 1.193, 24],
  [-5.736, 0.001, 30], [-5.602, -2.355, 36], [-1.145, 5.771, 36], [4.614, -3.475, 30],
  [0.083, -3.334, 18], [3.389, -1.168, 24], [-0.100, 2.237, 12], [3.346, 1.126, 24],
  [1.235, 4.574, 30], [4.520, 0.097, 24], [-2.172, 5.682, 36], [5.627, 2.196, 36],
  [2.333, 5.618, 36], [-2.309, -4.590, 30], [-4.472, 3.423, 30], [2.196, -5.735, 36],
  [-4.475, -2.251, 30], [3.480, -0.050, 18], [-4.568, 1.146, 30], [-4.625, -3.489, 30],
  [2.220, 1.170, 18], [1.131, -1.126, 12], [4.541, -2.329, 30], [1.053, -4.547, 30],
  [2.240, -4.526, 30], [4.635, 3.507, 30], [1.189, -2.346, 18], [-4.503, 4.453, 36],
  [-2.197, -2.309, 18], [-3.397, 4.581, 30], [-5.736, 3.426, 36], [-1.218, -5.771, 36],
  [5.774, -5.664, 42], [-3.378, 0.022, 18], [4.524, -1.224, 30], [1.121, 1.078, 12],
  [2.218, -3.464, 24], [4.535, 2.257, 30], [-5.725, -4.599, 42], [-5.618, 4.445, 42],
  [3.358, 3.493, 30], [-0.040, -2.244, 12], [-2.189, -0.008, 12], [5.699, 1.171, 30]
];

// 6. Grid Center 10x10 Pattern Generator Helper
function generateGridPattern(type = 'center') {
  const nodes = [];
  // Node 0: Start at (4, 0)
  nodes.push({ id: 0, x: 4.0, y: 0.0, score: 0 });
  // Node 1: End at (5, 9)
  nodes.push({ id: 1, x: 5.0, y: 9.0, score: 0 });

  for (let x = 0; x < 10; x++) {
    for (let y = 0; y < 10; y++) {
      let score = 1;
      const distFromCenter = Math.hypot(x - 4.5, y - 4.5);
      
      if (type === 'center') {
        score = Math.max(1, Math.round(15 - distFromCenter * 2.5));
      } else if (type === 'checkerboard') {
        score = (x + y) % 2 === 0 ? 12 : 2;
      } else if (type === 'diagonal') {
        const distFromDiag = Math.abs(x - y) / Math.SQRT2;
        score = Math.max(1, Math.round(16 - distFromDiag * 3));
      } else if (type === 'ring') {
        const ringDist = Math.abs(distFromCenter - 3.0);
        score = Math.max(1, Math.round(15 - ringDist * 4));
      } else if (type === 'random') {
        score = ((x * 37 + y * 73) % 19) + 1;
      }

      nodes.push({ id: nodes.length, x: parseFloat(x.toFixed(1)), y: parseFloat(y.toFixed(1)), score });
    }
  }
  return nodes;
}

// Helper to create benchmark object from node array and budget
function createBenchmark(name, filename, rawNodes, budget, category, description) {
  const nodes = rawNodes.map((item, idx) => ({
    id: idx,
    x: Array.isArray(item) ? item[0] : item.x,
    y: Array.isArray(item) ? item[1] : item.y,
    score: Array.isArray(item) ? item[2] : item.score
  }));

  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  let maxScore = 0, totalScore = 0;

  nodes.forEach(n => {
    if (n.x < minX) minX = n.x;
    if (n.x > maxX) maxX = n.x;
    if (n.y < minY) minY = n.y;
    if (n.y > maxY) maxY = n.y;
    if (n.score > maxScore) maxScore = n.score;
    totalScore += n.score;
  });

  return {
    id: filename.replace(/\.[^/.]+$/, "").toLowerCase(),
    name,
    filename,
    budget,
    nodes,
    numNodes: nodes.length,
    startNode: 0,
    endNode: 1,
    category,
    description,
    bounds: { minX, maxX, minY, maxY },
    maxScore,
    totalScore
  };
}

// Build pre-packaged catalog
const PRESET_BENCHMARKS = [
  // Category 1: Educational & Quick Inspection
  createBenchmark(
    "Sample 6 Small (Ideal for Full Tree Inspection)",
    "sample_6_small.txt",
    SAMPLE_6_NODES,
    20.0,
    "Educational",
    "6 nodes with budget 20. Compact state-space where all tree branches and UCT formulas can be viewed simultaneously."
  ),
  createBenchmark(
    "Sample 30 Nodes",
    "sample_30.txt",
    SAMPLE_30_NODES,
    60.0,
    "Educational",
    "30-node problem with budget 60. Balanced test graph for exploring route trade-offs."
  ),

  // Category 2: Tsiligirides Problem 1 (32 Nodes)
  createBenchmark(
    "Tsiligirides 1 — Budget 15 (Tight)",
    "tsiligirides_problem_1_budget_15.txt",
    TSILIGIRIDES_1_NODES,
    15.0,
    "Tsiligirides",
    "Classic Orienteering benchmark (32 nodes) with restrictive budget 15. Requires precise node selection."
  ),
  createBenchmark(
    "Tsiligirides 1 — Budget 30 (Moderate)",
    "tsiligirides_problem_1_budget_30.txt",
    TSILIGIRIDES_1_NODES,
    30.0,
    "Tsiligirides",
    "Classic Tsiligirides 1 with budget 30. Expands feasible paths across western and eastern clusters."
  ),
  createBenchmark(
    "Tsiligirides 1 — Budget 50 (Expansive)",
    "tsiligirides_problem_1_budget_50.txt",
    TSILIGIRIDES_1_NODES,
    50.0,
    "Tsiligirides",
    "Budget 50 allows complex tours looping through major score hubs before returning to End."
  ),
  createBenchmark(
    "Tsiligirides 1 — Budget 85 (Global Tour)",
    "tsiligirides_problem_1_budget_85.txt",
    TSILIGIRIDES_1_NODES,
    85.0,
    "Tsiligirides",
    "High budget allowing workers to visit almost the entire graph. Tests deep MCTS search depth."
  ),

  // Category 3: Set 64 (Diamond / Hexagonal Topologies)
  createBenchmark(
    "Set 64 — Budget 15 (Early Pruning)",
    "set_64_1_15.txt",
    SET_64_1_NODES,
    15.0,
    "Set 64",
    "64-node diamond lattice. Tests reachability pruning to prevent getting stranded far from End."
  ),
  createBenchmark(
    "Set 64 — Budget 30 (Branching Tests)",
    "set_64_1_30.txt",
    SET_64_1_NODES,
    30.0,
    "Set 64",
    "Moderate budget on 64 nodes. Excellent for observing Virtual Loss divergence among parallel threads."
  ),
  createBenchmark(
    "Set 64 — Budget 50 (Deep Diamond)",
    "set_64_1_50.txt",
    SET_64_1_NODES,
    50.0,
    "Set 64",
    "Denser routes through the diamond structure, with competing paths through positive and negative X corridors."
  ),
  createBenchmark(
    "Set 64 — Budget 80 (High Capacity)",
    "set_64_1_80.txt",
    SET_64_1_NODES,
    80.0,
    "Set 64",
    "Long exploration horizon across the full lattice."
  ),

  // Category 4: Set 100 (Circular Cluster Topology)
  createBenchmark(
    "Set 100 — Budget 20 (Local Exploration)",
    "set_100_1_20.txt",
    SET_100_1_NODES,
    20.0,
    "Set 100",
    "100 nodes scattered on a circle. Tight budget 20 tests quick local greedy vs UCT exploration."
  ),
  createBenchmark(
    "Set 100 — Budget 40 (Multi-Cluster)",
    "set_100_1_40.txt",
    SET_100_1_NODES,
    40.0,
    "Set 100",
    "Budget 40 connecting multiple outer ring clusters."
  ),
  createBenchmark(
    "Set 100 — Budget 60 (Wide Swathe)",
    "set_100_1_60.txt",
    SET_100_1_NODES,
    60.0,
    "Set 100",
    "Budget 60 allows visiting dense clusters while preserving return path to End."
  ),

  // Category 5: Grid Patterns
  createBenchmark(
    "Grid Center Peak — Budget 20",
    "grid_center_b20.txt",
    generateGridPattern('center'),
    20.0,
    "Grid Patterns",
    "10x10 coordinate grid where high reward scores cluster at the center (4.5, 4.5). Budget 20."
  ),
  createBenchmark(
    "Grid Center Peak — Budget 30",
    "grid_center_b30.txt",
    generateGridPattern('center'),
    30.0,
    "Grid Patterns",
    "10x10 grid with center peak scores and budget 30."
  ),
  createBenchmark(
    "Grid Checkerboard — Budget 30",
    "grid_checkerboard_b30.txt",
    generateGridPattern('checkerboard'),
    30.0,
    "Grid Patterns",
    "Alternating high and low score tiles. Tests if MCTS discovers interleaving optimal hops."
  ),
  createBenchmark(
    "Grid Concentric Ring — Budget 30",
    "grid_ring_b30.txt",
    generateGridPattern('ring'),
    30.0,
    "Grid Patterns",
    "Circular ridge of high scores around the center. Encourages curved loop tours."
  ),
  createBenchmark(
    "Grid Diagonal Ridge — Budget 30",
    "grid_diagonal_b30.txt",
    generateGridPattern('diagonal'),
    30.0,
    "Grid Patterns",
    "Diagonal corridor of rich scores running from top-left to bottom-right."
  )
];

// ==========================================
// 3. SYNTHETIC GENERATOR
// ==========================================

function generateSyntheticProblem(type = 'clusters', nodeCount = 25, budget = 35.0) {
  const nodes = [];
  // Start: bottom-left
  nodes.push({ id: 0, x: 2.0, y: 2.0, score: 0 });
  // End: top-right
  nodes.push({ id: 1, x: 18.0, y: 18.0, score: 0 });

  if (type === 'clusters') {
    const clusterCenters = [
      { cx: 6.0, cy: 14.0, baseScore: 25 },
      { cx: 12.0, cy: 7.0, baseScore: 30 },
      { cx: 15.0, cy: 15.0, baseScore: 20 }
    ];

    for (let i = 2; i < nodeCount; i++) {
      const cluster = clusterCenters[i % clusterCenters.length];
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.random() * 3.2;
      const x = parseFloat((cluster.cx + Math.cos(angle) * radius).toFixed(2));
      const y = parseFloat((cluster.cy + Math.sin(angle) * radius).toFixed(2));
      const score = Math.max(1, Math.round(cluster.baseScore - radius * 4 + (Math.random() * 6 - 3)));
      nodes.push({ id: i, x, y, score });
    }
  } else if (type === 'corridor') {
    for (let i = 2; i < nodeCount; i++) {
      const t = (i - 2) / (nodeCount - 3);
      const baseX = 2 + t * 16;
      const baseY = 10 + Math.sin(t * Math.PI * 3) * 6;
      const x = parseFloat((baseX + (Math.random() - 0.5) * 2.0).toFixed(2));
      const y = parseFloat((baseY + (Math.random() - 0.5) * 2.0).toFixed(2));
      const score = Math.round(5 + Math.random() * 20);
      nodes.push({ id: i, x, y, score });
    }
  } else {
    for (let i = 2; i < nodeCount; i++) {
      const x = parseFloat((2 + Math.random() * 16).toFixed(2));
      const y = parseFloat((2 + Math.random() * 16).toFixed(2));
      const score = Math.round(3 + Math.random() * 25);
      nodes.push({ id: i, x, y, score });
    }
  }

  return createBenchmark(
    `Synthetic ${type.charAt(0).toUpperCase() + type.slice(1)} (${nodeCount} Nodes, Budget ${budget})`,
    `synthetic_${type}_${nodeCount}_b${budget}.txt`,
    nodes,
    budget,
    "Synthetic",
    `Procedurally generated ${type} topology with ${nodeCount} nodes and budget ${budget}.`
  );
}

// Export to window
if (typeof window !== 'undefined') {
  window.BenchmarkParser = {
    parseBenchmarkText,
    PRESET_BENCHMARKS,
    generateSyntheticProblem,
    createBenchmark
  };
}
