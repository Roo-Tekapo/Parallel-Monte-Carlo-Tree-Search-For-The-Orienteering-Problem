#!/bin/bash
# Benchmark Presets
# Collection of useful benchmark configurations

# Make scripts executable
chmod +x run_benchmark.py quick_test.py

echo "======================================================================"
echo "Benchmark Runner - Common Configurations"
echo "======================================================================"
echo ""
echo "Available presets:"
echo ""
echo "1. Quick Test (verify all algorithms work)"
echo "   python quick_test.py"
echo ""
echo "2. Small Dataset Comparison (fast, ~5 minutes)"
echo "   python run_benchmark.py --dataset sample --algorithms all --iterations 5000"
echo ""
echo "3. Medium Dataset Comparison (moderate, ~30 minutes)"
echo "   python run_benchmark.py --dataset grid_sample --algorithms all --iterations 10000"
echo ""
echo "4. Large Dataset with Time Limit (1 hour)"
echo "   python run_benchmark.py --dataset set_64_1 --algorithms all --max-time 60"
echo ""
echo "5. Parallel Algorithm Comparison (4 workers)"
echo "   python run_benchmark.py --dataset parallel_friendly_v2 --algorithms simple_wu vl --workers 4"
echo ""
echo "6. OR-Tools Only on All Datasets"
echo "   python run_benchmark.py --dataset all --algorithms ortools --ortools-time 60"
echo ""
echo "7. Comprehensive Test (WARNING: may take hours)"
echo "   python run_benchmark.py --dataset all --algorithms all --iterations 10000 --output comprehensive_results.xlsx"
echo ""
echo "8. Worker Scaling Test (test 2, 4, 8 workers)"
echo "   python run_benchmark.py --dataset grid_sample --algorithms vl --workers 2 --output vl_2w.xlsx"
echo "   python run_benchmark.py --dataset grid_sample --algorithms vl --workers 4 --output vl_4w.xlsx"
echo "   python run_benchmark.py --dataset grid_sample --algorithms vl --workers 8 --output vl_8w.xlsx"
echo ""
echo "9. Virtual Loss Tuning Test"
echo "   python run_benchmark.py --dataset sample --algorithms vl --vl-value 0.5 --output vl_0.5.xlsx"
echo "   python run_benchmark.py --dataset sample --algorithms vl --vl-value 1.0 --output vl_1.0.xlsx"
echo "   python run_benchmark.py --dataset sample --algorithms vl --vl-value 2.0 --output vl_2.0.xlsx"
echo ""
echo "======================================================================"
echo ""
read -p "Enter preset number to run (or press Enter to exit): " choice

case $choice in
    1)
        echo "Running Quick Test..."
        python quick_test.py
        ;;
    2)
        echo "Running Small Dataset Comparison..."
        python run_benchmark.py --dataset sample --algorithms all --iterations 5000
        ;;
    3)
        echo "Running Medium Dataset Comparison..."
        python run_benchmark.py --dataset grid_sample --algorithms all --iterations 10000
        ;;
    4)
        echo "Running Large Dataset with Time Limit..."
        python run_benchmark.py --dataset set_64_1 --algorithms all --max-time 60
        ;;
    5)
        echo "Running Parallel Algorithm Comparison..."
        python run_benchmark.py --dataset parallel_friendly_v2 --algorithms simple_wu vl --workers 4
        ;;
    6)
        echo "Running OR-Tools Only..."
        python run_benchmark.py --dataset all --algorithms ortools --ortools-time 60
        ;;
    7)
        echo "Running Comprehensive Test (this may take a long time)..."
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            python run_benchmark.py --dataset all --algorithms all --iterations 10000 --output comprehensive_results.xlsx
        else
            echo "Cancelled."
        fi
        ;;
    8)
        echo "Running Worker Scaling Test..."
        python run_benchmark.py --dataset grid_sample --algorithms vl --workers 2 --output vl_2w.xlsx
        python run_benchmark.py --dataset grid_sample --algorithms vl --workers 4 --output vl_4w.xlsx
        python run_benchmark.py --dataset grid_sample --algorithms vl --workers 8 --output vl_8w.xlsx
        echo "Results saved to: vl_2w.xlsx, vl_4w.xlsx, vl_8w.xlsx"
        ;;
    9)
        echo "Running Virtual Loss Tuning Test..."
        python run_benchmark.py --dataset sample --algorithms vl --vl-value 0.5 --output vl_0.5.xlsx
        python run_benchmark.py --dataset sample --algorithms vl --vl-value 1.0 --output vl_1.0.xlsx
        python run_benchmark.py --dataset sample --algorithms vl --vl-value 2.0 --output vl_2.0.xlsx
        echo "Results saved to: vl_0.5.xlsx, vl_1.0.xlsx, vl_2.0.xlsx"
        ;;
    *)
        echo "Exiting..."
        ;;
esac
