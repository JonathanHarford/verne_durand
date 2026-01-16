# /// script
# dependencies = [
#   "httpx",
# ]
# ///
import unittest
from unittest.mock import MagicMock, patch
import time
import sys
import os
import importlib.util

# Import the logic we want to test. 
spec = importlib.util.spec_from_file_location("ralph_wiggum_jules", "ralph-wiggum-jules.py")
ralph = importlib.util.module_from_spec(spec)
sys.modules["ralph_wiggum_jules"] = ralph
spec.loader.exec_module(ralph)

class TestStaleSession(unittest.TestCase):
    @patch('time.sleep', return_value=None)
    def test_stale_cancellation(self, mock_sleep):
        # Setup mock API
        api = MagicMock()
        api.get_session.return_value = {"state": "RUNNING"}
        # Return empty activities to simulate no progress
        api.list_activities.return_value = []
        
        # Override threshold for fast test
        with patch('ralph_wiggum_jules.STALE_THRESHOLD_SEC', 1):
            session_id = "test-session"
            # We need to simulate time passing. 
            # The loop uses time.time(). 
            # We can mock time.time() to advance.
            start_time = 1000
            with patch('time.time') as mock_time:
                # 1. Start time
                # 2. Inside loop: check session
                # 3. Inside loop: check activities
                # 4. Inside loop: current time for stale check
                mock_time.side_effect = [
                    start_time,           # start_time init in function
                    start_time,           # last_act_time init
                    start_time + 0.1,     # while condition check
                    start_time + 0.2,     # get_session
                    start_time + 0.3,     # list_activities
                    start_time + 2.0,     # stale check (STALE!)
                ]
                
                success, status, session = ralph.wait_for_session(api, session_id, 100)
                
                self.assertFalse(success)
                self.assertEqual(status, "STALE")
                api.delete_session.assert_called_once_with(session_id)

    @patch('time.sleep', return_value=None)
    def test_progress_resets_stale(self, mock_sleep):
        api = MagicMock()
        api.get_session.side_effect = [{"state": "RUNNING"}, {"state": "RUNNING"}, {"state": "COMPLETED"}]
        
        # First poll: 0 activities
        # Second poll: 1 activity (progress!)
        api.list_activities.side_effect = [[], [{"id": "act1"}]]
        
        with patch('ralph_wiggum_jules.STALE_THRESHOLD_SEC', 5):
            session_id = "test-session"
            start_time = 1000
            with patch('time.time') as mock_time:
                mock_time.side_effect = [
                    start_time,           # start_time
                    start_time,           # last_act_time
                    start_time + 0.1,     # loop 1 condition
                    start_time + 0.2,     # loop 1 get_session
                    start_time + 0.3,     # loop 1 list_activities
                    start_time + 0.4,     # loop 1 stale check
                    start_time + 4.0,     # loop 2 condition
                    start_time + 4.1,     # loop 2 get_session (RUNNING)
                    start_time + 4.2,     # loop 2 list_activities (1 act)
                    start_time + 4.3,     # loop 2 update last_act_time
                    start_time + 4.4,     # loop 2 stale check
                    start_time + 8.0,     # loop 3 condition
                    start_time + 8.1,     # loop 3 get_session (COMPLETED)
                ]
                
                success, status, session = ralph.wait_for_session(api, session_id, 100)
                
                self.assertTrue(success)
                self.assertEqual(status, "COMPLETED")
                api.delete_session.assert_not_called()

if __name__ == '__main__':
    unittest.main()
