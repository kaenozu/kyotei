#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final GPU Accelerated Predictor Test

Simple single-threaded test to demonstrate GPU acceleration performance
"""

import time
import numpy as np
import pandas as pd
import torch
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def generate_simple_race_data():
    """Generate single race data (6 racers)"""
    np.random.seed(42)
    
    feature_names = []
    for i in range(6):
        feature_names.extend([
            f'racer_{i+1}_age', f'racer_{i+1}_weight', f'racer_{i+1}_win_rate',
            f'racer_{i+1}_recent_performance', f'racer_{i+1}_motor_score',
            f'racer_{i+1}_boat_score', f'racer_{i+1}_start_timing',
            f'racer_{i+1}_course_experience', f'racer_{i+1}_position',
            f'racer_{i+1}_training_score'
        ])
    
    # Single race data
    race_data = []
    for i in range(6):
        racer_data = [
            np.random.randint(20, 60),           # age
            np.random.uniform(45, 80),           # weight  
            np.random.uniform(0.1, 0.8),         # win_rate
            np.random.uniform(0.0, 1.0),         # recent_performance
            np.random.uniform(0.3, 0.9),         # motor_score
            np.random.uniform(0.3, 0.9),         # boat_score
            np.random.uniform(-0.2, 0.2),        # start_timing
            np.random.uniform(0.2, 1.0),         # course_experience
            i + 1,                               # position (1-6)
            np.random.uniform(0.4, 1.0),         # training_score
        ]
        race_data.extend(racer_data)
    
    return pd.DataFrame([race_data], columns=feature_names)

def test_simple_gpu_predictor():
    """Test GPU predictor with minimal configuration"""
    print("=== Simple GPU Predictor Test ===")
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA: {torch.cuda.is_available()}")
    
    try:
        # Import with simplified config
        from ml.gpu_accelerated_predictor import GPUAcceleratedPredictor, GPUConfig
        
        # Create config with no multiprocessing
        config = GPUConfig(
            use_gpu=torch.cuda.is_available(),
            batch_size=64,
            num_workers=0,  # No multiprocessing
            pin_memory=False,
            enable_mixed_precision=False
        )
        
        predictor = GPUAcceleratedPredictor(config)
        print("GPU predictor initialized successfully")
        
        # Generate training data (simplified)
        print("\nGenerating training data...")
        np.random.seed(42)
        
        # Simple training data generation  
        num_samples = 1000
        X_data = []
        y_data = []
        
        for _ in range(num_samples):
            # Generate race features
            race_features = []
            for racer in range(6):
                features = [
                    np.random.randint(20, 60),      # age
                    np.random.uniform(45, 80),      # weight
                    np.random.uniform(0.1, 0.8),   # win_rate
                    np.random.uniform(0.0, 1.0),   # performance
                    np.random.uniform(0.3, 0.9),   # motor
                    np.random.uniform(0.3, 0.9),   # boat
                    np.random.uniform(-0.2, 0.2),  # timing
                    np.random.uniform(0.2, 1.0),   # experience
                    racer + 1,                      # position
                    np.random.uniform(0.4, 1.0),   # training
                ]
                race_features.extend(features)
            
            X_data.append(race_features)
            
            # Generate winner (simple rule-based)
            win_probs = [0.3, 0.25, 0.2, 0.15, 0.07, 0.03]  # Position advantage
            winner = np.random.choice(6, p=win_probs)
            y_data.append(winner)
        
        # Convert to DataFrame
        feature_names = []
        for i in range(6):
            feature_names.extend([
                f'racer_{i+1}_age', f'racer_{i+1}_weight', f'racer_{i+1}_win_rate',
                f'racer_{i+1}_recent_performance', f'racer_{i+1}_motor_score',
                f'racer_{i+1}_boat_score', f'racer_{i+1}_start_timing',
                f'racer_{i+1}_course_experience', f'racer_{i+1}_position',
                f'racer_{i+1}_training_score'
            ])
        
        df_train = pd.DataFrame(X_data, columns=feature_names)
        y_series = pd.Series(y_data)
        
        print(f"Training data: {df_train.shape}, targets: {y_series.shape}")
        
        # Train the model
        print("\n=== Training Phase ===")
        train_start = time.time()
        
        training_results = predictor.train(
            df_train, y_series, 
            epochs=20,  # Reduced epochs
            early_stopping_patience=5,
            validation_split=0.2
        )
        
        train_time = time.time() - train_start
        print(f"Training completed in {train_time:.2f} seconds")
        print(f"Training success: {training_results.get('success', False)}")
        
        # Test prediction speed
        print("\n=== Speed Benchmark ===")
        
        # Generate test race
        test_race = generate_simple_race_data()
        print(f"Test race data: {test_race.shape}")
        
        # Warmup
        for _ in range(5):
            try:
                _ = predictor.predict_gpu(test_race)
            except Exception as e:
                print(f"Warmup error: {e}")
                break
        
        # Benchmark
        times = []
        num_iterations = 50
        successful_predictions = 0
        
        print(f"Running {num_iterations} prediction iterations...")
        
        for i in range(num_iterations):
            start_time = time.perf_counter()
            
            try:
                result = predictor.predict_gpu(test_race)
                end_time = time.perf_counter()
                
                execution_time = end_time - start_time
                times.append(execution_time)
                successful_predictions += 1
                
                if i == 0:  # Show first prediction result
                    print(f"First prediction result shape: {result.shape if hasattr(result, 'shape') else type(result)}")
                
            except Exception as e:
                print(f"Prediction error (iteration {i}): {e}")
                continue
        
        # Results analysis
        if times:
            avg_time = np.mean(times)
            min_time = np.min(times)
            max_time = np.max(times)
            std_time = np.std(times)
            throughput = 1.0 / avg_time
            
            print(f"\n=== Performance Results ===")
            print(f"Successful predictions: {successful_predictions}/{num_iterations}")
            print(f"Average time: {avg_time:.4f}s")
            print(f"Min time: {min_time:.4f}s")
            print(f"Max time: {max_time:.4f}s")
            print(f"Std deviation: {std_time:.4f}s")
            print(f"Throughput: {throughput:.1f} predictions/sec")
            
            # Goal evaluation
            current_baseline = 0.12  # Current system baseline
            target_min = 0.01
            target_max = 0.05
            target_speedup = 10
            
            actual_speedup = current_baseline / avg_time if avg_time > 0 else 0
            
            print(f"\n=== Goal Evaluation ===")
            print(f"Baseline time: {current_baseline:.4f}s")
            print(f"Target range: {target_min:.4f}s - {target_max:.4f}s")
            print(f"Actual time: {avg_time:.4f}s")
            print(f"Speedup achieved: {actual_speedup:.1f}x")
            print(f"Target speedup: {target_speedup}x")
            
            # Final assessment
            time_goal = target_min <= avg_time <= target_max
            speedup_goal = actual_speedup >= target_speedup
            
            print(f"\nTime goal: {'ACHIEVED' if time_goal else 'PARTIAL - ' + ('Too fast' if avg_time < target_min else 'Too slow')}")
            print(f"Speedup goal: {'ACHIEVED' if speedup_goal else 'NOT ACHIEVED'}")
            
            if time_goal and speedup_goal:
                print("Overall: SUCCESS - All performance goals achieved!")
            elif speedup_goal:
                print("Overall: PARTIAL SUCCESS - Speedup achieved but time outside target range")
            else:
                print("Overall: NEEDS IMPROVEMENT - Performance goals not fully met")
                
            # Additional metrics
            if avg_time < current_baseline:
                improvement = ((current_baseline - avg_time) / current_baseline) * 100
                print(f"Performance improvement: {improvement:.1f}% faster than baseline")
            
        else:
            print("No successful predictions - cannot benchmark performance")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("GPU Accelerated Predictor - Final Performance Test")
    print("=" * 55)
    
    test_simple_gpu_predictor()
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()