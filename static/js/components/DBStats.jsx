import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import Popover from "@material-ui/core/Popover";
import Box from "@material-ui/core/Box";
import { makeStyles } from "@material-ui/core/styles";

import * as dbStatsActions from "../ducks/dbStats";

const useStyles = makeStyles((theme) => ({
  popover: {
    pointerEvents: "none",
  },
  paper: {
    padding: theme.spacing(1),
  },
}));

const DBStats = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const dbStats = useSelector((state) => state.dbStats);
  const [popoverAnchorEl, setPopoverAnchorEl] = useState(null);

  const handlePopoverOpen = (event) => {
    setPopoverAnchorEl(event.currentTarget);
  };

  const handlePopoverClose = () => {
    setPopoverAnchorEl(null);
  };

  const popoverOpen = Boolean(popoverAnchorEl);

  useEffect(() => {
    if (dbStats === null) {
      dispatch(dbStatsActions.fetchDBStats());
    }
  }, [dbStats, dispatch]);

  if (dbStats === null) {
    return (
      <>
        <br />
        <CircularProgress />
      </>
    );
  }

  return (
    <>
      <br />
      <Typography variant="h5">DB Stats</Typography>
      <br />
      <Table>
        <TableBody>
          {Object.keys(dbStats).map((key) => (
            <TableRow key={key}>
              <TableCell>
                <em>{key}</em>
              </TableCell>
              <TableCell>
                {Array.isArray(dbStats[key]) && (
                  <ul style={{ paddingLeft: "0.8rem" }}>
                    {dbStats[key].map((item, idx) => (
                      <li key={item.summary}>
                        {item.summary}
                        {item.output && (
                          <>
                            <Typography
                              variant="caption"
                              aria-owns={
                                popoverOpen
                                  ? `mouse-over-popover${idx}`
                                  : undefined
                              }
                              aria-haspopup="true"
                              onMouseEnter={handlePopoverOpen}
                              onMouseLeave={handlePopoverClose}
                            >
                              <em> (mouse over to see output)</em>
                            </Typography>
                            <Popover
                              id={`mouse-over-popover${idx}`}
                              open={popoverOpen}
                              className={classes.popover}
                              classes={{
                                paper: classes.paper,
                              }}
                              anchorEl={popoverAnchorEl}
                              anchorOrigin={{
                                vertical: "bottom",
                                horizontal: "left",
                              }}
                              transformOrigin={{
                                vertical: "top",
                                horizontal: "left",
                              }}
                              onClose={handlePopoverClose}
                              disableRestoreFocus
                            >
                              <Typography>
                                <Box fontFamily="Monospace">
                                  {item.output.split("\n").map((line) => (
                                    <>
                                      <span>{line}</span>
                                      <br />
                                    </>
                                  ))}
                                </Box>
                              </Typography>
                            </Popover>
                          </>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                {!Array.isArray(dbStats[key]) &&
                  (!Number.isNaN(Number(dbStats[key]))
                    ? Number(dbStats[key]).toLocaleString()
                    : dbStats[key])}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
};

export default DBStats;
