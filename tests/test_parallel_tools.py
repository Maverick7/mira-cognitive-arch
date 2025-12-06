import time
import json
from concurrent.futures import ThreadPoolExecutor

def test_mock_tool_execution():
    print("--- Testing Tool Logic ---")
    
    # Mock Extrinsic Output
    extrinsic_report = '{"tool": "calc", "args": {"expression": "25 * 4"}}'
    
    # Tool Registry Mock
    def calc(expression):
        return eval(expression)
        
    tools = {"calc": calc}
    
    if "{" in extrinsic_report and '"tool":' in extrinsic_report:
        start = extrinsic_report.find("{")
        end = extrinsic_report.rfind("}")
        call_data = json.loads(extrinsic_report[start:end+1])
        tool_name = call_data.get("tool")
        tool_args = call_data.get("args")
        
        print(f"Detected Tool: {tool_name}")
        if tool_name in tools:
            res = tools[tool_name](**tool_args)
            print(f"Result: {res}")
            assert res == 100
            print("✅ Tool Execution Logic works.")
        else:
            print("❌ Tool not found.")
    else:
        print("❌ JSON detection failed.")

def test_parallel_sim():
    print("\n--- Testing Parallel Simulation ---")
    start_time = time.time()
    
    def mock_agent(name):
        time.sleep(1.0) # Simulate LLM latency
        return f"Report from {name}"
        
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(mock_agent, name) for name in ["A", "B", "C", "D"]]
        results = [f.result() for f in futures]
        
    duration = time.time() - start_time
    print(f"Total Duration: {duration:.2f}s")
    
    # Should be ~1.0s, not 4.0s
    if duration < 1.5:
        print("✅ Parallel execution confirmed (approx 1s).")
    else:
        print(f"❌ Too slow ({duration}s) - Sequential?")

if __name__ == "__main__":
    test_mock_tool_execution()
    test_parallel_sim()
