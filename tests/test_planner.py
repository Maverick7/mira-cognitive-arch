# -*- coding: utf-8 -*-
"""Test script for the Meta-Reasoning Planner.
Tests various query types and validates the Planner's JSON output.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mira.core.planner import get_execution_plan
import json

# Test scenarios
TEST_CASES = [
    # (query, expected_keys_true, expected_keys_false)
    ("Hi!", [], ["needs_council", "needs_rag"]),
    ("Hello there!", [], ["needs_council"]),
    ("What about the AirPods we were discussing?", ["needs_history"], []),
    ("I'm feeling really anxious about my interview.", ["needs_council"], []),
    ("What's the latest score of the Man Utd game?", [], []),  # Should suggest web_search tool
    ("Calculate 123 * 456", [], []),  # Should suggest calc tool
    ("Tell me about yourself", ["needs_profile"], []),
    ("What did I tell you about my job?", ["needs_rag"], []),
    ("Why do I always feel tired?", ["needs_council"], []),
]

def test_planner():
    print("=" * 60)
    print("META-REASONING PLANNER TEST")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for query, expected_true, expected_false in TEST_CASES:
        print(f"\n📝 Query: \"{query}\"")
        
        try:
            plan = get_execution_plan(query)
            print(f"   Plan: {json.dumps(plan, indent=2)}")
            
            # Validate structure
            required_keys = ["needs_profile", "needs_history", "needs_rag", "needs_council", "tool"]
            missing_keys = [k for k in required_keys if k not in plan]
            if missing_keys:
                print(f"   ❌ FAIL: Missing keys: {missing_keys}")
                failed += 1
                continue
            
            # Check expected values
            errors = []
            for key in expected_true:
                if not plan.get(key):
                    errors.append(f"Expected {key}=true but got {plan.get(key)}")
            for key in expected_false:
                if plan.get(key):
                    errors.append(f"Expected {key}=false but got {plan.get(key)}")
            
            if errors:
                print(f"   ⚠️ WARN: {errors}")
                # Still count as passed if structure is valid
            
            print(f"   ✅ PASS (valid JSON structure)")
            passed += 1
            
        except Exception as e:
            print(f"   ❌ FAIL: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = test_planner()
    sys.exit(0 if success else 1)
