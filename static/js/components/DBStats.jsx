import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";
import Dialog from "@material-ui/core/Dialog";
import DialogContent from "@material-ui/core/DialogContent";
import DialogTitle from "@material-ui/core/DialogTitle";
import Box from "@material-ui/core/Box";
import Button from "@material-ui/core/Button";
import List from "@material-ui/core/List";
import ListItem from "@material-ui/core/ListItem";

import * as dbStatsActions from "../ducks/dbStats";

const DBStats = () => {
  const dispatch = useDispatch();
  const dbStats = useSelector((state) => state.dbStats);
  const [clickedCronjobOutput, setClickedCronjobOutput] = useState(null);

  const handleDialogClose = () => {
    setClickedCronjobOutput(null);
  };

  const dialogOpen = Boolean(clickedCronjobOutput);

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
                  <>
                    <List>
                      {dbStats[key].map((item) => (
                        <ListItem key={item.summary}>
                          {item.summary}
                          {item.output && (
                            <>
                              <Button
                                variant="contained"
                                size="small"
                                style={{ marginLeft: "1rem" }}
                                onClick={() =>
                                  setClickedCronjobOutput(item.output)
                                }
                              >
                                See job output
                              </Button>
                            </>
                          )}
                        </ListItem>
                      ))}
                    </List>
                    <Dialog
                      open={dialogOpen}
                      style={{ position: "fixed" }}
                      onClose={handleDialogClose}
                    >
                      <DialogTitle>Process Output</DialogTitle>
                      <DialogContent>
                        <Typography>
                          <Box fontFamily="Monospace">
                            {clickedCronjobOutput &&
                              clickedCronjobOutput.split("\n").map((line) => (
                                <>
                                  <span>{line}</span>
                                  <br />
                                </>
                              ))}
                          </Box>
                        </Typography>
                      </DialogContent>
                    </Dialog>
                  </>
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
