import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";

import { makeStyles } from "@material-ui/core/styles";
import Table from "@material-ui/core/Table";
import TableBody from "@material-ui/core/TableBody";
import TableCell from "@material-ui/core/TableCell";
import TableHead from "@material-ui/core/TableHead";
import TableRow from "@material-ui/core/TableRow";

import SearchBox from "./SearchBox";
import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";

import styles from "./SourceList.css";

const useStyles = makeStyles({
  table: {
    width: 80,
    height: 12
  },
  cell: {
    padding: 7
  }
});

const SourceList = () => {
  const sources = useSelector((state) => state.sources);

  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const dispatch = useDispatch();

  useEffect(() => {
    if (!sources.latest) {
      dispatch(sourcesActions.fetchSources());
    }
  }, []);

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }

  const tableClasses = useStyles();

  if (sources) {
    return (
      <div className={styles.SourceListWrapper}>
        <h2>Sources</h2>
        <SearchBox sources={sources} />
        {!sources.queryInProgress && (
          <div>
            <Table
              className={tableClasses.table}
              size="small"
              aria-label="a dense table"
            >
              <TableHead>
                <TableRow>
                  <TableCell className={tableClasses.cell}>
                    Last detected
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    ID
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    RA
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    DEC
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    varstar
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    transient
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    disagree
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    is_roid
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    Gmag
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    Teff
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    Score
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    N Detections
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    Simbad Class
                  </TableCell>
                  <TableCell className={tableClasses.cell} align="left">
                    TNS Name
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sources.latest &&
                  sources.latest.map((source) => (
                    <TableRow key={source.id}>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.last_detected &&
                          String(source.last_detected).split(".")[0]}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        <Link to={`/source/${source.id}`}>{source.id}</Link>
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.ra && Number(source.ra).toFixed(3)}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.dec && Number(source.dec.toFixed(4))}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.varstar.toString()}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.transient.toString()}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {(source.transient === source.varstar).toString()}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.is_roid.toString()}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.gaia_info &&
                          Number(JSON.parse(source.gaia_info).Gmag).toFixed(2)}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.gaia_info &&
                          JSON.parse(source.gaia_info).Teff &&
                          Number(JSON.parse(source.gaia_info).Teff).toFixed(1)}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {Number(source.score).toFixed(2)}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.detect_photometry_count}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.simbad_class}
                      </TableCell>
                      <TableCell className={tableClasses.cell} align="left">
                        {source.tns_name}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    );
  } else {
    return "Loading sources...";
  }
};

export default SourceList;
