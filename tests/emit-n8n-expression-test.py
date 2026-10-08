"""Emit fixture JS for the installed n8n evaluator; never execute a workflow.

Usage from repository root:
python3 tests/emit-n8n-expression-test.py | docker exec -i homelab-n8n node
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
workflow = json.loads((root / 'n8n-workflows/nutritrace-diary-mcp.json').read_text())
expression = next(node for node in workflow['nodes'] if node['name'] == 'Update')['parameters']['jsonBody']
print("const assert=require('node:assert/strict');")
print("const {Expression}=require('/usr/local/lib/node_modules/n8n/node_modules/n8n-workflow');")
print("const resolver=new Expression('Asia/Singapore');")
print('const expression=' + json.dumps(expression) + ';')
print('''
const cases=[
 [{food_server_id:'716',quantity:'2',meal:'breakfast'},{food_server_id:716,quantity:2,meal:'breakfast'}],
 [{food_server_id:716,quantity:2},{food_server_id:716,quantity:2}],
 [{food_server_id:716,meal:0},{food_server_id:716,meal:0}],
 [{food_server_id:716,quantity:0,meal:'snacks'},{food_server_id:716,quantity:0,meal:'snacks'}],
 [{food_server_id:716,quantity:null,meal:null},{food_server_id:716}],
];
for(const [input,expected] of cases){
 const rendered=resolver.resolveSimpleParameterValue(expression,{$json:{body:input}});
 assert.deepEqual(JSON.parse(rendered),expected);
 assert.equal(rendered.includes('={{'),false);
 console.log('PASS evaluated Update body:',rendered);
}
''')
