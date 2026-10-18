# Validation record

Prepared on 18 October 2026 using Python 3.13 on Windows.

- 18 tests discovered: **16 passed; 2 skipped** because this managed environment denies outgoing loopback TCP connections (Windows error 10013).
- The skipped tests exercise a real local listening server and a real non-listening local port. They remain in the test suite for running on a normal local machine.
- A mocked successful TCP test exercised name-resolution output, socket connection handling, timing, and status assignment. It does not replace a successful live integration test.
- Both offline CLI demonstrations completed and produced CSV, JSON, SQLite, and HTML files.
- Monitor demo: 5 checks, 3 reachable, 60% check reachability, 2 failed checks, 61.67 ms mean successful connection time. All measurements are simulated.
- KPI demo: 8 measurements, 4 cells, CELL_B triggered all four thresholds; CELL_D had an unknown call drop rate because established calls were zero.
- SQL result checks, weighted call-count aggregation, duplicate/invalid inputs, zero denominator handling, threshold boundaries, and HTML escaping passed.

Before the interview, run both projects on your laptop and complete the local-server exercise in the monitor README. Do not describe the sample output as a real mobile network result.
