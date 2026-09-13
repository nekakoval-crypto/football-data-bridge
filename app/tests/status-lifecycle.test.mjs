import test from 'node:test';
import assert from 'node:assert/strict';
import {STATUS_GLOSSARY,statusLabel} from '../status-glossary.js';
import {oddsSummary,projectLifecycle} from '../lifecycle.js';

test('status glossary uses locked labels and priority',()=>{
  assert.equal(statusLabel({canonical:true}),'БРАТЬ ПО СИСТЕМЕ');
  assert.equal(statusLabel({watch:true}),'НАБЛЮДЕНИЕ');
  assert.equal(statusLabel({value_radar:true}),'РАСХОЖДЕНИЕ С РЫНКОМ');
  assert.equal(statusLabel({action_required:true,canonical:true}),'НУЖНО ДЕЙСТВИЕ');
  assert.equal(statusLabel({canonical:true,system_warning:true,value_radar:true,watch:true}),'БРАТЬ ПО СИСТЕМЕ');
  assert.equal(statusLabel({system_warning:true,blocking:true,value_radar:true,watch:true}),'СИСТЕМНОЕ ПРЕДУПРЕЖДЕНИЕ');
  assert.equal(statusLabel({value_radar:true,watch:true}),'РАСХОЖДЕНИЕ С РЫНКОМ');
  assert.equal(statusLabel({research:true,market_view:true}),'ИССЛЕДОВАНИЕ');
  assert.equal(statusLabel({market_view:true}),'РЫНОК');
  assert.equal(statusLabel({status:'ACTIVE'}),'ИНФОРМАЦИЯ');
  assert.deepEqual(Object.values(STATUS_GLOSSARY).filter(x=>x==='ACTIVE'),[]);
});

test('lifecycle default projection keeps meaningful events and compresses odds',()=>{
  const rows=[
    {event_type:'ODDS_SNAPSHOT',event_time_utc:'2026-01-01T10:00:00Z',odds:'2.4'},
    {event_type:'SIGNAL_CREATED',event_time_utc:'2026-01-01T09:00:00Z'},
    {event_type:'ODDS_SNAPSHOT',event_time_utc:'2026-01-01T10:01:00Z',odds:'1.8'},
    {event_type:'ODDS_SNAPSHOT',event_time_utc:'2026-01-01T10:02:00Z',odds:'bad'},
    {event_type:'ODDS_SNAPSHOT',event_time_utc:'2026-01-01T10:03:00Z',odds:'2.7'},
    {event_type:'USER_EXECUTION_FROZEN',event_time_utc:'2026-01-01T10:04:00Z'},
    {event_type:'CLOSE_LOCKED',event_time_utc:'2026-01-01T10:05:00Z'},
    {event_type:'FIXTURE_EVENT',event_time_utc:'2026-01-01T10:06:00Z',status:'POSTPONED'},
    {event_type:'SETTLEMENT',event_time_utc:'2026-01-01T10:07:00Z'},
    {event_type:'TECHNICAL_EVENT',event_time_utc:'2026-01-01T10:08:00Z'}
  ];
  const projected=projectLifecycle(rows);
  assert.deepEqual(projected.map(x=>x.event_type),['SIGNAL_CREATED','ODDS_SUMMARY','USER_EXECUTION_FROZEN','CLOSE_LOCKED','FIXTURE_EVENT','SETTLEMENT']);
  assert.equal(oddsSummary(rows).odds,'Коэффициент: первый 2.4 → min 1.8 → max 2.7 → последний 2.7 · 4 снимков');
  assert.equal(rows.length,10);
  assert.ok(rows.some(x=>x.event_type==='TECHNICAL_EVENT'));
});
