# Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem
University Capstone Research Project on Parallel MCTS for Strategic Planning in Robotics using the Orienteering Problem



Single threaded MCTS
Root and Leaf
VL-UCT and WU-UCT
Batch

Find the format description for Tsiligirides and Chao

*********************
* OP test instances *
*********************

The first line contains the following data: 

	Tmax P

Where
	Tmax 	= available time budget per path
	P	= number of paths (=1)


The remaining lines contain the data of each point. 
For each point, the line contains the following data:

	x y S

Where
	x	= x coordinate 
	y	= y coordinate
	S	= score

* REMARKS *
	- The first point is the starting point.
	- The second point is the ending point.
	- The Euclidian distance is used.



# go to project root
cd /Users/reubenkappely/Documents/Projects/Parallel-Monte-Carlo-Tree-Search-For-The-Orienteering-Problem

# (optional) create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate

# install dependency
pip install matplotlib

# run (ensures repo root is on PYTHONPATH)
PYTHONPATH=$(pwd) python3 viz/mcts_viz.py

# alternatively (if you already run from repo root)
python3 viz/mcts_viz.py