import React, { useEffect } from "react";
import { Link } from "react-router-dom";
import { useSelector, useDispatch } from "react-redux";

import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";

import SearchBox from "./SearchBox";
import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";

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
  }, [sources.latest, dispatch]);

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }
  if (sources) {
    return (
      <Paper elevation={1}>
        <div style={{ padding: "1rem", height: "100%" }}>
          <Typography variant="h6">Sources</Typography>

          <SearchBox sources={sources} />
          {!sources.queryInProgress && (
            <div style={{ overflowX: "scroll" }}>
              <table id="tab" style={{ paddingTop: "10px" }}>
                <thead>
                  <tr>
                    <th />
                    <th />
                    <th colSpan="2">Position</th>
                    <th colSpan="4">Type</th>
                    <th colSpan="2">Gaia</th>
                    <th />
                    <th />
                    <th />
                    <th />
                  </tr>

                  <tr>
                    <th>Last detected</th>
                    <th>Name</th>
                    <th>RA</th>
                    <th>DEC</th>
                    <th>varstar</th>
                    <th>transient</th>
                    <th>disagree</th>
                    <th>is_roid</th>
                    <th>Gmag</th>
                    <th>
                      T<sub>eff</sub>
                    </th>
                    <th>Score</th>
                    <th>
                      N
                      <br />
                      detections
                    </th>
                    <th>
                      Simbad
                      <br />
                      Class
                    </th>
                    <th>TNS Name</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.latest &&
                    sources.latest.map((source) => (
                      <tr key={source.id}>
                        <td>
                          {source.last_detected &&
                            String(source.last_detected).split(".")[0]}
                        </td>
                        <td>
                          <Link to={`/source/${source.id}`}>{source.id}</Link>
                        </td>
                        <td>{source.ra && Number(source.ra).toFixed(3)}</td>
                        <td>{source.dec && Number(source.dec.toFixed(4))}</td>
                        <td>{source.varstar.toString()}</td>
                        <td>{source.transient.toString()}</td>
                        <td>
                          {(source.transient === source.varstar).toString()}
                        </td>
                        <td>{source.is_roid.toString()}</td>
                        <td>
                          {source.altdata?.gaia?.info?.Gmag &&
                            Number(source.altdata.gaia.info.Gmag).toFixed(2)}
                        </td>
                        <td>
                          {source.altdata?.gaia?.info?.Teff &&
                            Number(source.altdata.gaia.info.Teff).toFixed(1)}
                        </td>
                        <td>{Number(source.score).toFixed(2)}</td>
                        <td>{source.detect_photometry_count}</td>
                        <td>{source.altdata?.simbad?.class ?? ""}</td>
                        <td>{source.altdata?.tns?.name ?? ""}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
          {sources.queryInProgress && (
            <div>
              <br />
              <br />
              <i>Query in progress...</i>
            </div>
          )}
        </div>
      </Paper>
    );
  }
  return <div>Loading sources...</div>;
};

export default SourceList;
