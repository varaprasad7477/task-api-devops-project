import importlib.util
from contextlib import closing
import json
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
monitor = load('monitor', ROOT / 'network-connectivity-monitor/monitor.py')
kpi = load('analyzer', ROOT / 'telecom-kpi-analyzer/analyzer.py')
THRESHOLDS = dict(drop=2, latency=50, throughput=10, utilization=85)


class MonitorTests(unittest.TestCase):
    def test_local_tcp_server_accepts_real_connection(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen()
            server.settimeout(3)
            # Some managed environments deny all outgoing sockets, even loopback.
            with socket.socket() as probe:
                probe.settimeout(.5)
                code = probe.connect_ex(server.getsockname())
            if code in {10013, 13, 1}:
                self.skipTest('Environment denies loopback TCP connections')
            if code == 0:
                connection, _ = server.accept()
                connection.close()
            def accept():
                connection, _ = server.accept()
                connection.close()
            thread = threading.Thread(target=accept, daemon=True)
            thread.start()
            result = monitor.check_target('127.0.0.1', server.getsockname()[1], slow_ms=10000)
            thread.join(3)
            self.assertEqual(result['status'], 'UP')
            self.assertGreaterEqual(result['connect_ms'], 0)

    def test_closed_local_port(self):
        # Bound but not listening: no race with another process claiming the port.
        with socket.socket() as closed:
            closed.bind(('127.0.0.1', 0))
            row = monitor.check_target('127.0.0.1', closed.getsockname()[1], timeout=.2)
        self.assertEqual(row['status'], 'TCP_ERROR')
        self.assertIsNone(row['connect_ms'])
        if '10013' in row['detail'] or 'Permission denied' in row['detail']:
            self.skipTest('Environment denies loopback TCP connections')

    def test_successful_tcp_path_with_mocked_socket(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        addresses = [(socket.AF_INET,socket.SOCK_STREAM,6,'',('192.0.2.1',443))]
        with patch.object(monitor.socket,'getaddrinfo',return_value=addresses), \
             patch.object(monitor.socket,'socket',return_value=connection):
            row = monitor.check_target('demo.example',443,slow_ms=10000)
        self.assertEqual(row['status'],'UP')
        self.assertEqual(row['address'],'192.0.2.1')
        connection.connect.assert_called_once_with(('192.0.2.1',443))

    def test_dns_failure(self):
        with patch.object(monitor.socket, 'getaddrinfo', side_effect=socket.gaierror('demo error')):
            row = monitor.check_target('invalid.example', 443)
        self.assertEqual(row['status'], 'DNS_ERROR')

    def test_threshold_boundary_and_slow_reachable(self):
        self.assertEqual(monitor.classify(True, True, 100, 100), 'UP')
        self.assertEqual(monitor.classify(True, True, 101, 100), 'SLOW')
        summary = monitor.summarize([{'status':'SLOW','connect_ms':101}])
        self.assertEqual(summary['reachability_pct'], 100)

    def test_missing_success_timing_rejected(self):
        row = json.loads((ROOT/'network-connectivity-monitor/sample_checks.json').read_text())[0]
        row['connect_ms'] = None
        with self.assertRaises(ValueError):
            monitor.validate([row])

    def test_empty_summary(self):
        self.assertIsNone(monitor.summarize([])['reachability_pct'])

    def test_demo_outputs_sql_and_escaping(self):
        rows = json.loads((ROOT/'network-connectivity-monitor/sample_checks.json').read_text())
        rows[0]['host'] = '<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as temp:
            summary = monitor.write_outputs(rows, temp, 'simulated', 100)
            self.assertEqual(summary['reachability_pct'], 60)
            with closing(sqlite3.connect(Path(temp)/'history.sqlite')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM checks').fetchone()[0],5)
                self.assertEqual(db.execute('SELECT DISTINCT mode FROM checks').fetchone()[0],'simulated')
            page = (Path(temp)/'report.html').read_text()
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('<script>', page)


class KpiTests(unittest.TestCase):
    def setUp(self):
        self.rows = kpi.load_rows(ROOT/'telecom-kpi-analyzer/sample_kpis.csv')

    def test_expected_demo_alarm_cell(self):
        results = {r['cell_id']:r for r in kpi.calculate(self.rows)}
        self.assertEqual(len(kpi.alarms(results['CELL_B'], THRESHOLDS)),4)
        self.assertEqual(kpi.alarms(results['CELL_A'], THRESHOLDS),[])
        self.assertEqual(kpi.alarms(results['CELL_C'], THRESHOLDS),[])
        self.assertAlmostEqual(results['CELL_B']['call_drop_pct'],100*17/270)
        self.assertAlmostEqual(results['CELL_B']['throughput_mbps'],8*70/120)

    def test_aggregate_counts_before_ratios(self):
        first, second = self.rows[0].copy(), self.rows[1].copy()
        first.update(call_attempts=10, established_calls=10, dropped_calls=5)
        second.update(call_attempts=1000, established_calls=1000, dropped_calls=0)
        row = kpi.calculate([first,second])[0]
        self.assertAlmostEqual(row['call_drop_pct'],500/1010)
        self.assertNotEqual(row['call_drop_pct'],25)

    def test_zero_denominator_is_unknown(self):
        row = next(r for r in kpi.calculate(self.rows) if r['cell_id']=='CELL_D')
        self.assertIsNone(row['call_drop_pct'])
        self.assertIsNone(row['setup_success_pct'])

    def invalid_csv(self, transform):
        text = (ROOT/'telecom-kpi-analyzer/sample_kpis.csv').read_text()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'invalid.csv'
            path.write_text(transform(text))
            with self.assertRaises(ValueError):
                kpi.load_rows(path)

    def test_inconsistent_counters_rejected(self):
        self.invalid_csv(lambda s:s.replace(',100,98,1,',',100,98,99,',1))

    def test_duplicate_interval_rejected(self):
        self.invalid_csv(lambda s:s+'\n'+s.splitlines()[1])

    def test_nan_rejected(self):
        self.invalid_csv(lambda s:s.replace(',25,150,',',nan,150,',1))

    def test_zero_transfer_duration_rejected(self):
        self.invalid_csv(lambda s:s.replace(',150,60,',',150,0,',1))

    def test_empty_input_rejected(self):
        self.invalid_csv(lambda s:s.splitlines()[0]+'\n')

    def test_report_and_sql_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            result = kpi.analyze(ROOT/'telecom-kpi-analyzer/sample_kpis.csv',temp,THRESHOLDS)
            self.assertEqual(len(result),4)
            page = (Path(temp)/'report.html').read_text()
            self.assertIn('SIMULATED EDUCATIONAL DATA',page)
            self.assertIn('No established calls',page)
            with closing(sqlite3.connect(Path(temp)/'measurements.sqlite')) as db:
                self.assertEqual(db.execute('SELECT SUM(dropped_calls) FROM samples WHERE cell_id=?',('CELL_B',)).fetchone()[0],17)

    def test_exact_threshold_is_not_alarm(self):
        row = dict(call_drop_pct=2,avg_latency_ms=50,throughput_mbps=10,peak_utilization_pct=85)
        self.assertEqual(kpi.alarms(row,THRESHOLDS),[])


if __name__ == '__main__':
    unittest.main()
