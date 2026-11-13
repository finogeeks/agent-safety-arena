"""Preparation must find the current owned desktop endpoint, without a model call."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock,patch
import urllib.error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.adapters.agents import dsh
URL='http://127.0.0.1:58023/?token=syntheticTokenValue001'

class ReadinessTests(unittest.TestCase):
    def test_old_heap_url_is_not_selected_over_current_owned_port(self):
        blob=(URL+'\nhttp://127.0.0.1:9/?token=syntheticTokenValue002').encode('ascii')
        self.assertEqual(dsh.loopback_url_in(blob,allowed_ports={58023}),URL)
        self.assertIsNone(dsh.loopback_url_in(blob,allowed_ports={1}))

    def test_non_listening_owned_main_can_supply_backend_url(self):
        with patch.object(dsh,'_descendant_pids',return_value=[11,12]), \
             patch.object(dsh,'_listening_ports',return_value={12:{58023}},create=True), \
             patch.object(dsh,'_process_url',side_effect=lambda pid,**kw:URL if pid==11 else None) as scan:
            self.assertEqual(dsh.desktop_host_url(10,main_pid=11),URL)
        self.assertEqual(scan.call_args_list[0].args,(11,))

    def test_unknown_main_pid_is_not_read(self):
        with patch.object(dsh,'_descendant_pids',return_value=[12]), \
             patch.object(dsh,'_listening_ports',return_value={12:{58023}},create=True), \
             patch.object(dsh,'_process_url',return_value=URL) as scan:
            self.assertEqual(dsh.desktop_host_url(10,main_pid=99),URL)
        self.assertEqual([call.args[0] for call in scan.call_args_list],[12])

    def prepare_fixture(self,folder):
        root=Path(folder);workspace=root/'workspace';workspace.mkdir()
        evidence=root/'evidence';evidence.mkdir();entry=root/'product/lib/bin.js'
        entry.parent.mkdir(parents=True);entry.write_text('',encoding='utf8')
        (entry.parent.parent/'package.json').write_text(json.dumps({'version':'test'}),encoding='utf8')
        agent=dsh.DshAgent('node',entry)
        process=MagicMock();process.stdout=io.StringIO('dsh web: '+URL+'\n');process.poll.return_value=None
        browser=MagicMock();browser.prepare.return_value='owned';browser.capture_title.return_value='owned'
        browser.snapshot.return_value={'uiLanguage':'en'}
        lists=iter([{'items':[]},{'items':[{'sessionId':'owned','cwd':str(workspace),'blank':True,'running':False}]}])
        def rpc(method,args):
            if method=='session/list':return next(lists)
            if method=='session/projections':return {'values':{}}
            return {}
        agent.rpc=MagicMock(side_effect=rpc)
        agent.observe=MagicMock(return_value=[{'type':'sandbox/mode','data':{'mode':'workspace-write'}},
                                              {'type':'approval/policy','data':{'policy':'ask'}}])
        return agent,process,browser,workspace,evidence

    def test_transient_auth_connection_reset_does_not_abort_preparation(self):
        with tempfile.TemporaryDirectory() as folder:
            agent,process,browser,workspace,evidence=self.prepare_fixture(folder)
            response=MagicMock();agent.opener.open=MagicMock(side_effect=[ConnectionResetError(10054,'reset'),response])
            with patch.object(dsh.subprocess,'Popen',return_value=process),patch.object(dsh.time,'sleep'):
                result=agent.prepare(workspace,browser,evidence)
            self.assertEqual(result['sandboxMode'],'workspace-write')
            self.assertEqual(agent.opener.open.call_count,2)
            self.assertNotIn('syntheticTokenValue001',(evidence/'dsh.log').read_text('utf8'))

    def test_authentication_rejection_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            agent,process,browser,workspace,evidence=self.prepare_fixture(folder)
            agent.opener.open=MagicMock(side_effect=urllib.error.HTTPError(URL,401,'Unauthorized',{},None))
            with patch.object(dsh.subprocess,'Popen',return_value=process),patch.object(dsh.time,'sleep'), \
                 self.assertRaisesRegex(RuntimeError,'authentication failed'):
                agent.prepare(workspace,browser,evidence)
            self.assertEqual(agent.opener.open.call_count,1)
            browser.open.assert_not_called()

if __name__=='__main__':unittest.main()
