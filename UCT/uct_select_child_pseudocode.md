# UCT Select Child - Pseudocode

## Method Signature
```
Function uct_select_child(node, exploration_constant = √2):
    Returns: Best child node selected by UCT formula
```

## Pseudocode

```
FUNCTION uct_select_child(node, exploration_constant):
    
    // STEP 1: Check if node has any children
    IF node.children is empty THEN
        RAISE ERROR "Cannot select child from node with no children"
    END IF
    
    // STEP 2: Prioritize unvisited children first
    unvisited_children = []
    FOR EACH child IN node.children DO
        IF child.visits == 0 THEN
            ADD child TO unvisited_children
        END IF
    END FOR
    
    // If any unvisited children exist, pick one randomly
    IF unvisited_children is not empty THEN
        RETURN random_choice(unvisited_children)
    END IF
    
    // STEP 3: All children visited - calculate UCT values
    parent_visits = MAX(1, node.visits)
    ln_parent_visits = ln(parent_visits)
    
    best_child = NULL
    best_uct_value = -∞
    
    // STEP 4: Evaluate each child using UCT formula
    FOR EACH child IN node.children DO
        
        // Safety check (shouldn't happen but defensive)
        IF child.visits == 0 THEN
            RETURN child
        END IF
        
        // Calculate UCT components
        exploitation = child.total_reward / child.visits
        exploration = exploration_constant × √(ln_parent_visits / child.visits)
        uct_value = exploitation + exploration
        
        // Track best child
        IF uct_value > best_uct_value THEN
            best_uct_value = uct_value
            best_child = child
        END IF
    END FOR
    
    // STEP 5: Return child with highest UCT value
    RETURN best_child

END FUNCTION
```

## Detailed Breakdown

### Step 1: Validation
```
IF node.children is empty:
    ERROR
```
- Ensures we have children to select from
- Prevents invalid operations

### Step 2: Prefer Unvisited Children
```
unvisited = [child for child in children if child.visits == 0]
IF unvisited exists:
    RETURN random choice from unvisited
```
- **Why?** Unvisited nodes have unknown potential
- Ensures all children get at least one visit
- Random choice breaks ties
- This is the **exploration** component in action

### Step 3: Setup for UCT Calculation
```
parent_visits = max(1, node.visits)
ln_parent_visits = ln(parent_visits)
```
- Get parent's visit count (ensure at least 1)
- Pre-calculate logarithm for efficiency
- Used in exploration term for all children

### Step 4: Calculate UCT for Each Child
```
FOR each child:
    exploitation = child.total_reward / child.visits
    exploration = c × √(ln(parent_visits) / child.visits)
    uct_value = exploitation + exploration
```

**Exploitation Term:**
```
Q/N = child.total_reward / child.visits
```
- Average reward of this child
- Higher = better past performance
- Encourages visiting **proven good** choices

**Exploration Term:**
```
c × √(ln(N_parent) / N_child)
```
- Uncertainty bonus
- Higher when child visited less
- Decreases as child gets more visits
- Encourages visiting **uncertain** choices

**Combined:**
```
UCT = Average Reward + Uncertainty Bonus
    = Q/N + c × √(ln(N_parent) / N_child)
```

### Step 5: Select Best
```
best_child = argmax(uct_value for child in children)
RETURN best_child
```
- Choose child with highest UCT value
- Balances exploitation and exploration

## Mathematical Details

### UCT Formula Components

```
UCT(child) = Q/N + c × √(ln(N_parent) / N_child)

Where:
    Q           = total_reward of child (sum of all simulation rewards)
    N_child     = visits of child (number of simulations)
    N_parent    = visits of parent node
    c           = exploration_constant (typically √2 ≈ 1.414)
    ln          = natural logarithm
```

### Behavior Analysis

**High Exploitation (Q/N is large):**
- Child has high average reward
- Proven performer
- Tends to get selected

**High Exploration (second term is large):**
- Child has few visits (small N_child)
- Uncertainty is high
- Gets bonus to be explored

**Over Time:**
- Exploration term decreases as visits increase
- Selection converges to best performing child
- Balance controlled by constant `c`

### Example Calculation

