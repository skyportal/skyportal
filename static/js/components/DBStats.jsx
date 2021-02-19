import React, { useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";
import Typography from "@material-ui/core/Typography";
import CircularProgress from "@material-ui/core/CircularProgress";

import * as dbStatsActions from "../ducks/dbStats";

const DBStats = () => {
  const dispatch = useDispatch();
  const dbStats = useSelector((state) => state.dbStats);

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
                {/* eslint-disable-next-line no-nested-ternary */}
                {!Number.isNaN(Number(dbStats[key])) ? (
                  Number(dbStats[key]).toLocaleString()
                ) : Array.isArray(dbStats[key]) ? (
                  <ul>
                    {dbStats[key].map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  dbStats[key]
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
};

export default DBStats;
