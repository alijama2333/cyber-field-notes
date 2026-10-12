# Active Directory User Lifecycle Management


---

## 1. What Active Directory is

Active Directory (AD) is Microsoft's directory service. It stores users, groups and computers in one central place and decides who can log in and what they can access.

A domain comes to exist by installing the **AD DS (Active Directory Domain Services)** role on a Windows Server and **promoting** that server to a **Domain Controller (DC)**. Other computers then join the domain and authenticate against the DC.

## 2. Organizational Units (OUs)

- An OU is a container that holds **users, groups and computers** (not files).
- OUs can be **nested** (e.g. `Company > Finance > Finance-Laptops`).
- Group Policy Objects (GPOs) linked to a parent OU **cascade down** to child OUs, so OU design decides who gets which settings.

## 3. Groups: type vs scope

**Type decides what a group does. Scope decides how far it reaches.**

| Type | Purpose |
|---|---|
| Security | Assign permissions/access to resources; can also be used for email |
| Distribution | Email lists only; no permissions |

| Scope | Reach |
|---|---|
| Domain Local | Used to assign permissions to resources in its own domain |
| Global | Holds users from its own domain; the default and most common |
| Universal | Spans multiple domains in a forest |

Examples: **Finance** = Global Security group (access to finance files). **All Staff** = Distribution group (email only).

## 4. Joiner / Mover / Leaver (JML)

| Stage | What IT does |
|---|---|
| **Joiner** | Create account in the correct OU, add to the right groups, set temporary password with change-at-first-logon |
| **Mover** | Move account to the new OU, remove old group memberships, add new ones (avoids access creep) |
| **Leaver** | **Disable** the account, remove from groups, move to a Leavers OU, delete only after the retention period |

**Why disable before delete:** deleting is irreversible and can break ownership of files, mailboxes and scheduled tasks. Disabling blocks access immediately while keeping the option to recover or audit.

## 5. Password resets and account unlocks

**Reset a password:**
1. Open *Active Directory Users and Computers*.
2. Find the user, right-click, **Reset Password**.
3. Enter a temporary password.
4. Tick **"User must change password at next logon"**. Otherwise IT knows the user's real password, which is a security and audit problem.

**Unlock an account:** open the user's properties, go to the **Account** tab and tick **Unlock account**.

## 6. Verification before action

Before resetting a password or changing access, confirm the caller's identity:

- Ask identity questions that only the real user would answer, per the organisation's policy.
- If a third party (e.g. a manager or colleague) calls, get confirmation from the account owner or follow the approved process.
- Treat urgent, pressured requests as a possible **social engineering** attempt.
- Handle personal data carefully under **GDPR**: only access and share what is needed.

This draws on my previous customer-facing and call-centre experience, where verifying identity before acting was routine.

## 7. Group Policy

- Managed with the **Group Policy Management Console (GPMC)**.
- A GPO is **linked to an OU** (or domain/site) and applies to the users and computers inside it.
- Child OUs inherit parent GPOs; a lower-level GPO can override a higher-level one.
- Apply and check policies with:
  - `gpupdate /force` — refresh policy now
  - `gpresult /r` — show which policies applied to a user/computer

**Password policy settings:** minimum length, complexity, maximum age, password history.

**Account lockout settings:** lockout threshold (failed attempts), lockout duration, reset counter (time before the failed-attempt count resets).

**Fine-grained password policies** allow different password rules for specific groups (e.g. admins stricter than standard users) instead of one domain-wide rule.

*To add from my own notes: the name and purpose of the demo GPO shown in Episode 2.*

## 8. PowerShell for AD

| Task | Example |
|---|---|
| Create user | `New-ADUser -Name "Jane Doe" -SamAccountName jdoe -AccountPassword (ConvertTo-SecureString "Temp#Pass123" -AsPlainText -Force) -Enabled $true -ChangePasswordAtLogon $true -Path "OU=Finance,DC=lab,DC=local"` |
| View user | `Get-ADUser -Identity jdoe -Properties *` |
| Disable user | `Disable-ADAccount -Identity jdoe` |
| Move user | `Move-ADObject -Identity "CN=Jane Doe,OU=Finance,DC=lab,DC=local" -TargetPath "OU=Leavers,DC=lab,DC=local"` |
| Delete user | `Remove-ADUser -Identity jdoe` |

PowerShell matters because it turns repetitive JML work into repeatable scripts.

## 9. How this applies to support work

The most common service desk tickets this covers:
- Password reset and account unlock
- New starter set-up (Joiner)
- Access requests and group membership changes
- Leaver account disabling
- "Why can't I access this share?" (check group membership and policy)
