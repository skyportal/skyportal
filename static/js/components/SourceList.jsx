import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';


const SourceList = ({ sources }) => (
  <div>
    <h2>
Sources
    </h2>

    <table id="tab">
     <tr>
     <th>Last detected</th><th>Name</th><th>RA</th><th>DEC</th><th>varstar</th><th>transient</th><th>disagree</th><th>Score</th><th>N detections</th><th>Simbad Class</th></tr>
      {
        sources.map((source, idx) => (
          <tr key={source.id}>
            <td>{source.last_detected.split(".")[0]}&nbsp;&nbsp;</td>
            <td><Link to={`/source/${source.id}`}>
              {source.id}</Link></td>
              <td>{Number(source.ra_dis).toFixed(3)}</td><td>{Number(source.dec_dis.toFixed(4))}</td>
              <td>{source.varstar.toString()}</td>
              <td>{source.transient.toString()}</td>
              <td>{(source.transient == source.varstar).toString()}</td>
              <td>{Number(source.score).toFixed(2)}
              </td>
              <td>{source.detect_photometry_count}</td>
              <td>{source.simbad_class}</td>
          </tr>
        ))
      }
    </table>
    <script>
    sorttable.makeSortable(document.getElementById('tab'));
    </script>
  </div>
);

SourceList.propTypes = {
  sources: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default SourceList;
