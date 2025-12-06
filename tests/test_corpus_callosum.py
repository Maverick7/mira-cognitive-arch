import unittest
from mira.env.corpus_callosum import CorpusCallosumEnv

class TestCorpusCallosumEnv(unittest.TestCase):
    def test_env_flow(self):
        env = CorpusCallosumEnv("Should I learn Rust?", ltm_context="User likes low-level programming.")
        state = env.reset()
        
        # Step 1: Intrinsic (Right Brain)
        next_agent = env._get_next_agent()
        self.assertEqual(next_agent, "intrinsic")
        prompt = env.get_expert_prompt(next_agent)
        self.assertIn("Intrinsic Motivation Expert", prompt)
        
        state, reward, done, info = env.step({"agent_type": "intrinsic", "content": "It is fun."})
        self.assertFalse(done)
        self.assertEqual(state["reports"]["intrinsic"], "It is fun.")
        
        # Step 2: Extrinsic (Left Brain)
        next_agent = env._get_next_agent()
        self.assertEqual(next_agent, "extrinsic")
        prompt = env.get_expert_prompt(next_agent)
        self.assertIn("Extrinsic Goals Expert", prompt)
        
        state, reward, done, info = env.step({"agent_type": "extrinsic", "content": "It pays well."})
        self.assertFalse(done)
        
        # Step 3: Safety
        next_agent = env._get_next_agent()
        self.assertEqual(next_agent, "safety")
        
        state, reward, done, info = env.step({"agent_type": "safety", "content": "Safe."})
        self.assertFalse(done)
        
        # Step 4: Adversarial
        next_agent = env._get_next_agent()
        self.assertEqual(next_agent, "adversarial")
        
        state, reward, done, info = env.step({"agent_type": "adversarial", "content": "Hard to learn."})
        self.assertFalse(done)
        
        # Step 5: Council
        next_agent = env._get_next_agent()
        self.assertEqual(next_agent, "council")
        prompt = env.get_expert_prompt(next_agent)
        self.assertIn("Global Value Council", prompt)
        self.assertIn("It is fun.", prompt) # Check if reports are included
        
        state, reward, done, info = env.step({"agent_type": "council", "content": "Do it."})
        self.assertTrue(done)
        self.assertEqual(state["final_decision"], "Do it.")

if __name__ == '__main__':
    unittest.main()
