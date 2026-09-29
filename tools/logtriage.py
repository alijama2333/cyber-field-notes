fail_count = 0
with open("mission001.log") as f:
    for line in f:
        if "Failed password" in line:
            fail_count += 1
print("Total failed logins:", fail_count)
