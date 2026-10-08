import ast, importlib.util, io, json, os, sqlite3, sys, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bridge', ROOT/'nutritrace-api.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        bridge.DB_PATH = str(Path(self.tmp.name)/'fixture.db')
        self.db = sqlite3.connect(bridge.DB_PATH)
        self.db.execute('CREATE TABLE diary(id INTEGER PRIMARY KEY,user_id INTEGER,date TEXT,items TEXT,body_stats TEXT,water TEXT,notes TEXT,deleted_at TEXT,updated_at TEXT)')
        self.db.execute('CREATE TABLE foods(id INTEGER PRIMARY KEY,user_id INTEGER,name TEXT,brand TEXT,nutrition TEXT,portion REAL,unit TEXT,notes TEXT,barcode TEXT,category TEXT,favorite INTEGER,deleted_at TEXT)')
        self.db.execute("INSERT INTO foods VALUES(716,1,'Fixture PB','',?,16,'g','','','',0,NULL)", (json.dumps({'calories':95}),))
        self.db.execute('ALTER TABLE foods ADD COLUMN usage_count INTEGER DEFAULT 0')
        self.db.execute('ALTER TABLE foods ADD COLUMN last_used_at TEXT')
        self.items=[{'uuid':'pb-1','food_server_id':716,'name':'Fixture PB','meal':0,'quantity':1,'addedAt':'2026-10-09T04:51:31.516723'},
                    {'uuid':'pb-2','food_server_id':716,'name':'Fixture PB','meal':0,'quantity':1,'addedAt':'2026-10-09T04:59:06.403007'}]
        self.db.execute('INSERT INTO diary VALUES(1,1,?,?,?,?,?,NULL,?)',('2026-10-09',json.dumps(self.items),'{}','[]','','fixture'))
        self.db.commit()
        self.original_clock=bridge._utc_timestamp
        bridge._utc_timestamp=lambda:'2026-10-08T21:10:00.000Z'

    def tearDown(self):
        bridge._utc_timestamp=self.original_clock
        self.db.close()
        self.tmp.cleanup()

    def request(self,method,payload,path='/diary/2026-10-09'):
        raw=json.dumps(payload).encode()
        handler=object.__new__(bridge.APIHandler)
        handler.path=path
        handler.headers={'Content-Length':str(len(raw))}
        handler.rfile=io.BytesIO(raw);handler.wfile=io.BytesIO()
        statuses=[];handler.send_response=statuses.append
        handler.send_header=lambda *args:None;handler.end_headers=lambda:None
        getattr(handler,'do_'+method)()
        return statuses[0],json.loads(handler.wfile.getvalue())

    def stored(self):
        return json.loads(self.db.execute('SELECT items FROM diary WHERE id=1').fetchone()[0])

    def test_patch_stamps_one_item_and_preserves_identical_food(self):
        status,body=self.request('PATCH',{'food_server_id':716,'quantity':2})
        self.assertEqual(status,200,body)
        first,second=self.stored()
        self.assertEqual(first['quantity'],2)
        self.assertEqual(first['updatedAt'],'2026-10-08T21:10:00.000Z')
        self.assertEqual(first['addedAt'],self.items[0]['addedAt'])
        self.assertEqual(second,self.items[1])

    def test_patch_meal_zero_is_valid(self):
        status,body=self.request('PATCH',{'food_server_id':716,'meal':0})
        self.assertEqual(status,200,body)
        self.assertEqual(self.stored()[0]['updatedAt'],'2026-10-08T21:10:00.000Z')

    def test_invalid_literal_does_not_mutate(self):
        status,body=self.request('PATCH',{'food_server_id':716,'quantity':2,'meal':'={{$json.body.meal}}'})
        self.assertEqual(status,400)
        self.assertEqual(body,{'error':"invalid meal: '={{$json.body.meal}}'"})
        self.assertEqual(self.stored(),self.items)
        self.assertEqual(self.db.execute('SELECT updated_at FROM diary').fetchone()[0],'fixture')

    def test_add_uses_utc_and_new_uuid_without_collapsing_old_foods(self):
        status,body=self.request('POST',{'food_id':716,'quantity':1,'meal':'breakfast','date':'2026-10-09'},'/diary/add')
        self.assertEqual(status,200,body)
        result=self.stored()
        self.assertEqual(result[:2],self.items)
        self.assertEqual(len(result),3)
        self.assertEqual(result[-1]['addedAt'],'2026-10-08T21:10:00.000Z')
        self.assertEqual(len({i['uuid'] for i in result}),3)

    def test_retry_guard_handles_legacy_aware_and_gui_timestamps(self):
        for stamp in ['2026-10-09T05:09:30.000000','2026-10-09T05:09:30+08:00','2026-10-08T21:09:30.000Z']:
            self.db.execute('UPDATE diary SET items=?',(json.dumps([{**self.items[0],'addedAt':stamp}]),))
            self.db.commit()
            status,body=self.request('POST',{'food_id':716,'quantity':1,'meal':'breakfast','date':'2026-10-09'},'/diary/add')
            self.assertEqual(status,200,body)
            self.assertTrue(body.get('deduplicated'),(stamp,body))
            self.assertEqual(len(self.stored()),1)

    def test_timestamp_helper_canonical_utc_and_legacy_midnight(self):
        stamp=self.original_clock()
        self.assertRegex(stamp,r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        expected=datetime(2026,10,8,20,51,31,516723,tzinfo=timezone.utc)
        self.assertEqual(bridge._item_datetime('2026-10-09T04:51:31.516723'),expected)
        self.assertEqual(bridge._item_datetime('2026-10-09T04:51:31.516723+08:00'),expected)
        self.assertEqual(bridge._item_datetime('2026-10-08T20:51:31.516723Z'),expected)

    def test_generator_matches_staged_update_expression(self):
        tree=ast.parse((ROOT/'scripts/create-nutritrace-n8n.py').read_text())
        create=next(n.value for n in tree.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                    and isinstance(n.value.func,ast.Name) and n.value.func.id=='create'
                    and isinstance(n.value.args[0],ast.Constant) and n.value.args[0].value=='NutriTrace Diary - MCP')
        update=next(n for n in create.args[3].elts if n.args[0].value=='Update')
        generated=next(k.value.value for k in update.keywords if k.arg=='body')
        workflow=json.loads((ROOT/'n8n-workflows/nutritrace-diary-mcp.json').read_text())
        exported=next(n for n in workflow['nodes'] if n['name']=='Update')['parameters']['jsonBody']
        self.assertEqual(generated,exported)
        self.assertTrue(exported.startswith('={{ JSON.stringify('))

if __name__=='__main__':unittest.main(verbosity=2)
