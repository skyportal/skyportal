import glob
import numpy as np
from astropy.time import Time
import re

from ..base import BaseHandler

health_log = "log/health_monitor.log"
applog_files = "log/app*.log"
max_log_lines = 100


def health_logread(line):
    lineSplit = re.findall(r'\[([^]]*)\]', line)
    if len(lineSplit) == 0:
        return None
    lineSplit2 = lineSplit[0].split('[')
    if len(lineSplit2) < 2:
        return None
    lineSplit3 = lineSplit2[1].split(" ")
    if len(lineSplit3) < 2:
        return None
    tt, logname = lineSplit3[0], lineSplit3[1]
    lineSplit = re.findall(r'\]([^]]*)\[', line)
    if len(lineSplit) == 0:
        return None
    logissue = lineSplit[0]

    return (
        Time(f'{Time.now().iso.split(" ")[0]} {tt}', format='iso').jd,
        logname,
        logissue,
    )


def app_logread(line):
    lineSplit = re.findall(r'\[([^]]*)\]', line)
    if len(lineSplit) == 0:
        return None
    print(lineSplit[0])
    lineSplit2 = lineSplit[0].replace('"', '').replace('', "").split(',')
    print(lineSplit2)
    if len(lineSplit2) < 2:
        return None
    lineSplit3 = lineSplit2[1].split(" ")
    if len(lineSplit3) < 2:
        return None
    tt, logname = lineSplit3[0], lineSplit3[1]
    lineSplit = re.findall(r'\]([^]]*)\[', line)
    if len(lineSplit) == 0:
        return None
    logissue = lineSplit[0]

    print(tt, logname, logissue)

    return (
        Time(f'{Time.now().iso.split(" ")[0]} {tt}', format='iso').jd,
        logname,
        logissue,
    )


class LogInfoHandler(BaseHandler):
    def get(self):
        """
        ---
        description: Retrieve logging info
        tags:
          - logging_info
        responses:
          200:
            content:
              application/json:
                schema:
                  allOf:
                    - $ref: '#/components/schemas/Success'
                    - type: object
                      properties:
                        data:
                          type: object
                          properties:
                            gitlog:
                                type: array
                                description: Recent log file lines

        """

        with open(health_log) as f:
            lines = f.readlines()[-100:]
            parsed_log = {}
            for line in lines:
                output = health_logread(line)
                if output is None:
                    continue
                tt, logname, logissue = output
                print(tt, logname, logissue)

                tts, lognames, logs = [], [], []
                for logfile in glob.glob(applog_files):
                    with open(logfile) as g:
                        lines = g.readlines()
                        for line in lines:
                            output = app_logread(line)
                            if output is None:
                                continue
                            tt2, logname2, logissue2 = output
                            tts.append(tt2)
                            lognames.append(logname2)
                            logs.append(logissue2)

                idx = np.argmin(np.abs(np.array(tts) - tt))
                print(tt, logname, logissue)
                print(tts[idx], lognames[idx], logs[idx])

        return self.success(
            data={
                "log": parsed_log,
            }
        )
