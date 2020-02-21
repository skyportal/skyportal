import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';

import SearchBox from './SearchBox';
import * as sourcesActions from '../ducks/sources';
import UninitializedDBMessage from './UninitializedDBMessage';

import styles from './SourceList.css';

import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableContainer from '@material-ui/core/TableContainer';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import Paper from '@material-ui/core/Paper';


const SourceList = () => {
  const sources = useSelector(
    (state) => state.sources
  );

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
  
  if (sources) {
    // rows = [];
    // if (sources.latest) {
    //   rows = sources.latest.map((source, idx) => {
    //     return {
    //       last_detected: source.last_detected && String(source.last_detected).split(".")[0],
    //       id: source.id, 
    //       ra: source.ra && Number(source.ra).toFixed(3),
    //       dec: source.dec && Number(source.dec.toFixed(4)),
    //       varstar: source.varstar.toString(),
    //       transient: source.transient.toString(),
    //       disagree: (source.transient === source.varstar).toString(),
    //       is_roid: source.is_roid.toString(),
    //       Gmag: source.gaia_info && Number(JSON.parse(source.gaia_info).Gmag).toFixed(2),
    //       Teff: source.gaia_info && JSON.parse(source.gaia_info).Teff && Number(JSON.parse(source.gaia_info).Teff).toFixed(1),
    //       Score: Number(source.score).toFixed(2),
    //       NDetections: source.detect_photometry_count,
    //       simbad_class: source.simbad_class,
    //       tns_name: source.tns_name,
    //     };
    //   });  
    // }
    // {rows.map(row => (
    //   <TableRow key={row.name}>
    //     <TableCell> Last detected </TableCell>
    //     <TableCell align="right"> {row.Name} </TableCell>
    //     <TableCell align="right"> {row.RA} </TableCell>
    //     <TableCell align="right"> {row.DEC} </TableCell>
    //     <TableCell align="right"> {row.varstar} </TableCell>
    //     <TableCell align="right"> {row.transient} </TableCell>
    //     <TableCell align="right"> {row.disagree} </TableCell>
    //     <TableCell align="right"> {row.is_roid} </TableCell>
    //     <TableCell align="right"> {row.Gmag} </TableCell>
    //     <TableCell align="right"> {row.Teff} </TableCell>
    //     <TableCell align="right"> {row.Score} </TableCell>
    //     <TableCell align="right"> {row.NDetections} </TableCell>
    //     <TableCell align="right"> {row.simbad_class} </TableCell>
    //     <TableCell align="right"> {row.tns_name} </TableCell>
    //   </TableRow>
    // console.log(rows);
    return (
      <div className={styles.SourceListWrapper}>
        <h2>
          Sources
        </h2>
        !sources.queryInProgress && (
        <SearchBox sources={sources} />
          <TableContainer component={Paper}>
            <Table size="small" aria-label="a dense table">
              <TableHead>
                <TableRow>
                  <TableCell> Last detected </TableCell>
                  <TableCell align="right"> ID </TableCell>
                  <TableCell align="right"> RA </TableCell>
                  <TableCell align="right"> DEC </TableCell>
                  <TableCell align="right"> varstar </TableCell>
                  <TableCell align="right"> transient </TableCell>
                  <TableCell align="right"> disagree </TableCell>
                  <TableCell align="right"> is_roid </TableCell>
                  <TableCell align="right"> Gmag </TableCell>
                  <TableCell align="right"> Teff </TableCell>
                  <TableCell align="right"> Score </TableCell>
                  <TableCell align="right"> N Detections </TableCell>
                  <TableCell align="right"> Simbad Class </TableCell>
                  <TableCell align="right"> TNS Name </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {sources.latest && sources.latest.map((source) => (
                  <TableRow key={source.id}>
                    <TableCell align="right"> {source.last_detected && String(source.last_detected).split(".")[0]} </TableCell>
                    <TableCell align="right"> {source.id} </TableCell>
                    <TableCell align="right"> {source.ra && Number(source.ra).toFixed(3)} </TableCell>
                    <TableCell align="right"> {source.dec && Number(source.dec.toFixed(4))} </TableCell>
                    <TableCell align="right"> {source.varstar.toString()} </TableCell>
                    <TableCell align="right"> {source.transient.toString()} </TableCell>
                    <TableCell align="right"> {(source.transient === source.varstar).toString()} </TableCell>
                    <TableCell align="right"> {source.is_roid.toString()} </TableCell>
                    <TableCell align="right"> {source.gaia_info && Number(JSON.parse(source.gaia_info).Gmag).toFixed(2)} </TableCell>
                    <TableCell align="right"> {source.gaia_info && JSON.parse(source.gaia_info).Teff && Number(JSON.parse(source.gaia_info).Teff).toFixed(1)} </TableCell>
                    <TableCell align="right"> {Number(source.score).toFixed(2)} </TableCell>
                    <TableCell align="right"> {source.detect_photometry_count} </TableCell>
                    <TableCell align="right"> {source.simbad_class} </TableCell>
                    <TableCell align="right"> {source.tns_name} </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )
        {
          sources.queryInProgress && (
            <div>
              <br />
              <br />
              <i>
                Query in progress...
              </i>
            </div>
          )
        }
      </div>
    );
  } else {
    return "Loading sources...";
  }
};

export default SourceList;
