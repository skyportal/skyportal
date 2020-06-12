import React, { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import PropTypes from 'prop-types';
import Plot from 'react-plotly.js';

import { GET } from '../API';

import styles from './CandidatePlot.css';


const arrayToObject = (array) => {
  /*
  Convert an array of object to an object of arrays.

  E.g.:

  [
    {a: 1, b: 2},
    {a: 3, b: 4}
  ]

  becomes

  {
    a: [1, 3],
    b: [2, 4]
  }

  */
  const out = {};
  array.forEach((obj) => {
    Object.keys(obj).forEach((key) => {
      out[key] = (out[key] || []).concat([obj[key]]);
    });
  });
  return out;
};


const CandidatePlot = ({ dataUrl }) => {
  const [traces, setTraces] = useState();
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchTraces = async () => {
      const response = await dispatch(
        GET(dataUrl, 'skyportal/FETCH_CANDIDATEPLOT')
      );

      const data = arrayToObject(response.data);

      setTraces([
        {
          name: 'mag',
          x: data.mjd,
          y: data.mag,
          mode: 'markers',
          type: 'scatter',
          transforms: [{
            type: 'groupby',
            groups: data.filter
          }]
        },
        {
          name: 'lim',
          x: data.mjd,
          y: data.limiting_mag,
          mode: 'markers',
          type: 'scatter',
          marker: {
            symbol: 'triangle-down',
            opacity: 0.4
          },
          transforms: [{
            type: 'groupby',
            groups: data.filter
          }]
        },
      ]);
    };

    fetchTraces();
  }, [dataUrl, dispatch]);

  const layout = {
    xaxis: {
      title: 'mjd'
    },
    yaxis: {
      autorange: 'reversed',
      title: 'mag'
    },
    autosize: true,
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
  };

  return (
    <Plot
      className={styles.plot}
      data={traces}
      layout={layout}
      useResizeHandler
      config={{ responsive: true }}
    />
  );
};

CandidatePlot.propTypes = {
  dataUrl: PropTypes.string.isRequired
};

export default CandidatePlot;
