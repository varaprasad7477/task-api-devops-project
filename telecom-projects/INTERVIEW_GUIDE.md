# Explain the projects clearly

These are newly prepared learning projects. Run them, inspect the code, and make a small change yourself before claiming proficiency. Do not claim production network experience or a measured improvement to a real operator network.

## 30-second introduction

"I am a Computer Science undergraduate at GITAM. I am interested in networking and data analysis. To practise skills relevant to this role, I worked through two Python projects: one checks DNS and TCP connectivity and stores results in SQL; the other calculates telecom performance indicators from simulated data and generates reports. I can demonstrate the calculations, warning rules, and tests. I am looking to build on this foundation in a telecom engineering role."

Use this only after you can demonstrate both projects yourself.

## Project 1: explain in 45 seconds

"My connectivity monitor checks a selected host and TCP port. It first resolves the name using DNS, then tries a TCP connection. It records the result and timing in SQLite. A report separates DNS failures, connection failures, slow connections, and successful checks. I tested it with a local server, including stopping the server to demonstrate a failed connection."

Use the last sentence only after running the local-server exercise yourself.

### Questions you should answer

- **What is DNS?** A service that maps names to addresses. My program asks the operating system to resolve the name.
- **What is TCP?** A transport protocol providing a reliable, ordered byte stream. This project measures whether a TCP connection can be established; it does not send or analyze application traffic.
- **Which OSI layers relate to it?** TCP is transport, IP is network, and DNS is usually discussed at application level. The tool uses socket APIs rather than implementing the layers.
- **Why not call this packet loss?** I count connection outcomes, not transmitted and received ICMP or data packets.
- **Is a failed connection proof of an outage?** No. The service may be closed or blocked while the host remains reachable in other ways.
- **Why SQLite?** It is included with Python, runs locally without a server, and lets me practise SQL queries over observations.
- **How do you test it?** Start a loopback TCP server for success, use a bound but non-listening port for failure, and simulate DNS failure. Unit tests also check reporting and SQL inserts.
- **Does a two-second timeout limit everything?** No. It bounds the TCP attempt budget; OS DNS resolution can take longer.

## Project 2: explain in 45 seconds

"My KPI analyzer reads simulated cell data from a CSV file. It checks that the values are valid, uses SQL to group measurements by cell, and calculates call drop rate, latency, and throughput. It flags values outside configurable thresholds and exports a report. One sample cell has four warnings, while another has no established calls, so its call drop rate is shown as unknown."

### Questions you should answer

- **What is a KPI?** A key performance indicator: a measurement used to track performance, such as call drop rate.
- **Call drop formula?** Dropped calls divided by successfully established calls, multiplied by 100. In this project's data, the counters cover separate intervals, so I sum counts first.
- **What is latency?** Delay. The analyzer averages the sample interval latency values in milliseconds. The monitor separately measures TCP connection setup time.
- **What is throughput?** The observed rate of data transfer. Decimal MB multiplied by eight and divided by seconds gives Mbps.
- **Why is CELL_B flagged?** 17 dropped calls out of 270 established calls gives about 6.30%; latency averages 85 ms; throughput is about 4.67 Mbps; peak utilization is 96%. These exceed the chosen demonstration rules.
- **Why show N/A instead of 0%?** With no established calls, the denominator is zero, so a drop rate cannot be calculated.
- **Did you optimize a real 5G network?** No. This is analysis of simulated data. I would need actual counters, permission, and guidance before doing live optimization.
- **Can a warning find the root cause?** No. It identifies a symptom. I would inspect time patterns, alarms, traffic load, and available RF/core/transmission information to narrow down the cause.
- **What SQL do you use?** SELECT, SUM, AVG, MAX, GROUP BY, and NULLIF. NULLIF prevents division by zero.
- **What if one bad interval has more calls than another?** I aggregate call counts before dividing; averaging percentages can give a misleading result.

## One-week preparation plan

| Day | Practice | What you should be able to show |
| --- | --- | --- |
| 1 | Run both offline demonstrations; inspect each output | Explain inputs and outputs |
| 2 | Read monitor.py; run the local TCP server and stop it | Show successful and failed live checks |
| 3 | Revise OSI, TCP/IP, DNS, ports, and sockets | Explain the network path in your own words |
| 4 | Calculate CELL_B manually; run the SQL examples | Explain each KPI and its units |
| 5 | Add one sample cell and change one threshold | Show your own small modification |
| 6 | Run tests; read validation failures | Explain two useful tests and one limitation |
| 7 | Practise a five-minute demonstration and common questions | Explain both projects without reading notes |

## Resume wording after practising

**Technical Skills**

- Programming: Python, SQL
- Networking: OSI Model, TCP/IP, DNS
- Database & Tools: SQLite, GitHub
- Analysis & Testing: Data Analysis, Reporting, Software Testing

An honest answer to "How did you gain these skills as a fresher?" is: "Through my coursework and these personal projects. I can demonstrate the functions and calculations I have practised, and I am still learning the telecom-specific tools."
