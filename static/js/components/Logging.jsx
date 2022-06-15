import React from "react";
import { useSelector } from "react-redux";

import makeStyles from "@mui/styles/makeStyles";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";

import dayjs from "dayjs";

const useStyles = makeStyles((theme) => ({
  root: {
    padding: "1rem 2rem 2rem 2rem",
    fontSize: "1rem",
    "& .MuiTypography-h5": {
      margin: "1rem 0 0.83rem 0",
      fontWeight: 600,
      wordBreak: "break-all",
    },
    "& .MuiTypography-body1": {
      margin: "1rem 0",
    },
  },
  hidden: {
    display: "none",
  },
  logPaper: {
    maxHeight: "30rem",
    overflow: "auto",
  },
  logList: {
    fontFamily: "monospace",
  },
  logSHA: {
    color: `${theme.palette.error.main} !important`,
  },
  logPR: {
    color: theme.palette.secondary.dark,
  },
}));

const Logging = () => {
  const classes = useStyles();
  const log = useSelector((state) => state.sysInfo.log);
  return (
    <Paper className={classes.root}>
      {log && (
        <>
          <Typography variant="h5">Recent Log Activity</Typography>
          <Paper mt={1} className={classes.gitlogPaper}>
            <Box p={1}>
              <ul className={classes.logList}>
                {log.map(
                  ({
                    name,
                    time,
                    sha,
                    description,
                    pr_nr,
                    pr_url,
                    commit_url,
                  }) => (
                    <li key={sha}>
                      {name && (
                        <span className={classes.gitlogName}>[{name}]</span>
                      )}
                      [{dayjs(time).format("YYYY-MM-DD")}
                      <a className={classes.gitlogSHA} href={commit_url}>
                        &nbsp;{sha}
                      </a>
                      ] {description}
                      {pr_nr && (
                        <a href={pr_url}>
                          &nbsp;(
                          <span className={classes.gitlogPR}>#{pr_nr}</span>)
                        </a>
                      )}
                    </li>
                  )
                )}
              </ul>
            </Box>
          </Paper>
        </>
      )}
    </Paper>
  );
};

export default Logging;
