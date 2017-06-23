import React from 'react'
import Plot from './Plot'

const Source = ({ ra, dec, red_shift, name, id }) => (
  <div>
    <hr/>
    <b>{name} (location: {ra}, {dec})</b>
    <hr/>
    <b>Red Shift:</b>{red_shift}<br/>
    <b>Photometry ({id}):</b><br/>
    <Plot url={`/plot_photometry/${id}`}/>
  </div>
);

export default Source;
