#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified GPU Accelerated Predictor Test

Target: Verify 10-12x speed improvement from 0.12sec to 0.01-0.05sec
"""

import time
import numpy as np
import pandas as pd
import torch
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_gpu_availability():
    """Test GPU availability"""
    print("=== GPU Availability Test ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"Current GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
    else:
        print("CUDA not available - running CPU tests only")
    print()

def generate_simple_test_data(num_races=100):
    """Generate simple test data"""
    print(f"Generating test data for {num_races} races...")
    
    np.random.seed(42)
    data = []
    
    for race_id in range(num_races):
        for racer_num in range(1, 7):
            row = {
                'race_id': f"race_{race_id:04d}",
                'racer_number': racer_num,
                'age': np.random.randint(20, 60),
                'weight': np.random.uniform(45, 80),
                'win_rate': np.random.uniform(0.1, 0.8),
                'recent_performance': np.random.uniform(0.0, 1.0),
                'motor_score': np.random.uniform(0.3, 0.9),
                'boat_score': np.random.uniform(0.3, 0.9),
                'start_timing': np.random.uniform(-0.2, 0.2),
                'course_experience': np.random.uniform(0.2, 1.0),
            }
            data.append(row)
    
    df = pd.DataFrame(data)
    print(f"Generated {len(df)} rows of test data")
    return df

def test_basic_import():
    """Test basic module imports"""
    print("=== Import Test ===")
    
    try:
        from ml.gpu_accelerated_predictor import GPUAcceleratedPredictor
        print("GPU predictor import: SUCCESS")
        return GPUAcceleratedPredictor
    except ImportError as e:
        print(f"GPU predictor import: FAILED - {e}")
        return None

def test_gpu_predictor_creation(predictor_class):
    """Test GPU predictor creation"""
    print("=== GPU Predictor Creation Test ===")
    
    if predictor_class is None:
        print("Skipping GPU predictor test - import failed")
        return None
        
    try:
        predictor = predictor_class()
        print("GPU predictor creation: SUCCESS")
        return predictor
    except Exception as e:
        print(f"GPU predictor creation: FAILED - {e}")
        return None

def measure_prediction_time(predictor, test_data, iterations=10):
    """Measure prediction time"""
    print(f"Measuring prediction time ({iterations} iterations)...")
    
    if predictor is None:
        print("No predictor available")
        return None
    
    times = []
    race_data = test_data.head(6)  # Single race (6 racers)
    
    # Warmup
    for _ in range(3):
        try:
            if hasattr(predictor, 'predict_gpu'):
                _ = predictor.predict_gpu(race_data)
            elif hasattr(predictor, 'predict'):
                _ = predictor.predict(race_data)
            else:
                print("No predict method found")
                return None
        except Exception:
            pass
    
    # Actual measurement
    for i in range(iterations):
        start_time = time.perf_counter()
        
        try:
            if hasattr(predictor, 'predict_gpu'):
                result = predictor.predict_gpu(race_data)
            elif hasattr(predictor, 'predict'):
                result = predictor.predict(race_data)
            else:
                print("No predict method found")
                break
                
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            times.append(execution_time)
            
        except Exception as e:
            print(f"Prediction error (iteration {i}): {e}")
            continue
    
    if times:
        avg_time = np.mean(times)
        min_time = np.min(times)
        max_time = np.max(times)
        
        print(f"Average time: {avg_time:.4f}s")
        print(f"Min time: {min_time:.4f}s")
        print(f"Max time: {max_time:.4f}s")
        print(f"Throughput: {1.0/avg_time:.1f} predictions/sec")
        
        return {
            'avg_time': avg_time,
            'min_time': min_time,
            'max_time': max_time,
            'throughput': 1.0/avg_time
        }
    else:
        print("No successful predictions")
        return None

def evaluate_performance_goals(results):
    """Evaluate performance against goals"""
    print("\n=== Performance Goal Evaluation ===")
    
    if results is None:
        print("No results to evaluate")
        return
    
    current_baseline = 0.12  # Current baseline: 0.12 seconds
    target_min = 0.01        # Target minimum: 0.01 seconds
    target_max = 0.05        # Target maximum: 0.05 seconds
    target_speedup = 10      # Target speedup: 10x
    
    avg_time = results['avg_time']
    actual_speedup = current_baseline / avg_time if avg_time > 0 else 0
    
    print(f"Current baseline: {current_baseline:.4f}s")
    print(f"Target range: {target_min:.4f}s - {target_max:.4f}s")
    print(f"Actual time: {avg_time:.4f}s")
    print(f"Target speedup: {target_speedup}x")
    print(f"Actual speedup: {actual_speedup:.1f}x")
    
    # Goal evaluation
    time_goal_met = target_min <= avg_time <= target_max
    speedup_goal_met = actual_speedup >= target_speedup
    
    print(f"\nTime goal: {'ACHIEVED' if time_goal_met else 'NOT ACHIEVED'}")
    print(f"Speedup goal: {'ACHIEVED' if speedup_goal_met else 'NOT ACHIEVED'}")
    print(f"Overall: {'SUCCESS' if time_goal_met and speedup_goal_met else 'NEEDS IMPROVEMENT'}")

def main():
    """Main test function"""
    print("GPU Accelerated Predictor - Performance Test")
    print("=" * 50)
    
    # Test GPU availability
    test_gpu_availability()
    
    # Generate test data
    test_data = generate_simple_test_data(100)
    
    # Test imports
    predictor_class = test_basic_import()
    
    # Test predictor creation
    predictor = test_gpu_predictor_creation(predictor_class)
    
    # Measure performance
    if predictor:
        print("\n=== Performance Measurement ===")
        results = measure_prediction_time(predictor, test_data, iterations=20)
        evaluate_performance_goals(results)
    else:
        print("Cannot perform benchmarks - predictor initialization failed")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()