/**
 * Parallel MCTS Visualizer - Core Application Logic
 * Tic-Tac-Toe Demonstration of Single UCT, Virtual Loss (VL-UCT), WU-UCT, and Root Parallel
 */

// ==========================================
// 1. TIC-TAC-TOE ENGINE & STATE
// ==========================================

class BoardState {
  constructor(grid = null, turn = 'X') {
    this.grid = grid ? [...grid] : Array(9).fill(null);
    this.turn = turn; // 'X' moves first
  }

  clone() {
    return new BoardState(this.grid, this.turn);
  }

  getLegalMoves() {
    const moves = [];
    for (let i = 0; i < 9; i++) {
      if (this.grid[i] === null) moves.push(i);
    }
    return moves;
  }

  makeMove(index) {
    if (this.grid[index] !== null) return false;
    this.grid[index] = this.turn;
    this.turn = this.turn === 'X' ? 'O' : 'X';
    return true;
  }

  checkWinner() {
    const lines = [
      [0, 1, 2], [3, 4, 5], [6, 7, 8], // Rows
      [0, 3, 6], [1, 4, 7], [2, 5, 8], // Cols
      [0, 4, 8], [2, 4, 6]             // Diagonals
    ];

    for (const [a, b, c] of lines) {
      if (this.grid[a] && this.grid[a] === this.grid[b] && this.grid[a] === this.grid[c]) {
        return { winner: this.grid[a], line: [a, b, c] };
      }
    }

    if (this.grid.every(cell => cell !== null)) {
      return { winner: 'DRAW', line: null };
    }

    return null; // Game ongoing
  }

  isTerminal() {
    return this.checkWinner() !== null;
  }
}

// ==========================================
// 2. MCTS NODE DATA STRUCTURES
// ==========================================

let globalNodeIdCounter = 0;

class MCTSNode {
  constructor(state, move = null, parent = null) {
    this.id = ++globalNodeIdCounter;
    this.state = state.clone();
    this.move = move; // Move index (0-8) that led here
    this.parent = parent;
    this.children = [];
    this.unexploredMoves = state.getLegalMoves();
    
    // Who played the move to reach this state?
    this.playerJustMoved = state.turn === 'X' ? 'O' : 'X';
    
    // Statistics
    this.visits = 0;         // N
    this.totalReward = 0;    // Q (from perspective of playerJustMoved)
    
    // Virtual Loss extensions (VL-UCT)
    this.virtualLoss = 0.0;  // L
    this.virtualVisits = 0;  // V
    
    // WU-UCT extensions (Asynchronous unobserved count)
    this.unobservedCount = 0; // O
    
    // Visualization coordinates
    this.x = 0;
    this.y = 0;
    this.depth = parent ? parent.depth + 1 : 0;
  }

  isFullyExpanded() {
    return this.unexploredMoves.length === 0;
  }

  isTerminal() {
    return this.state.isTerminal();
  }

  getWinRate() {
    if (this.visits === 0) return 0.5;
    return this.totalReward / this.visits;
  }

  // Calculate UCT value based on algorithm mode
  getUCT(c = 1.414, algo = 'uct', vlPenalty = 0.20) {
    // Unvisited nodes get maximum priority for exploration
    const effectiveVisits = this.visits + (algo === 'vl' ? this.virtualVisits : 0);
    if (effectiveVisits === 0) {
      return 1000.0 + Math.random() * 0.01;
    }

    const parentVisits = this.parent ? this.parent.visits : this.visits;

    if (algo === 'vl') {
      // Virtual Loss Formula:
      // UCT = max(0, Q - L) / (N + V) + c * sqrt( ln(N_p) / (N + V) )
      const effReward = Math.max(0, this.totalReward - this.virtualLoss);
      const denom = this.visits + this.virtualVisits;
      const exploit = effReward / denom;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits)) / denom);
      return exploit + explore;
    } 
    else if (algo === 'wu') {
      // WU-UCT Formula:
      // UCT = Q / N + c * sqrt( ln(N_p + O_p) / (N + O) )
      const parentO = this.parent ? this.parent.unobservedCount : 0;
      const exploit = this.visits > 0 ? this.totalReward / this.visits : 0.5;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits + parentO)) / (this.visits + this.unobservedCount));
      return exploit + explore;
    } 
    else {
      // Standard UCT:
      // UCT = Q / N + c * sqrt( ln(N_p) / N )
      const exploit = this.totalReward / this.visits;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits)) / this.visits);
      return exploit + explore;
    }
  }

  // Get detailed breakdown for formula inspector
  getBreakdown(c = 1.414, algo = 'uct', vlPenalty = 0.20) {
    const parentVisits = this.parent ? this.parent.visits : this.visits;
    const effectiveVisits = this.visits + (algo === 'vl' ? this.virtualVisits : 0);
    
    if (effectiveVisits === 0) {
      return {
        exploit: 0,
        explore: '∞ (Unvisited)',
        vlTerm: 0,
        wuTerm: 0,
        total: 1000.0
      };
    }

    if (algo === 'vl') {
      const denom = this.visits + this.virtualVisits;
      const rawExploit = this.totalReward / denom;
      const vlPenaltyTerm = this.virtualLoss / denom;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits)) / denom);
      return {
        exploit: rawExploit.toFixed(3),
        explore: explore.toFixed(3),
        vlTerm: (-vlPenaltyTerm).toFixed(3),
        wuTerm: 0,
        total: (rawExploit - vlPenaltyTerm + explore).toFixed(3)
      };
    } else if (algo === 'wu') {
      const parentO = this.parent ? this.parent.unobservedCount : 0;
      const exploit = this.visits > 0 ? (this.totalReward / this.visits) : 0.5;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits + parentO)) / (this.visits + this.unobservedCount));
      return {
        exploit: exploit.toFixed(3),
        explore: explore.toFixed(3),
        vlTerm: 0,
        wuTerm: `O=${this.unobservedCount}`,
        total: (exploit + explore).toFixed(3)
      };
    } else {
      const exploit = this.totalReward / this.visits;
      const explore = c * Math.sqrt(Math.log(Math.max(1, parentVisits)) / this.visits);
      return {
        exploit: exploit.toFixed(3),
        explore: explore.toFixed(3),
        vlTerm: 0,
        wuTerm: 0,
        total: (exploit + explore).toFixed(3)
      };
    }
  }
}

// ==========================================
// 3. WORKER & QUEUE SIMULATOR (PARALLEL MODES)
// ==========================================

class SimulatedWorker {
  constructor(id, name, color) {
    this.id = id;
    this.name = name;
    this.color = color;
    this.state = 'IDLE'; // 'IDLE', 'SELECTING', 'EXPANDING', 'ROLLOUT', 'BACKPROP'
    this.taskDesc = 'Idle — ready';
    this.targetMove = null;
    this.simulations = 0;
    this.currentPath = [];
  }

  reset() {
    this.state = 'IDLE';
    this.taskDesc = 'Idle — ready';
    this.targetMove = null;
    this.simulations = 0;
    this.currentPath = [];
  }
}

class WorkUnit {
  constructor(id, path, stateToSimulate) {
    this.id = id;
    this.path = path;
    this.stateToSimulate = stateToSimulate.clone();
    this.timestamp = Date.now();
  }
}

// ==========================================
// 4. MAIN CONTROLLER
// ==========================================

