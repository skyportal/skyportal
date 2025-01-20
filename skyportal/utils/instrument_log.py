from astropy.time import Time


def read_logs(logs):
    """Read instrument logs string and return dictionary"""

    logs_dict = []
    for line in logs.split("\n"):
        lineSplit = line.strip().split(" ")
        if len(lineSplit) < 4:
            continue
        if ":" in lineSplit[1]:
            lineSplit[1] = lineSplit[1][:-1]
        try:
            tt = Time("T".join(lineSplit[:2]), format="isot")
        except Exception:
            continue
        log_type = lineSplit[2][1:-2]
        message = " ".join(lineSplit[3:])

        logs_dict.append({"mjd": tt.mjd, "type": log_type, "message": message})
    logs = {"logs": logs_dict}

    return logs
