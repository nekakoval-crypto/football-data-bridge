import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import stage72_build_data_layer as stage72
import stage73_internal_api as api


ROUND_FIELDS = [
    'fixture_id','provider_league_id','league_name','country','country_flag_url','league_logo_url',
    'season','round','kickoff_utc','home_team','home_team_logo_url','away_team','away_team_logo_url',
    'status','source_status','score_home','score_away','observed_at_utc','live_observed_at_utc',
    'live_freshness_status','elapsed','red_cards_home','red_cards_away'
]


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def fixture(status='scheduled', source='NS', score_home='', score_away='', observed='2026-09-14T15:00:00Z'):
    return {
        'fixture_id':'999','provider_league_id':'39','league_name':'Premier League','country':'England',
        'country_flag_url':'https://img/eng.png','league_logo_url':'https://img/epl.png','season':'2026','round':'Round 5',
        'kickoff_utc':'2026-09-14T16:30:00Z','home_team':'Alpha','home_team_logo_url':'https://img/a.png',
        'away_team':'Beta','away_team_logo_url':'https://img/b.png','status':status,'source_status':source,
        'score_home':score_home,'score_away':score_away,'observed_at_utc':observed,
        'live_observed_at_utc':'','live_freshness_status':'unknown','elapsed':'','red_cards_home':'0','red_cards_away':'0',
    }


class MatchCardE2ETests(unittest.TestCase):
    def build(self, base_row, overlay_rows=None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        ops = root / 'ops'
        out = root / 'pbk.sqlite'
        ops.mkdir(parents=True)
        write_csv(ops/'current_round_leagues.csv', stage72.CURRENT_ROUND_LEAGUE_FIELDS, [{
            'provider_league_id':'39','league_name':'Premier League','country':'England',
            'country_flag_url':'https://img/eng.png','league_logo_url':'https://img/epl.png',
            'season':'2026','round':'Round 5','observed_at_utc':'2026-09-14T15:00:00Z','status':'available','error':''
        }])
        write_csv(ops/'current_round_fixtures.csv', ROUND_FIELDS, [base_row])
        write_csv(ops/'live_fixture_overlay.csv', ROUND_FIELDS, overlay_rows or [])
        write_csv(ops/'stage61_market_snapshots.csv', [
            'api_fixture_id','captured_at_utc','b365_home','b365_draw','b365_away','p_home','p_draw','p_away',
            'user_bookmaker','user_home','user_draw','user_away'
        ], [
            {'api_fixture_id':'999','captured_at_utc':'2026-09-14T15:30:00Z','b365_home':'2.10','b365_draw':'3.40','b365_away':'3.60',
             'p_home':'0.45','p_draw':'0.28','p_away':'0.27','user_bookmaker':'Marathonbet','user_home':'2.12','user_draw':'3.45','user_away':'3.65'},
            {'api_fixture_id':'999','captured_at_utc':'2026-09-14T17:00:00Z','b365_home':'1.01','b365_draw':'50','b365_away':'90',
             'p_home':'0.97','p_draw':'0.02','p_away':'0.01','user_bookmaker':'Marathonbet','user_home':'1.01','user_draw':'50','user_away':'90'},
        ])
        # Stage72 status can legitimately be WARN in this minimal fixture because most optional/stable sources are absent.
        with patch.object(stage72, 'OPS', ops), patch.object(stage72, 'OUT', out), \
             patch.object(stage72, 'META', ops/'stage72_last_run.json'), \
             patch.object(stage72, 'SCHEMA', ops/'stage72_schema.json'):
            stage72.main()
        self.assertTrue(out.exists())
        with patch.object(api, 'DB', out):
            status, payload = api.dispatch('/v1/match-card?fixture_id=999')
        return temp, out, status, payload

    def test_stage72_to_stage73_live_card_uses_overlay_but_keeps_prematch_market(self):
        base = fixture()
        overlay = fixture('live','2H','1','0','2026-09-14T17:10:00Z')
        overlay.update({
            'live_observed_at_utc':'2026-09-14T17:10:00Z','live_freshness_status':'fresh',
            'elapsed':'65','red_cards_home':'1','red_cards_away':'0'
        })
        temp, out, status, payload = self.build(base, [overlay])
        try:
            self.assertEqual(status, 200)
            self.assertEqual(payload['fixture']['status'], 'live')
            self.assertEqual(payload['fixture']['score'], {'home': 1, 'away': 0})
            self.assertEqual(payload['fixture']['elapsed'], 65)
            self.assertEqual(payload['fixture']['home']['red_cards'], 1)
            family = next(x for x in payload['markets']['families'] if x['id']=='MATCH_RESULT_1X2')
            self.assertEqual(family['observed_at_utc'], '2026-09-14T15:30:00Z')
            self.assertEqual(family['items'][0]['bet365_odds'], '2.10')
            self.assertNotEqual(family['items'][0]['bet365_odds'], '1.01')
            self.assertTrue(payload['read_only'])
            self.assertFalse(payload['provider_polling'])
            self.assertFalse(payload['model_mutation'])
        finally:
            temp.cleanup()

    def test_stage72_terminal_protection_survives_full_api_path(self):
        base = fixture('finished','FT','2','1','2026-09-14T18:25:00Z')
        base.update({'live_observed_at_utc':'2026-09-14T18:25:00Z','elapsed':'90','red_cards_home':'1'})
        stale_live = fixture('live','2H','1','1','2026-09-14T18:30:00Z')
        stale_live.update({'live_observed_at_utc':'2026-09-14T18:30:00Z','elapsed':'80','red_cards_home':'0'})
        temp, out, status, payload = self.build(base, [stale_live])
        try:
            self.assertEqual(status, 200)
            self.assertEqual(payload['fixture']['status'], 'finished')
            self.assertEqual(payload['fixture']['source_status'], 'FT')
            self.assertEqual(payload['fixture']['score'], {'home': 2, 'away': 1})
            self.assertEqual(payload['fixture']['home']['red_cards'], 1)
        finally:
            temp.cleanup()


if __name__ == '__main__':
    unittest.main()
