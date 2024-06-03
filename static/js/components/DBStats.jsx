import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Box from "@mui/material/Box";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import Button from "./Button";

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
                                secondary
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