class MCTSVisualizerApp {
  constructor() {
    this.currentBoard = new BoardState();
    this.algorithm = 'uct'; // 'uct', 'vl', 'wu', 'root'
    this.explorationConstant = 1.414;
    this.vlPenaltyValue = 0.20;
    this.speed = 25; // iterations per second
    this.isRunning = false;
    this.runTimer = null;

    // Single MCTS tree root
    this.rootNode = null;
    this.selectedNode = null;
    
    // Step-by-step phase state machine
    this.stepPhase = 0; // 0: Select, 1: Expand, 2: Simulate, 3: Backprop
    this.activeStepWorker = 0;
    this.activeStepPath = [];
    this.activeStepNode = null;
    this.activeRolloutState = null;
    this.activeRolloutReward = 0;

    // Metrics & collision detection
    this.stats = {
      iterations: 0,
      nodesCount: 1,
      maxDepth: 0,
      collisionsAvoided: 0,
      activeVLCount: 0,
      startTime: null
    };

    // Parallel Workers Pool (up to 8 customizable)
    this.workerCount = 4;
    this.currentWorkerIndex = 0;
    this.initWorkers();

    // WU-UCT Work Queue
    this.workQueue = [];
    this.workUnitCounter = 0;

    // Root-Parallel mini trees
    this.rootParallelTrees = [];

    // Tree Viewport SVG Pan & Zoom (Root centered at x=0)
    this.viewportTransform = { x: 0, y: 35, scale: 0.95 };
    this.isPanning = false;
    this.panStart = { x: 0, y: 0 };
    this.maxVisibleDepth = 'all';
    this.lastLayoutNodes = [];

    this.boardMode = 'play'; // 'play' or 'setup'

    // Initialize UI and State
    this.initDOM();
    this.resetTree();
    this.renderBoard();
    this.updateWorkerUI();
    this.updateFormulaUI();
    this.updateStatsUI();
  }

  // ------------------------------------------------
  // DOM References & Event Listeners
  // ------------------------------------------------
  initDOM() {
    // Buttons
    this.btnPlayPause = document.getElementById('btnPlayPause');
    this.btnStepPhase = document.getElementById('btnStepPhase');
    this.btnStepIter = document.getElementById('btnStepIter');
    this.btnResetTree = document.getElementById('btnResetTree');
    this.btnResetBoard = document.getElementById('btnResetBoard');
    this.btnClearBoard = document.getElementById('btnClearBoard');
    this.btnAIMove = document.getElementById('btnAIMove');
    this.speedSlider = document.getElementById('speedSlider');
    this.speedValue = document.getElementById('speedValue');

    // Pan / Zoom & View Depth
    this.btnCenterRoot = document.getElementById('btnCenterRoot');
    this.btnFitTree = document.getElementById('btnFitTree');
    this.btnZoomIn = document.getElementById('btnZoomIn');
    this.btnZoomOut = document.getElementById('btnZoomOut');
    this.btnZoomReset = document.getElementById('btnZoomReset');
    this.depthFilter = document.getElementById('depthFilter');
    this.treeViewport = document.getElementById('treeViewport');
    this.treeRootGroup = document.getElementById('treeRootGroup');
    this.treeSvg = document.getElementById('treeSvg');
    this.treeEmptyState = document.getElementById('treeEmptyState');

    // Parameters
    this.sliderExploration = document.getElementById('sliderExploration');
    this.valExplorationConst = document.getElementById('valExplorationConst');
    this.sliderVLValue = document.getElementById('sliderVLValue');
    this.valVLSetting = document.getElementById('valVLSetting');
    this.rowVLTune = document.getElementById('rowVLTune');

    // Board & Containers
    this.tictactoeGrid = document.getElementById('tictactoeGrid');
    this.turnBadge = document.getElementById('turnBadge');
    this.boardStatusStrip = document.getElementById('boardStatusStrip');
    this.modePlay = document.getElementById('modePlay');
    this.modeSetup = document.getElementById('modeSetup');

    // Workers & Queue Containers
    this.workersGrid = document.getElementById('workersGrid');
    this.workerCountSelect = document.getElementById('workerCountSelect');
    this.workerCountBadge = document.getElementById('workerCountBadge');
    if (this.workerCountSelect) this.workerCount = parseInt(this.workerCountSelect.value, 10);
    this.queueContainer = document.getElementById('queueContainer');
    this.queueTrack = document.getElementById('queueTrack');
    this.queueCount = document.getElementById('queueCount');
    this.vlMetricsContainer = document.getElementById('vlMetricsContainer');
    this.workersCardTitle = document.getElementById('workersCardTitle');

    // Rollout Preview
    this.rolloutGrid = document.getElementById('rolloutGrid');
    this.rolloutMeta = document.getElementById('rolloutMeta');
    this.rolloutReward = document.getElementById('rolloutReward');
    this.rolloutResultBadge = document.getElementById('rolloutResultBadge');

    // Formula & Stats
    this.formulaEquationBox = document.getElementById('formulaEquationBox');
    this.valExploit = document.getElementById('valExploit');
    this.valExplore = document.getElementById('valExplore');
    this.valVL = document.getElementById('valVL');
    this.valWU = document.getElementById('valWU');
    this.valTotalUCT = document.getElementById('valTotalUCT');
    this.selectedNodeBadge = document.getElementById('selectedNodeBadge');
    this.rowVLTerm = document.getElementById('rowVLTerm');
    this.rowWUTerm = document.getElementById('rowWUTerm');

    this.statIterations = document.getElementById('statIterations');
    this.statNodes = document.getElementById('statNodes');
    this.statDepth = document.getElementById('statDepth');
    this.statThroughput = document.getElementById('statThroughput');
    this.recBars = document.getElementById('recBars');

    // Phase Banner
    this.phaseSteps = [
      document.getElementById('phaseStepSelect'),
      document.getElementById('phaseStepExpand'),
      document.getElementById('phaseStepSim'),
      document.getElementById('phaseStepBackprop')
    ];
    this.phaseDesc = document.getElementById('phaseDesc');

    // Log Stream
    this.logStream = document.getElementById('logStream');
    this.btnClearLog = document.getElementById('btnClearLog');

    // Help Modal
    this.helpModal = document.getElementById('helpModal');
    this.btnHelpModal = document.getElementById('btnHelpModal');
    this.btnCloseModal = document.getElementById('btnCloseModal');

    // Event Bindings
    this.bindEvents();
  }

