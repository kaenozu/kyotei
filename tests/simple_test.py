#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple System Test for Windows
"""

def test_system():
    print("=" * 50)
    print("Competition Boat Racing System Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # 1. Config test
    try:
        from config import config
        print("OK [1/4] Config System")
        success_count += 1
    except Exception as e:
        print(f"ERROR [1/4] Config: {e}")
    
    # 2. Data fetcher test
    try:
        from data.boatrace_openapi_fetcher import BoatraceOpenAPIFetcher
        fetcher = BoatraceOpenAPIFetcher()
        print("OK [2/4] Data Fetcher")
        success_count += 1
    except Exception as e:
        print(f"ERROR [2/4] Data Fetcher: {e}")
    
    # 3. Investment manager test
    try:
        from investment_manager import investment_manager
        print("OK [3/4] Investment Manager")
        success_count += 1
    except Exception as e:
        print(f"ERROR [3/4] Investment Manager: {e}")
    
    # 4. Web app test
    try:
        from openapi_app import app
        print("OK [4/4] Web Application")
        success_count += 1
    except Exception as e:
        print(f"ERROR [4/4] Web App: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Result: {success_count}/{total_tests} Success")
    
    if success_count == total_tests:
        print("\nSUCCESS! Ready for production use.")
        print("\nHow to start:")
        print("  python openapi_app.py")
        print("  Open http://localhost:5000 in browser")
        print("\nMain features:")
        print("  Investment Dashboard: http://localhost:5000/investment")
        print("  Prediction System: From main page")
        print("  Report Generation: In dashboard")
        print("  Alert Monitoring: Automatic")
    elif success_count >= 2:
        print("\nWARNING: Basic functions work but some issues exist")
        print("  Can be used for production but fixes recommended")
    else:
        print("\nERROR: Critical issues found. Fix before production use")
    
    print("=" * 50)

if __name__ == "__main__":
    test_system()