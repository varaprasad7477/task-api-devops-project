# Telecom Network Analyst Projects

Two small, explainable fresher projects for network monitoring and performance analysis.
**Technology: Python 3.10+ and SQLite (included in Python). No pip installation, cloud service, or paid tool is required.**

| Project | What it demonstrates | Data |
| --- | --- | --- |
| [Network Connectivity Monitor](network-connectivity-monitor/) | DNS lookup, TCP connection timing, failure flags, SQL history | Offline simulated demo or an explicitly chosen live host |
| [Telecom KPI Analyzer](telecom-kpi-analyzer/) | Call drop rate, latency, throughput, threshold alarms, SQL aggregation | Simulated 4G/5G measurements |

These are educational personal projects, not evidence of employment, NOC operations, RF optimization, or production telecom access. Learn the code and run the demonstrations before presenting them as your work. AI assistance was used to prepare this initial implementation and documentation.

## Quick start on Windows PowerShell

Download this branch using GitHub's **Code > Download ZIP**, extract it, and open PowerShell in the `telecom-projects` folder. If `python` does not work, try `py` instead.

```powershell
python network-connectivity-monitor/monitor.py --demo --out network-connectivity-monitor/output
python telecom-kpi-analyzer/analyzer.py --out telecom-kpi-analyzer/output
Start-Process network-connectivity-monitor/output/report.html
Start-Process telecom-kpi-analyzer/output/report.html
python -m unittest discover -s tests -v
```

Run from any location by supplying absolute script/output paths. Both scripts print the location of the report.

## Five-minute interview demonstration

1. Run the monitor in demo mode. Show UP, SLOW, TCP_ERROR, and DNS_ERROR. Explain why the three reachable samples out of five mean 60% **check reachability**, not monthly uptime or packet loss.
2. Run the KPI analyzer. Show CELL_B's four alarms, healthy comparison cells, and CELL_D's unknown call drop rate when no calls were established.
3. Change a threshold and rerun. Explain the difference between changing a warning rule and fixing an underlying network problem.
4. Show the SQL `GROUP BY` query and one unit test. Explain how counts are added before calculating call drop percentage.

Read [INTERVIEW_GUIDE.md](INTERVIEW_GUIDE.md) for explanations, questions, limitations, and a one-week practice plan.

## Contents

- `network-connectivity-monitor/monitor.py` - live checks, simulation, SQL history, CSV/JSON/HTML reports
- `telecom-kpi-analyzer/analyzer.py` - input validation, SQL calculations, alarms, reports
- `*/sample_*` - small, manually inspectable simulated datasets
- `*/examples/` - generated reports from the bundled samples (not live results)
- `tests/test_projects.py` - real loopback TCP tests and calculation/validation tests

## Scope

The monitor does not measure radio coverage, mobile call drops, packet loss, or bandwidth. TCP connection time is not ICMP round-trip time or application response time. DNS resolution uses the OS resolver; the TCP timeout does not limit OS DNS lookup time.

The analyzer does not connect to a telecom operator. Its thresholds are illustrative and its data is synthetic. It flags possible performance symptoms; deciding root cause needs further evidence. Nothing here changes device configurations or upgrades networks.

## Reference documentation

- [Python socket module](https://docs.python.org/3/library/socket.html)
- [Python SQLite module](https://docs.python.org/3/library/sqlite3.html)
- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [TRAI training material: call drop rate and established calls](https://www.trai.gov.in/sites/default/files/2025-02/IDT_Mysuru_11022025.pdf)

The simplified data schema is for learning and does not claim compliance with an operator's complete KPI definition.
