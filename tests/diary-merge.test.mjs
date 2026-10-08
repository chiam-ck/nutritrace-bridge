import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeEntries } from '../overlays/nutritrace/server/lib/diary-merge.js';

const base = {uuid:'pb-1',food_server_id:716,quantity:1,meal:0,
  addedAt:'2026-10-09T04:51:31.516723'};
const merge = (server, client, deleted=[], tombstones=[]) =>
  mergeEntries(server, client, deleted, tombstones);

test('legacy SGT around midnight accepts later UTC portion edit',()=> {
  const edited={...base,quantity:2,updatedAt:'2026-10-08T20:56:18.000Z'};
  assert.equal(merge([base],[edited]).merged[0].quantity,2);
});
test('naive SGT semantics do not depend on host timezone',()=> {
  const original=process.env.TZ;
  try {
    for(const zone of ['UTC','Asia/Singapore','America/Los_Angeles']) {
      process.env.TZ=zone;
      const edit={...base,quantity:2,updatedAt:'2026-10-08T20:56:18.000Z'};
      assert.equal(merge([base],[edit]).merged[0].quantity,2);
    }
  } finally { if(original===undefined)delete process.env.TZ;else process.env.TZ=original; }
});
test('aware offsets compare instants instead of date strings',()=> {
  const server={...base,updatedAt:'2026-10-09T05:00:00.000+08:00'};
  const newer={...base,quantity:2,updatedAt:'2026-10-08T21:00:01.000Z'};
  const stale={...base,quantity:3,updatedAt:'2026-10-08T20:59:59.000Z'};
  assert.equal(merge([server],[newer]).merged[0].quantity,2);
  assert.equal(merge([server],[stale]).merged[0].quantity,1);
});
test('microsecond bridge timestamps equal JS milliseconds and retain incoming-wins tie',()=> {
  const tie={...base,quantity:2,updatedAt:'2026-10-08T20:51:31.516Z'};
  assert.equal(merge([base],[tie]).merged[0].quantity,2);
});
test('explicit UTC and canonical UTC retain latest edit',()=> {
  const server={...base,addedAt:'2026-10-08T20:51:31.516+00:00'};
  const client={...server,quantity:2,updatedAt:'2026-10-08T21:00:00.000Z'};
  assert.equal(merge([server],[client]).merged[0].quantity,2);
});
test('negative offset and midnight represent the same instant; water follows same rules',()=> {
  const water={uuid:'water-1',amount:250,addedAt:'2026-10-09T00:00:00+08:00'};
  const later={...water,amount:500,updatedAt:'2026-10-08T09:00:01-07:00'};
  const stale={...water,amount:750,updatedAt:'2026-10-08T15:59:59Z'};
  assert.equal(merge([water],[later]).merged[0].amount,500);
  assert.equal(merge([water],[stale]).merged[0].amount,250);
});
test('missing/invalid legacy timestamps rank below valid timestamps',()=> {
  for(const addedAt of [undefined,'garbage','2026-10-09']) {
    const server={...base,addedAt};
    const client={...server,quantity:2,updatedAt:'2026-10-08T21:00:00.000Z'};
    assert.equal(merge([server],[client]).merged[0].quantity,2);
    assert.equal(merge([client],[server]).merged[0].quantity,2);
  }
});
test('two identical foods remain independent; concurrent server-only entries survive',()=> {
  const second={...base,uuid:'pb-2'};
  const other={...base,uuid:'other',food_server_id:512};
  const edited={...base,quantity:2,updatedAt:'2026-10-08T21:00:00Z'};
  const result=merge([base,second,other],[edited,second]).merged;
  assert.deepEqual(result.map(x=>[x.uuid,x.quantity]),[['pb-1',2],['pb-2',1],['other',1]]);
});
test('new and prior tombstones beat future edits and are persisted only once',()=> {
  const future={...base,quantity:2,updatedAt:'2027-01-01T00:00:00Z'};
  assert.deepEqual(merge([base],[future],['pb-1']).merged,[]);
  assert.deepEqual(merge([base],[future],[],['pb-1']).merged,[]);
  assert.deepEqual(merge([base],[future],['pb-1'],['pb-1']).newTombstoneUuids,[]);
});
test('duplicate UUID payload collapses to latest entry',()=> {
  const newer={...base,quantity:2,updatedAt:'2026-10-08T21:00:00Z'};
  assert.deepEqual(merge([base],[newer,base]).merged,[newer]);
});