```
Parent: visits = 100

Child A:
    visits = 10
    total_reward = 5.0
    
    exploitation = 5.0 / 10 = 0.5
    exploration = √2 × √(ln(100) / 10) = 1.414 × √(4.605 / 10) 
                = 1.414 × 0.679 = 0.960
    UCT = 0.5 + 0.960 = 1.460

Child B:
    visits = 50
    total_reward = 28.0
    
    exploitation = 28.0 / 50 = 0.56
    exploration = √2 × √(ln(100) / 50) = 1.414 × √(4.605 / 50)
                = 1.414 × 0.304 = 0.430
    UCT = 0.56 + 0.430 = 0.990

Result: Select Child A (higher UCT despite lower average reward!)
```

**Why Child A?**
- Child B has slightly better exploitation (0.56 vs 0.5)
- But Child A has much higher exploration bonus (0.960 vs 0.430)
- Child A is less explored, deserves more investigation
- This prevents premature convergence to local optima

## Flowchart

```
                    ┌─────────────────────┐
                    │  uct_select_child   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Has children?        │
                    └──────┬───────────────┘
                           │ No
                           ├─────────► ERROR
                           │ Yes
                           ▼
                    ┌──────────────────────┐
                    │ Any unvisited?       │
                    └──────┬───────────────┘
                           │ Yes
                           ├─────────► Random choice from unvisited
                           │ No
                           ▼
                    ┌──────────────────────┐
                    │ Calculate UCT for    │
                    │ each child           │
                    └──────┬───────────────┘
                           │
                           ▼
            ┌──────────────────────────────────┐
            │  For each child:                 │
            │  exploitation = Q/N              │
            │  exploration = c×√(ln(Np)/Nc)   │
            │  uct = exploitation + exploration│
            └──────────────┬───────────────────┘
                           │
                           ▼
                    ┌──────────────────────┐
                    │ Select child with    │
                    │ max UCT value        │
                    └──────┬───────────────┘
                           │
                           ▼
                    ┌──────────────────────┐
                    │ Return best child    │
                    └──────────────────────┘
```

## Key Properties

### 1. **Exploration-Exploitation Balance**
```
As visits increase:
    - Exploitation term stays relatively stable
    - Exploration term decreases (√(ln(N)/n) shrinks)
    - Eventually favors best performing child
```

### 2. **Optimistic Initialization**
```
Unvisited children (visits=0) selected first:
    - Gives every child at least one chance
    - Prevents ignoring potentially good branches
    - Random selection among unvisited breaks symmetry
```

### 3. **Logarithmic Growth**
```
Using ln(parent_visits):
    - Exploration decreases slowly
    - Not too aggressive in convergence
    - Proven theoretically optimal
```

### 4. **Regret Bounds**
```
UCT provides logarithmic regret bounds:
    - Provably converges to optimal action
    - Balances exploration efficiently
    - Standard in MCTS algorithms
```

## Comparison with Other Selection Strategies

### UCT (Used Here)
```
UCT = Q/N + c × √(ln(N_parent) / N_child)
✓ Theoretical guarantees
✓ Balanced exploration
✓ Standard in MCTS
```

### ε-Greedy
```
With probability ε: random child
With probability 1-ε: best average reward
✗ No adaptive exploration
✗ Fixed exploration rate
```

### Softmax
```
P(child) ∝ exp(Q/N / temperature)
✓ Smooth probability distribution
✗ No exploration bonus
✗ Requires temperature tuning
```

### Pure Exploitation
```
Always select max(Q/N)
✗ No exploration
✗ Gets stuck in local optima
```

## Tuning the Exploration Constant

### Default: c = √2 ≈ 1.414
- Theoretically optimal for many problems
- Good starting point

### Higher c (e.g., 2.0):
- More exploration
- Slower convergence
- Better for:
  - Large action spaces
  - Deceptive reward landscapes
  - When avoiding local optima is critical

### Lower c (e.g., 0.5):
- Less exploration
- Faster convergence
- Better for:
  - Small action spaces
  - Clear reward signals
  - When exploitation is more valuable

### Adaptive c:
- Could adjust based on problem features
- Not implemented in this version
- Research area for improvement

## Summary

**The algorithm:**
1. Prefers unvisited children (pure exploration)
2. Otherwise, uses UCT formula to balance:
   - **Exploitation:** Average past performance (Q/N)
   - **Exploration:** Uncertainty bonus (c√(ln(Np)/Nc))
3. Selects child with maximum UCT value

**Result:** Efficient exploration that converges to optimal choices while avoiding premature commitment to local optima.