  bindEvents() {
    // Algorithm switch buttons
    document.querySelectorAll('.algo-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.algo-btn').forEach(b => b.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.setAlgorithm(e.currentTarget.dataset.algo);
      });
    });

    // Run / Pause & Steps
    this.btnPlayPause.addEventListener('click', () => this.toggleRun());
    this.btnStepPhase.addEventListener('click', () => this.executeStepPhase());
    this.btnStepIter.addEventListener('click', () => this.executeStepIteration());
    this.btnResetTree.addEventListener('click', () => this.resetTree());
    this.btnResetBoard.addEventListener('click', () => this.resetBoard());
    this.btnClearBoard.addEventListener('click', () => this.clearBoard());
    this.btnAIMove.addEventListener('click', () => this.makeAIMove());

    // Speed Slider
    this.speedSlider.addEventListener('input', (e) => {
      this.speed = parseInt(e.target.value, 10);
      this.speedValue.textContent = `${this.speed} it/s`;
      if (this.isRunning) {
        this.pauseRun();
        this.startRun();
      }
    });

    // Exploration Constant
    this.sliderExploration.addEventListener('input', (e) => {
      this.explorationConstant = parseFloat(e.target.value);
      this.valExplorationConst.textContent = this.explorationConstant.toFixed(2);
      this.updateFormulaUI();
      this.renderTree();
    });

    // VL Penalty Value
    this.sliderVLValue.addEventListener('input', (e) => {
      this.vlPenaltyValue = parseFloat(e.target.value);
      this.valVLSetting.textContent = this.vlPenaltyValue.toFixed(2);
      document.getElementById('metricVLPenalty').textContent = this.vlPenaltyValue.toFixed(2);
      this.updateFormulaUI();
      this.renderTree();
    });

    // Board Modes
    this.modePlay.addEventListener('click', () => {
      this.boardMode = 'play';
      this.modePlay.classList.add('active');
      this.modeSetup.classList.remove('active');
      this.boardStatusStrip.textContent = 'Play Mode: Click an empty cell to move as Human.';
    });
    this.modeSetup.addEventListener('click', () => {
      this.boardMode = 'setup';
      this.modeSetup.classList.add('active');
      this.modePlay.classList.remove('active');
      this.boardStatusStrip.textContent = 'Custom Setup Mode: Click cells to cycle (Empty → X → O).';
    });

    // Log Clear
    this.btnClearLog.addEventListener('click', () => {
      this.logStream.innerHTML = '';
      this.log('Log cleared.', 'info');
    });

    // Modal
    this.btnHelpModal.addEventListener('click', () => this.helpModal.classList.remove('hidden'));
    this.btnCloseModal.addEventListener('click', () => this.helpModal.classList.add('hidden'));
    this.helpModal.addEventListener('click', (e) => {
      if (e.target === this.helpModal) this.helpModal.classList.add('hidden');
    });

    // Modal Tabs
    document.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const targetId = e.currentTarget.dataset.tab;
        document.getElementById(targetId).classList.add('active');
      });
    });

    // Worker Count Selector
    if (this.workerCountSelect) {
      this.workerCountSelect.addEventListener('change', (e) => {
        this.workerCount = parseInt(e.target.value, 10);
        this.log(`Configured active worker pool to ${this.workerCount} threads.`, 'info');
        this.updateWorkerUI();
      });
    }

    // Zoom, Pan & Depth Controls
    if (this.btnCenterRoot) this.btnCenterRoot.addEventListener('click', () => this.centerOnRoot());
    if (this.btnFitTree) this.btnFitTree.addEventListener('click', () => this.fitEntireTree());
    if (this.depthFilter) {
      this.depthFilter.addEventListener('change', (e) => {
        this.maxVisibleDepth = e.target.value;
        this.renderTree();
        this.log(`Tree display filter set to Depth: ${this.maxVisibleDepth.toUpperCase()}`, 'info');
      });
    }
    this.btnZoomIn.addEventListener('click', () => this.zoom(1.2));
    this.btnZoomOut.addEventListener('click', () => this.zoom(0.8));
    this.btnZoomReset.addEventListener('click', () => this.resetZoom());

    this.treeViewport.addEventListener('mousedown', (e) => {
      this.isPanning = true;
      this.panStart = { x: e.clientX - this.viewportTransform.x, y: e.clientY - this.viewportTransform.y };
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.isPanning) return;
      this.viewportTransform.x = e.clientX - this.panStart.x;
      this.viewportTransform.y = e.clientY - this.panStart.y;
      this.applyViewportTransform();
    });

    window.addEventListener('mouseup', () => {
      this.isPanning = false;
    });

    this.treeViewport.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
      this.zoom(zoomFactor, e.clientX, e.clientY);
    });
  }

  // ------------------------------------------------
  // Algorithm Switching
  // ------------------------------------------------
  setAlgorithm(algo) {
    if (this.isRunning) this.pauseRun();
    this.algorithm = algo;
    this.log(`Switched algorithm to: ${this.getAlgoName(algo)}`, 'info');

    // Adjust UI displays according to mode
    if (algo === 'vl') {
      this.rowVLTune.style.display = 'flex';
      this.vlMetricsContainer.classList.remove('hidden');
      this.queueContainer.classList.add('hidden');
      this.rowVLTerm.style.display = 'flex';
      this.rowWUTerm.style.display = 'none';
      this.workersCardTitle.textContent = 'Virtual Loss Worker Threads';
      this.workerCountBadge.textContent = '4 Threads';
    } else if (algo === 'wu') {
      this.rowVLTune.style.display = 'none';
      this.vlMetricsContainer.classList.add('hidden');
      this.queueContainer.classList.remove('hidden');
      this.rowVLTerm.style.display = 'none';
      this.rowWUTerm.style.display = 'flex';
      this.workersCardTitle.textContent = 'WU-UCT Pipeline Workers';
      this.workerCountBadge.textContent = '1 Exp + 3 Sim';
    } else if (algo === 'root') {
      this.rowVLTune.style.display = 'none';
      this.vlMetricsContainer.classList.add('hidden');
      this.queueContainer.classList.add('hidden');
      this.rowVLTerm.style.display = 'none';
      this.rowWUTerm.style.display = 'none';
      this.workersCardTitle.textContent = 'Root-Parallel Workers';
      this.workerCountBadge.textContent = '4 Independent Trees';
    } else {
      // Standard single UCT
      this.rowVLTune.style.display = 'none';
      this.vlMetricsContainer.classList.add('hidden');
      this.queueContainer.classList.add('hidden');
      this.rowVLTerm.style.display = 'none';
      this.rowWUTerm.style.display = 'none';
      this.workersCardTitle.textContent = 'Single Worker Thread';
    }

    if (algo === 'uct') {
      if (this.workerCountSelect) {
        this.workerCountSelect.value = '1';
        this.workerCountSelect.disabled = true;
      }
      this.workerCount = 1;
    } else {
      if (this.workerCountSelect) {
        this.workerCountSelect.disabled = false;
        if (this.workerCountSelect.value === '1') this.workerCountSelect.value = '4';
        this.workerCount = parseInt(this.workerCountSelect.value, 10);
      }
    }

    this.initWorkers();
    this.resetTree();
    this.updateFormulaUI();
    this.updateWorkerUI();
  }

  getAlgoName(algo) {
    switch (algo) {
      case 'vl': return 'Virtual Loss (VL-UCT)';
      case 'wu': return 'WU-UCT (Asynchronous Queue)';
      case 'root': return 'Root-Parallel MCTS';
      default: return 'Single-Threaded Standard UCT';
    }
  }

  // ------------------------------------------------
  // Board & Game UI
  // ------------------------------------------------
  renderBoard() {
    this.tictactoeGrid.innerHTML = '';
    const outcome = this.currentBoard.checkWinner();

    for (let i = 0; i < 9; i++) {
      const cell = document.createElement('div');
      cell.className = 'cell';
      cell.dataset.index = i;

      const val = this.currentBoard.grid[i];
      if (val === 'X') {
        cell.classList.add('player-x');
        cell.textContent = 'X';
      } else if (val === 'O') {
        cell.classList.add('player-o');
        cell.textContent = 'O';
      }

      // Coordinate marker (r, c)
      const r = Math.floor(i / 3);
      const c = i % 3;
      const coordSpan = document.createElement('span');
      coordSpan.className = 'cell-coord';
      coordSpan.textContent = `${r},${c}`;
      cell.appendChild(coordSpan);

      // Best move highlight
      if (this.rootNode && this.rootNode.children.length > 0 && !val && !outcome) {
        const bestChild = this.getBestMoveChild(this.rootNode);
        if (bestChild && bestChild.move === i) {
          cell.classList.add('best-move');
        }
      }

      cell.addEventListener('click', () => this.handleCellClick(i));
      this.tictactoeGrid.appendChild(cell);
    }

    // Update Turn Badge & Status
    if (outcome) {
      if (outcome.winner === 'DRAW') {
        this.turnBadge.textContent = 'Game Over: Draw';
        this.turnBadge.className = 'badge';
        this.boardStatusStrip.textContent = 'Game ended in a draw.';
      } else {
        this.turnBadge.textContent = `Winner: ${outcome.winner}!`;
        this.turnBadge.className = 'badge badge-success';
        this.boardStatusStrip.textContent = `Player ${outcome.winner} wins the game!`;
      }
    } else {
      this.turnBadge.textContent = `Turn: ${this.currentBoard.turn}`;
      this.turnBadge.className = this.currentBoard.turn === 'X' ? 'badge badge-info' : 'badge badge-accent';
      this.boardStatusStrip.textContent = `Turn for ${this.currentBoard.turn}. Make a move or run MCTS.`;
    }

    this.updateRecommendationBars();
  }

  handleCellClick(index) {
    if (this.isRunning) this.pauseRun();

    if (this.boardMode === 'setup') {
      // Cycle: Empty -> X -> O -> Empty
      const cur = this.currentBoard.grid[index];
      if (cur === null) this.currentBoard.grid[index] = 'X';
      else if (cur === 'X') this.currentBoard.grid[index] = 'O';
      else this.currentBoard.grid[index] = null;
      
      this.resetTree();
      this.renderBoard();
      this.log(`Custom board updated cell ${index}. Tree reset.`, 'info');
      return;
    }

    // Play Mode
    if (this.currentBoard.grid[index] !== null || this.currentBoard.isTerminal()) {
      return;
    }

    const player = this.currentBoard.turn;
    this.currentBoard.makeMove(index);
    this.log(`Player ${player} moved to cell [${Math.floor(index/3)}, ${index%3}]`, 'info');
    this.resetTree();
    this.renderBoard();
  }

  resetBoard() {
    if (this.isRunning) this.pauseRun();
    this.currentBoard = new BoardState();
    this.resetTree();
    this.renderBoard();
    this.log('Board reset to initial empty state.', 'info');
  }

  clearBoard() {
    this.resetBoard();
  }

  makeAIMove() {
    if (this.currentBoard.isTerminal()) {
      this.log('Game already finished. Reset board to play again.', 'warn');
      return;
    }

    // Ensure we have explored the tree sufficiently
    if (!this.rootNode || this.rootNode.visits < 10) {
      this.log('Running 80 rapid MCTS iterations before algorithm chooses move...', 'info');
      for (let i = 0; i < 80; i++) {
        this.executeSingleIteration();
      }
      this.renderTree();
      this.updateStatsUI();
    }

    const bestChild = this.getBestMoveChild(this.rootNode);
    if (!bestChild) {
      this.log('No legal moves available.', 'warn');
      return;
    }

    const move = bestChild.move;
    const aiPlayer = this.currentBoard.turn;
    this.currentBoard.makeMove(move);
    this.log(`⚡ Algorithm (${aiPlayer}) selected Move [${Math.floor(move/3)}, ${move%3}] with ${bestChild.visits} visits (${(bestChild.getWinRate()*100).toFixed(1)}% win rate)`, 'success');
    
    this.resetTree();
    this.renderBoard();
  }

  getBestMoveChild(node) {
    if (this.algorithm === 'root' && this.rootParallelTrees && this.rootParallelTrees.length > 0) {
      // Aggregate across all worker trees by move index
      const moveVisits = {};
      const moveChildren = {};
      for (const tree of this.rootParallelTrees) {
        for (const child of tree.children) {
          moveVisits[child.move] = (moveVisits[child.move] || 0) + child.visits;
          if (!moveChildren[child.move]) moveChildren[child.move] = child;
        }
      }
      let bestMoveChild = null;
      let maxVisits = -1;
      for (const m in moveVisits) {
        if (moveVisits[m] > maxVisits) {
          maxVisits = moveVisits[m];
          bestMoveChild = moveChildren[m];
        }
      }
      return bestMoveChild || (node && node.children.length > 0 ? node.children[0] : null);
    }
    if (!node || node.children.length === 0) return null;
    // Robust decision rule: Child with the highest visit count N
    return node.children.reduce((best, child) => 
      child.visits > best.visits ? child : best, node.children[0]
    );
  }

  // ------------------------------------------------
  // Tree State Management
  // ------------------------------------------------
  resetTree() {
    if (this.isRunning) this.pauseRun();
    if (this.backpropTimeout) {
      clearTimeout(this.backpropTimeout);
      this.backpropTimeout = null;
    }
    globalNodeIdCounter = 0;
    
    if (this.algorithm === 'root') {
      const activeCount = this.getActiveWorkers().length;
      this.rootParallelTrees = [];
      for (let i = 0; i < activeCount; i++) {
        this.rootParallelTrees.push(new MCTSNode(this.currentBoard));
      }
      this.rootNode = this.rootParallelTrees[0];
    } else {
      this.rootParallelTrees = [];
      this.rootNode = new MCTSNode(this.currentBoard);
    }
    this.selectedNode = this.rootNode;
    this.stepPhase = 0;
    this.activeStepPath = [];
    this.activeStepNode = null;
    this.activeRolloutState = null;
    this.activeRolloutReward = 0;

    this.stats = {
      iterations: 0,
      nodesCount: 1,
      maxDepth: 0,
      collisionsAvoided: 0,
      activeVLCount: 0,
      startTime: null
    };

    this.workQueue = [];
    this.workUnitCounter = 0;

    // Reset workers
    this.workers.forEach(w => w.reset());

    this.centerOnRoot();
    this.renderTree();
    this.updateFormulaUI();
    this.updateStatsUI();
    this.updateWorkerUI();
    this.updatePhaseBanner();
    this.renderRolloutPreview(null);
  }

  // ------------------------------------------------
  // MCTS Algorithms & Stepping
  // ------------------------------------------------

  // Execute one step of the 4-phase cycle (Selection -> Expansion -> Simulation -> Backprop)
  executeStepPhase() {
    if (this.backpropTimeout) {
      clearTimeout(this.backpropTimeout);
      this.backpropTimeout = null;
    }
    if (this.currentBoard.isTerminal()) {
      this.log('Cannot run MCTS: current board is terminal.', 'warn');
      return;
    }

    switch (this.stepPhase) {
      case 0: // Selection
        this.doPhaseSelection();
        this.stepPhase = 1;
        break;
      case 1: // Expansion
        this.doPhaseExpansion();
        this.stepPhase = 2;
        break;
      case 2: // Simulation
        this.doPhaseSimulation();
        this.stepPhase = 3;
        break;
      case 3: // Backpropagation
        this.doPhaseBackpropagation();
        this.stepPhase = 0;
        this.stats.iterations++;
        this.updateStatsUI();
        break;
    }

    this.updatePhaseBanner();
    this.renderTree();
    this.updateWorkerUI();
    this.updateFormulaUI();
    this.renderBoard();
  }

  doPhaseSelection() {
    const worker = this.workers[0];
    worker.state = 'SELECTING';
    const path = [this.rootNode];
    let curr = this.rootNode;

    // In VL mode, show Worker 2 attempting selection to demonstrate collision diversion!
    let simulatedCollision = false;

    while (!curr.isTerminal() && curr.isFullyExpanded() && curr.children.length > 0) {
      // Pick child with highest UCT
      let bestChild = null;
      let bestVal = -Infinity;
      
      for (const child of curr.children) {
        const uct = child.getUCT(this.explorationConstant, this.algorithm, this.vlPenaltyValue);
        if (uct > bestVal) {
          bestVal = uct;
          bestChild = child;
        }
      }

      if (!bestChild) break;
      curr = bestChild;
      path.push(curr);
    }

    this.activeStepPath = path;
    this.activeStepNode = curr;
    worker.currentPath = path;
    worker.targetMove = curr.move;
    worker.taskDesc = `Selected Node #${curr.id} (Depth ${curr.depth})`;

    // Apply Virtual Loss if in VL mode
    if (this.algorithm === 'vl') {
      for (const node of path) {
        node.virtualLoss += this.vlPenaltyValue;
        node.virtualVisits += 1;
      }
      this.stats.activeVLCount++;
      document.getElementById('metricActiveVL').textContent = this.stats.activeVLCount;
      this.log(`Worker #1 applied Virtual Loss (L=+${this.vlPenaltyValue.toFixed(2)}) along selected path (Depth: ${path.length-1})`, 'vl');

      // Simulate Worker #2 selection to check if diverted!
      if (this.rootNode.children.length > 1) {
        const altChild = this.rootNode.children.find(c => c !== path[1]);
        if (altChild) {
          this.stats.collisionsAvoided++;
          document.getElementById('metricCollisionsAvoided').textContent = this.stats.collisionsAvoided;
          this.workers[1].state = 'SELECTING';
          this.workers[1].currentPath = [this.rootNode, altChild];
          this.log(`⚡ Collision avoided! Worker #2 diverted to alternate child Node #${altChild.id} because Worker #1's path was penalized.`, 'success');
        }
      }
    } 
    else if (this.algorithm === 'wu') {
      // Mark path unobserved O++
      for (const node of path) {
        node.unobservedCount++;
      }
      this.log(`Expansion Worker tagged path with unobserved count O=${curr.unobservedCount}`, 'wu');
    }

    this.log(`Phase 1 [Selection]: Traversed path down to Node #${curr.id} (Depth ${curr.depth}) using UCT`, 'info');
    this.selectedNode = curr;
  }

  doPhaseExpansion() {
    const curr = this.activeStepNode || this.rootNode;
    const worker = this.workers[0];
    worker.state = 'EXPANDING';

    if (curr.isTerminal()) {
      this.log(`Node #${curr.id} is a terminal game state. Skipping expansion, proceeding directly to rollout.`, 'info');
      return;
    }

    if (!curr.isFullyExpanded()) {
      // Pick an unexplored legal move
      const moveIndex = curr.unexploredMoves.shift();
      const nextState = curr.state.clone();
      nextState.makeMove(moveIndex);

      const newNode = new MCTSNode(nextState, moveIndex, curr);
      curr.children.push(newNode);
      this.stats.nodesCount++;
      if (newNode.depth > this.stats.maxDepth) {
        this.stats.maxDepth = newNode.depth;
      }

      worker.targetMove = moveIndex;
      worker.taskDesc = `Expanded [${Math.floor(moveIndex/3)}, ${moveIndex%3}] (Node #${newNode.id})`;
      this.activeStepNode = newNode;
      this.activeStepPath.push(newNode);
      this.selectedNode = newNode;

      this.log(`Phase 2 [Expansion]: Added new child Node #${newNode.id} for move [${Math.floor(moveIndex/3)}, ${moveIndex%3}]`, 'info');

      if (this.algorithm === 'wu') {
        newNode.unobservedCount++;
        const unit = new WorkUnit(++this.workUnitCounter, [...this.activeStepPath], newNode.state);
        this.workQueue.push(unit);
        this.updateQueueUI();
        this.log(`WU-UCT: Enqueued WorkUnit #${unit.id} to simulation worker queue`, 'wu');
      }
    } else {
      this.log(`Node #${curr.id} already fully expanded. Proceeding to rollout.`, 'info');
    }
  }

  doPhaseSimulation() {
    const curr = this.activeStepNode || this.rootNode;
    const worker = this.algorithm === 'wu' ? this.workers[1] : this.workers[0];
    worker.state = 'ROLLOUT';
    worker.taskDesc = 'Simulating random rollout...';

    // Perform random rollout from curr.state
    const simState = curr.state.clone();
    const rolloutMoves = [];

    while (!simState.isTerminal()) {
      const legalMoves = simState.getLegalMoves();
      const randomMove = legalMoves[Math.floor(Math.random() * legalMoves.length)];
      simState.makeMove(randomMove);
      rolloutMoves.push(randomMove);
    }

    const outcome = simState.checkWinner();
    this.activeRolloutState = simState;

    // Calculate reward from perspective of the root board's turn (AI player)
    const aiPlayer = this.currentBoard.turn;
    let rewardForAI = 0.5; // Draw
    if (outcome.winner === aiPlayer) rewardForAI = 1.0;
    else if (outcome.winner !== 'DRAW') rewardForAI = 0.0;

    this.activeRolloutReward = rewardForAI;
    worker.taskDesc = `Rollout finished: ${outcome.winner === 'DRAW' ? 'Draw' : outcome.winner + ' Won'}`;
    this.renderRolloutPreview(simState, outcome, rewardForAI, rolloutMoves);
    this.log(`Phase 3 [Simulation]: Rollout played ${rolloutMoves.length} moves. Result: ${outcome.winner === 'DRAW' ? 'Draw (0.5)' : outcome.winner + ' Won (' + rewardForAI + ')'}`, 'info');
  }

  doPhaseBackpropagation() {
    const path = this.activeStepPath;
    const reward = this.activeRolloutReward;
    const worker = this.workers[0];
    worker.state = 'BACKPROP';
    worker.simulations++;
    worker.taskDesc = `Committed R=${reward.toFixed(1)} (${worker.simulations} sims)`;

    // Backpropagate up the ancestral path
    for (const node of path) {
      // Remove Virtual Loss if in VL mode
      if (this.algorithm === 'vl') {
        node.virtualLoss = Math.max(0, node.virtualLoss - this.vlPenaltyValue);
        node.virtualVisits = Math.max(0, node.virtualVisits - 1);
      }
      // Remove unobserved if in WU mode
      else if (this.algorithm === 'wu') {
        node.unobservedCount = Math.max(0, node.unobservedCount - 1);
      }

      // Update true visits and reward
      node.visits += 1;
      
      // Zero-sum reward assignment:
      // If node's playerJustMoved equals AI player, reward is rewardForAI, else 1 - rewardForAI
      const aiPlayer = this.currentBoard.turn;
      const nodeReward = (node.playerJustMoved === aiPlayer) ? reward : (1.0 - reward);
      node.totalReward += nodeReward;
    }

    if (this.algorithm === 'vl') {
      this.stats.activeVLCount = Math.max(0, this.stats.activeVLCount - 1);
      document.getElementById('metricActiveVL').textContent = this.stats.activeVLCount;
      this.log(`Phase 4 [Backprop]: Removed Virtual Loss and committed reward (${reward}) to ${path.length} nodes.`, 'vl');
    } else if (this.algorithm === 'wu') {
      if (this.workQueue.length > 0) {
        this.workQueue.shift();
        this.updateQueueUI();
      }
      this.log(`Phase 4 [Backprop]: Update-Complete committed result to tree, decremented O.`, 'wu');
    } else {
      this.log(`Phase 4 [Backprop]: Updated N and Q for ${path.length} nodes up to root.`, 'info');
    }

    // Reset path highlights
    if (this.backpropTimeout) clearTimeout(this.backpropTimeout);
    this.backpropTimeout = setTimeout(() => {
      this.activeStepPath = [];
      this.activeStepNode = null;
      this.getActiveWorkers().forEach(w => {
        w.state = 'IDLE';
        w.taskDesc = `Idle (${w.simulations} sims done)`;
      });
      this.renderTree();
      this.updateWorkerUI();
      this.backpropTimeout = null;
    }, 450);
  }

  // Execute one complete 4-phase iteration
  // Execute one complete 4-phase iteration with worker attribution
  executeSingleIteration(worker = null) {
    if (this.currentBoard.isTerminal()) return;
    const w = worker || this.workers[0];

    // For Root-Parallel mode, use worker's dedicated tree
    let targetRoot = this.rootNode;
    if (this.algorithm === 'root' && this.rootParallelTrees && this.rootParallelTrees.length > 0) {
      const activeWorkers = this.getActiveWorkers();
      const workerIdx = Math.max(0, activeWorkers.indexOf(w));
      targetRoot = this.rootParallelTrees[workerIdx % this.rootParallelTrees.length];
    }

    // Selection
    w.state = 'SELECTING';
    const path = [targetRoot];
    let curr = targetRoot;

    while (!curr.isTerminal() && curr.isFullyExpanded() && curr.children.length > 0) {
      let bestChild = null;
      let bestVal = -Infinity;
      for (const child of curr.children) {
        const uct = child.getUCT(this.explorationConstant, this.algorithm, this.vlPenaltyValue);
        if (uct > bestVal) {
          bestVal = uct;
          bestChild = child;
        }
      }
      if (!bestChild) break;
      curr = bestChild;
      path.push(curr);
    }

    w.currentPath = path;
    const moveStr = curr.move !== null ? `[${Math.floor(curr.move/3)},${curr.move%3}]` : 'Root';
    w.targetMove = curr.move;
    w.taskDesc = `Exploring ${moveStr} (Depth ${curr.depth})`;

    // Apply Virtual Loss if in VL mode
    if (this.algorithm === 'vl') {
      for (const node of path) {
        node.virtualLoss += this.vlPenaltyValue;
        node.virtualVisits += 1;
      }
    } else if (this.algorithm === 'wu') {
      for (const node of path) {
        node.unobservedCount++;
      }
    }

    // Expansion
    w.state = 'EXPANDING';
    let expandedNode = curr;
    if (!curr.isTerminal() && !curr.isFullyExpanded()) {
      const moveIndex = curr.unexploredMoves.shift();
      const nextState = curr.state.clone();
      nextState.makeMove(moveIndex);
      expandedNode = new MCTSNode(nextState, moveIndex, curr);
      curr.children.push(expandedNode);
      this.stats.nodesCount++;
      if (expandedNode.depth > this.stats.maxDepth) {
        this.stats.maxDepth = expandedNode.depth;
      }
      path.push(expandedNode);
      w.targetMove = moveIndex;
      w.taskDesc = `Expanded [${Math.floor(moveIndex/3)},${moveIndex%3}]`;
    }

    // Simulation (Rollout)
    w.state = 'ROLLOUT';
    const simState = expandedNode.state.clone();
    while (!simState.isTerminal()) {
      const moves = simState.getLegalMoves();
      const randMove = moves[Math.floor(Math.random() * moves.length)];
      simState.makeMove(randMove);
    }

    const outcome = simState.checkWinner();
    const aiPlayer = this.currentBoard.turn;
    let rewardForAI = 0.5;
    if (outcome.winner === aiPlayer) rewardForAI = 1.0;
    else if (outcome.winner !== 'DRAW') rewardForAI = 0.0;

    // Backprop
    w.state = 'BACKPROP';
    for (const node of path) {
      if (this.algorithm === 'vl') {
        node.virtualLoss = Math.max(0, node.virtualLoss - this.vlPenaltyValue);
        node.virtualVisits = Math.max(0, node.virtualVisits - 1);
      } else if (this.algorithm === 'wu') {
        node.unobservedCount = Math.max(0, node.unobservedCount - 1);
      }

      node.visits += 1;
      const nodeReward = (node.playerJustMoved === aiPlayer) ? rewardForAI : (1.0 - rewardForAI);
      node.totalReward += nodeReward;
    }

    w.simulations++;
    const resText = outcome.winner === 'DRAW' ? 'Draw' : `${outcome.winner} Won`;
    w.taskDesc = `Finished rollout: ${resText}`;
    this.stats.iterations++;
  }

  executeStepIteration() {
    if (this.currentBoard.isTerminal()) {
      this.log('Cannot iterate: board is terminal.', 'warn');
      return;
    }
    this.executeSingleIteration();
    this.updateStatsUI();
    this.renderTree();
    this.updateFormulaUI();
    this.renderBoard();
    this.log(`Completed full iteration #${this.stats.iterations}`, 'info');
  }

  // ------------------------------------------------
  // Continuous Run Mode
  // ------------------------------------------------
  toggleRun() {
    if (this.isRunning) {
      this.pauseRun();
    } else {
      this.startRun();
    }
  }

  startRun() {
    if (this.currentBoard.isTerminal()) {
      this.log('Cannot run: current board is terminal. Reset board first.', 'warn');
      return;
    }

    this.isRunning = true;
    this.btnPlayPause.textContent = '⏸ Pause';
    this.btnPlayPause.className = 'btn btn-primary';
    this.stats.startTime = Date.now();
    this.log(`Started continuous search at ${this.speed} iterations/sec`, 'info');

    // Interval batching
    const intervalMs = Math.max(16, Math.floor(1000 / this.speed));
    const iterationsPerTick = Math.max(1, Math.round(this.speed / (1000 / intervalMs)));

    this.runTimer = setInterval(() => {
      const activeWorkers = this.getActiveWorkers();
      for (let i = 0; i < iterationsPerTick; i++) {
        const worker = activeWorkers[this.currentWorkerIndex % activeWorkers.length];
        this.currentWorkerIndex++;
        this.executeSingleIteration(worker);
      }
      this.updateWorkerUI();
      this.renderTree();
      this.updateStatsUI();
      this.renderBoard();
      this.updateFormulaUI();
    }, intervalMs);
  }

  pauseRun() {
    this.isRunning = false;
    this.btnPlayPause.textContent = '▶ Run';
    this.btnPlayPause.className = 'btn btn-success';
    if (this.runTimer) {
      clearInterval(this.runTimer);
      this.runTimer = null;
    }
    const activeWorkers = this.getActiveWorkers();
    activeWorkers.forEach(w => {
      w.state = 'IDLE';
      w.taskDesc = `Completed ${w.simulations} sims`;
    });
    this.updateWorkerUI();
    this.log(`Paused search after ${this.stats.iterations} iterations.`, 'info');
  }

  // ------------------------------------------------
  // Tree Visualization & SVG Rendering
  // ------------------------------------------------
  renderTree() {
    if (!this.rootNode) {
      this.treeEmptyState.classList.remove('hidden');
      this.treeRootGroup.innerHTML = '';
      return;
    }

    this.treeEmptyState.classList.add('hidden');
    this.treeRootGroup.innerHTML = '';

    // Layout nodes with tree layout algorithm
    const layoutNodes = [];
    const layoutEdges = [];
    this.computeTreeLayout(this.rootNode, layoutNodes, layoutEdges);

    // Render Edges
    for (const edge of layoutEdges) {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', edge.x1);
      line.setAttribute('y1', edge.y1);
      line.setAttribute('x2', edge.x2);
      line.setAttribute('y2', edge.y2);
      line.setAttribute('class', 'tree-edge');

      // Check if on active path
      if (this.activeStepPath.includes(edge.child) && this.activeStepPath.includes(edge.parent)) {
        line.classList.add('active-edge');
      }

      this.treeRootGroup.appendChild(line);
    }

    // Render Nodes
    for (const item of layoutNodes) {
      const node = item.node;
      const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('transform', `translate(${item.x}, ${item.y})`);
      g.style.cursor = 'pointer';

      // Circle
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const radius = node === this.rootNode ? 20 : 16;
      circle.setAttribute('r', radius);
      circle.setAttribute('class', 'node-circle');

      // Node Color by Win Rate
      const winRate = node.getWinRate();
      let fillColor = '#3b82f6'; // Mid / draw
      if (node.visits === 0) {
        fillColor = '#4b5563'; // Gray unvisited
      } else if (winRate >= 0.65) {
        fillColor = '#10b981'; // Green
      } else if (winRate <= 0.35) {
        fillColor = '#ef4444'; // Red
      }

      circle.setAttribute('fill', fillColor);
      circle.setAttribute('stroke', '#1f293d');
      circle.setAttribute('stroke-width', '2');

      // Visual state highlights
      if (this.activeStepPath.includes(node)) {
        circle.classList.add('active-worker');
      }
      if (node.virtualVisits > 0) {
        circle.classList.add('has-vl');
      }
      if (node.unobservedCount > 0) {
        circle.classList.add('has-wu');
      }
      if (node === this.selectedNode) {
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', '3');
      }
      if (node.isTerminal()) {
        circle.setAttribute('stroke', '#f59e0b');
        circle.setAttribute('stroke-dasharray', '3 2');
        circle.setAttribute('stroke-width', '2.5');
      }

      g.appendChild(circle);

      // Terminal Outcome Badge (Win/Loss/Draw)
      if (node.isTerminal()) {
        const winnerObj = node.state.checkWinner();
        const termLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        termLabel.setAttribute('class', 'node-sublabel');
        termLabel.setAttribute('y', -radius - 4);
        termLabel.setAttribute('fill', winnerObj && winnerObj.winner === 'DRAW' ? '#9ca3af' : (winnerObj.winner === 'X' ? 'var(--player-x)' : 'var(--player-o)'));
        termLabel.setAttribute('font-weight', '700');
        termLabel.textContent = winnerObj ? (winnerObj.winner === 'DRAW' ? 'Draw' : `${winnerObj.winner} Win`) : 'End';
        g.appendChild(termLabel);
      }

      // Node Move Label
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('class', 'node-label');
      text.setAttribute('y', 3);
      if (node === this.rootNode) {
        text.textContent = 'Root';
      } else {
        const r = Math.floor(node.move / 3);
        const c = node.move % 3;
        text.textContent = `${r},${c}`;
      }
      g.appendChild(text);

      // Node Visits Sublabel (N)
      const sub = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      sub.setAttribute('class', 'node-sublabel');
      sub.setAttribute('y', radius + 11);
      sub.textContent = `N=${node.visits}`;
      g.appendChild(sub);

      // Hidden Children Indicator if deeper than filter
      if (item.hasHiddenChildren) {
        const plusBadge = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        plusBadge.setAttribute('class', 'node-sublabel');
        plusBadge.setAttribute('y', radius + 21);
        plusBadge.setAttribute('fill', 'var(--accent-cyan)');
        plusBadge.textContent = `[+${item.node.children.length}]`;
        g.appendChild(plusBadge);
      }

      // Click to select node
      g.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectNode(node);
      });

      this.treeRootGroup.appendChild(g);
    }

    this.applyViewportTransform();
  }

  computeTreeLayout(root, outNodes, outEdges) {
    const levelHeight = 65;
    const maxDepth = this.maxVisibleDepth === 'all' ? 99 : parseInt(this.maxVisibleDepth, 10);

    // Adaptive width calculation: unvisited/leaf branches take less space
    const calcSubtreeWidth = (node) => {
      if (node.children.length === 0 || node.depth >= maxDepth) {
        return 38;
      }
      let sum = 0;
      for (const ch of node.children) {
        sum += calcSubtreeWidth(ch);
      }
      return Math.max(38, sum);
    };

    const assignCoords = (node, leftX, depth) => {
      const width = calcSubtreeWidth(node);
      const myX = leftX + width / 2;
      const myY = depth * levelHeight + 35;

      const hasHiddenChildren = (node.children.length > 0 && node.depth >= maxDepth);
      outNodes.push({ node, x: myX, y: myY, hasHiddenChildren });

      if (node.depth < maxDepth) {
        let curLeft = leftX;
        for (const ch of node.children) {
          const chWidth = calcSubtreeWidth(ch);
          const chX = curLeft + chWidth / 2;
          const chY = (depth + 1) * levelHeight + 35;

          outEdges.push({ parent: node, child: ch, x1: myX, y1: myY, x2: chX, y2: chY });
          assignCoords(ch, curLeft, depth + 1);
          curLeft += chWidth;
        }
      }
    };

    const totalTreeWidth = calcSubtreeWidth(root);
    // Root is ALWAYS anchored at x = 0 (left starts at -totalTreeWidth / 2)
    assignCoords(root, -totalTreeWidth / 2, 0);
    this.lastLayoutNodes = outNodes;
  }

  applyViewportTransform() {
    const rect = this.treeViewport.getBoundingClientRect();
    const centerX = (rect && rect.width > 0 ? rect.width : 700) / 2;
    this.treeRootGroup.setAttribute(
      'transform',
      `translate(${centerX + this.viewportTransform.x}, ${this.viewportTransform.y}) scale(${this.viewportTransform.scale})`
    );
  }

  centerOnRoot() {
    this.viewportTransform.x = 0;
    this.viewportTransform.y = 35;
    this.viewportTransform.scale = 1.0;
    this.applyViewportTransform();
    this.log('🎯 Centered view on Root node (x=0).', 'info');
  }

  fitEntireTree() {
    if (!this.lastLayoutNodes || this.lastLayoutNodes.length === 0) return;
    const rect = this.treeViewport.getBoundingClientRect();
    const vpWidth = (rect && rect.width > 0) ? rect.width : 700;
    const vpHeight = (rect && rect.height > 0) ? rect.height : 500;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const item of this.lastLayoutNodes) {
      minX = Math.min(minX, item.x - 30);
      maxX = Math.max(maxX, item.x + 30);
      minY = Math.min(minY, item.y - 30);
      maxY = Math.max(maxY, item.y + 30);
    }

    const treeWidth = Math.max(100, maxX - minX);
    const treeHeight = Math.max(100, maxY - minY);
    const scaleX = (vpWidth - 60) / treeWidth;
    const scaleY = (vpHeight - 60) / treeHeight;
    const fitScale = Math.min(1.2, Math.max(0.18, Math.min(scaleX, scaleY)));

    const treeCenterX = (minX + maxX) / 2;
    this.viewportTransform.scale = fitScale;
    this.viewportTransform.x = -treeCenterX * fitScale;
    this.viewportTransform.y = 35;
    this.applyViewportTransform();
    this.log(`⛶ Fitted entire tree (${this.lastLayoutNodes.length} nodes) at ${(fitScale * 100).toFixed(0)}% zoom.`, 'info');
  }

  zoom(factor, clientX = null, clientY = null) {
    const newScale = Math.min(2.5, Math.max(0.15, this.viewportTransform.scale * factor));
    this.viewportTransform.scale = newScale;
    this.applyViewportTransform();
  }

  resetZoom() {
    this.centerOnRoot();
  }

  selectNode(node) {
    this.selectedNode = node;
    this.updateFormulaUI();
    this.renderTree();
    this.log(`Inspecting Node #${node.id} (${node === this.rootNode ? 'Root' : `Move [${Math.floor(node.move/3)}, ${node.move%3}]`}, Depth: ${node.depth}, Visits: ${node.visits}, WinRate: ${(node.getWinRate()*100).toFixed(1)}%)`, 'info');
  }

  // ------------------------------------------------
  // UI Panels & Diagnostics
  // ------------------------------------------------
  updatePhaseBanner() {
    this.phaseSteps.forEach((step, idx) => {
      if (idx === this.stepPhase) {
        step.classList.add('active');
      } else {
        step.classList.remove('active');
      }
    });

    const phaseMessages = [
      '👉 Next: Phase 1 (Selection) — Traverses from root down the tree using UCT formula to pick the best leaf.',
      '👉 Next: Phase 2 (Expansion) — Creates a new child node on the tree frontier for an unexplored legal move.',
      '👉 Next: Phase 3 (Simulation / Rollout) — Plays random moves from the new state to terminal game state.',
      '👉 Next: Phase 4 (Backpropagation) — Propagates the win/draw/loss reward back up, updating visits N and reward Q.'
    ];
    this.phaseDesc.textContent = `${phaseMessages[this.stepPhase]} (Click 'Step Phase' to advance 1 phase, or 'Step Iteration' to do all 4)`;
  }

  updateFormulaUI() {
    const node = this.selectedNode || this.rootNode;
    if (!node) return;

    this.selectedNodeBadge.textContent = node === this.rootNode ? 'Root Node' : `Node #${node.id} (${Math.floor(node.move/3)}, ${node.move%3})`;

    // Formula equation string
    if (this.algorithm === 'vl') {
      this.formulaEquationBox.textContent = `UCT = (Q - L)/(N + V) + c × √( ln(Np) / (N + V) )`;
    } else if (this.algorithm === 'wu') {
      this.formulaEquationBox.textContent = `UCT = Q/N + c × √( ln(Np + Op) / (N + O) )`;
    } else {
      this.formulaEquationBox.textContent = `UCT = Q/N + c × √( ln(Np) / N )`;
    }

    const breakdown = node.getBreakdown(this.explorationConstant, this.algorithm, this.vlPenaltyValue);
    this.valExploit.textContent = breakdown.exploit;
    this.valExplore.textContent = breakdown.explore;
    this.valVL.textContent = breakdown.vlTerm;
    this.valWU.textContent = breakdown.wuTerm;
    this.valTotalUCT.textContent = breakdown.total;
  }

  updateStatsUI() {
    this.statIterations.textContent = this.stats.iterations;
    this.statNodes.textContent = this.stats.nodesCount;
    this.statDepth.textContent = this.stats.maxDepth;

    if (this.stats.startTime && this.stats.iterations > 0) {
      const elapsedSec = Math.max(0.1, (Date.now() - this.stats.startTime) / 1000);
      const throughput = Math.round(this.stats.iterations / elapsedSec);
      this.statThroughput.textContent = `${throughput}/s`;
    } else {
      this.statThroughput.textContent = '0/s';
    }

    this.updateRecommendationBars();
  }

  updateRecommendationBars() {
    let candidateList = [];
    if (this.algorithm === 'root' && this.rootParallelTrees && this.rootParallelTrees.length > 0) {
      const moveAgg = {};
      for (const tree of this.rootParallelTrees) {
        for (const child of tree.children) {
          if (!moveAgg[child.move]) {
            moveAgg[child.move] = { move: child.move, visits: 0, totalReward: 0 };
          }
          moveAgg[child.move].visits += child.visits;
          moveAgg[child.move].totalReward += child.totalReward;
        }
      }
      candidateList = Object.values(moveAgg).map(m => ({
        move: m.move,
        visits: m.visits,
        getWinRate: () => (m.visits > 0 ? m.totalReward / m.visits : 0.5)
      }));
    } else if (this.rootNode && this.rootNode.children.length > 0) {
      candidateList = this.rootNode.children;
    }

    if (candidateList.length === 0) {
      this.recBars.innerHTML = '<div class="rec-empty">Run iterations to see move evaluations.</div>';
      return;
    }

    this.recBars.innerHTML = '';
    const totalChildVisits = candidateList.reduce((acc, c) => acc + c.visits, 0);

    // Sort children by visits descending
    const sorted = [...candidateList].sort((a, b) => b.visits - a.visits);

    for (const child of sorted) {
      const pct = totalChildVisits > 0 ? (child.visits / totalChildVisits) * 100 : 0;
      const winPct = (child.getWinRate() * 100).toFixed(0);
      const r = Math.floor(child.move / 3);
      const c = child.move % 3;

      const item = document.createElement('div');
      item.className = 'rec-item';
      item.innerHTML = `
        <span class="rec-label">[${r},${c}]</span>
        <div class="rec-bar-wrap">
          <div class="rec-bar-fill" style="width: ${pct}%"></div>
        </div>
        <span class="rec-val">${winPct}%</span>
      `;
      this.recBars.appendChild(item);
    }
  }

  initWorkers() {
    const workerColors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899', '#6366f1', '#14b8a6'];
    this.workers = [];
    for (let i = 1; i <= 8; i++) {
      let name = `Worker #${i}`;
      if (this.algorithm === 'wu') {
        name = i === 1 ? 'Expansion Worker' : `Sim Worker #${i - 1}`;
      }
      this.workers.push(new SimulatedWorker(i, name, workerColors[(i - 1) % workerColors.length]));
    }
  }

  getActiveWorkers() {
    if (this.algorithm === 'uct') {
      return [this.workers[0]];
    }
    return this.workers.slice(0, this.workerCount);
  }

  updateWorkerUI() {
    this.workersGrid.innerHTML = '';
    const activeWorkers = this.getActiveWorkers();

    if (this.workerCountBadge) {
      this.workerCountBadge.textContent = `${activeWorkers.length} Active`;
    }

    activeWorkers.forEach(w => {
      const card = document.createElement('div');
      card.className = 'worker-badge-card';
      const isActive = w.state !== 'IDLE';
      if (isActive) card.classList.add('active');

      let badgeClass = 'badge';
      if (w.state === 'SELECTING') badgeClass = 'badge badge-info';
      else if (w.state === 'EXPANDING') badgeClass = 'badge badge-accent';
      else if (w.state === 'ROLLOUT' || w.state === 'SIMULATING') badgeClass = 'badge badge-warn';
      else if (w.state === 'BACKPROP' || w.state === 'COMMITTING') badgeClass = 'badge badge-success';

      const targetText = (w.targetMove !== null && w.targetMove !== undefined)
        ? `[${Math.floor(w.targetMove / 3)},${w.targetMove % 3}]`
        : 'Root';

      card.innerHTML = `
        <div class="worker-header">
          <span class="worker-title">
            <span class="worker-dot ${isActive ? 'pulse' : ''}" style="background-color: ${w.color}"></span>
            ${w.name}
          </span>
          <span class="${badgeClass}">${w.state}</span>
        </div>
        <div class="worker-task" title="${w.taskDesc}">
          ${w.taskDesc}
        </div>
        <div class="worker-stat-row">
          <span>Sims: <strong>${w.simulations}</strong></span>
          <span>Target: <strong>${targetText}</strong></span>
        </div>
      `;
      this.workersGrid.appendChild(card);
    });
  }

  updateQueueUI() {
    this.queueCount.textContent = `${this.workQueue.length} pending`;
    this.queueTrack.innerHTML = '';
    if (this.workQueue.length === 0) {
      this.queueTrack.innerHTML = '<span class="queue-empty">Queue empty - ready for WorkUnits</span>';
    } else {
      this.workQueue.slice(0, 6).forEach(unit => {
        const u = document.createElement('div');
        u.className = 'queue-unit';
        u.textContent = `Unit #${unit.id}`;
        this.queueTrack.appendChild(u);
      });
    }
  }

  renderRolloutPreview(state, outcome = null, reward = 0, moves = []) {
    this.rolloutGrid.innerHTML = '';
    if (!state) {
      this.rolloutResultBadge.textContent = 'Idle';
      this.rolloutResultBadge.className = 'badge';
      this.rolloutMeta.textContent = 'Rollout path and result will display during the Simulation phase.';
      this.rolloutReward.textContent = '';
      for (let i = 0; i < 9; i++) {
        const c = document.createElement('div');
        c.className = 'rollout-cell';
        this.rolloutGrid.appendChild(c);
      }
      return;
    }

    // Render cells of final rollout state
    for (let i = 0; i < 9; i++) {
      const c = document.createElement('div');
      c.className = 'rollout-cell';
      const val = state.grid[i];
      if (val === 'X') {
        c.textContent = 'X';
        c.style.color = 'var(--player-x)';
      } else if (val === 'O') {
        c.textContent = 'O';
        c.style.color = 'var(--player-o)';
      }
      this.rolloutGrid.appendChild(c);
    }

    if (outcome) {
      if (outcome.winner === 'DRAW') {
        this.rolloutResultBadge.textContent = 'Draw';
        this.rolloutResultBadge.className = 'badge';
      } else {
        this.rolloutResultBadge.textContent = `${outcome.winner} Won`;
        this.rolloutResultBadge.className = 'badge badge-success';
      }
      this.rolloutMeta.textContent = `Simulated ${moves.length} random moves to terminal state.`;
      this.rolloutReward.textContent = `Terminal Reward: ${reward.toFixed(1)}`;
    }
  }

  log(msg, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    const now = new Date();
    const timeStr = `${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    entry.innerHTML = `<span class="log-time">[${timeStr}]</span> ${msg}`;
    this.logStream.appendChild(entry);

    // Keep log stream bounded so it never grows or lags
    if (this.logStream.children.length > 80) {
      this.logStream.removeChild(this.logStream.firstChild);
    }

    this.logStream.scrollTop = this.logStream.scrollHeight;
  }
}

// Instantiate on load
window.addEventListener('DOMContentLoaded', () => {
  window.app = new MCTSVisualizerApp();
});
