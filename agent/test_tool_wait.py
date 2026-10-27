import unittest
from unittest.mock import patch
import yohaku_agent as agent


class ToolWaitTests(unittest.TestCase):
    def tools(self, results):
        self.requests=[]
        def execute(request):
            self.requests.append(request)
            return results.pop(0)
        return agent.Tools(execute, permissions={'run':True,'read':True}, native=True)

    def test_wait_pins_run_and_retains_final_exit_and_log(self):
        for code in [0,7]:
            final={'state':'finished' if code==0 else 'failed','run_id':'one','exit_code':code,'log_path':'tools/logs/one.log'}
            tools=self.tools([{'state':'starting','run_id':'one'},{'state':'running','run_id':'one'},final])
            with patch.object(agent.time,'sleep'):
                result=tools.call('run_tool',{'id':'demo','wait':True})
            self.assertTrue(result['ok'],result)
            self.assertEqual(result['result'],final)
            self.assertEqual(self.requests[1:], [{'command':'tool_status','run_id':'one'}]*2)

    def test_wait_budget_returns_running_without_inventing_exit(self):
        running={'state':'running','run_id':'one','exit_code':None}
        tools=self.tools([running])
        with patch.object(agent.time,'monotonic',side_effect=[10,41]):
            result=tools.call('tool_status',{'wait':True})
        self.assertEqual(result['result'],running)
        self.assertEqual(len(self.requests),1)

    def test_same_tool_new_run_must_not_supply_old_wait_result(self):
        tools=self.tools([{'tool_id':'same','state':'running','run_id':'old'}, {'tool_id':'same','state':'finished','run_id':'new','exit_code':0}])
        with patch.object(agent.time,'sleep'):
            result=tools.call('run_tool',{'id':'same','wait':True})
        self.assertFalse(result['ok'])
        self.assertIn('run changed',result['error'])

    def test_terminal_missing_exit_diagnostic_is_not_converted_to_success(self):
        final={'state':'failed','run_id':'one','exit_code':None,'status':'Tool connection ended without an exit event: exit status: 0'}
        tools=self.tools([{'state':'running','run_id':'one'},final])
        with patch.object(agent.time,'sleep'):
            result=tools.call('run_tool',{'id':'demo','wait':True})
        self.assertEqual(result['result'],final)


if __name__=='__main__':
    unittest.main()
