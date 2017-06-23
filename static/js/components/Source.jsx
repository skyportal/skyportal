import React from 'react'

const Source = ({ ra, dec, red_shift, name }) => (
  <div>
    <hr/>
    <b>{name} (location: {ra}, {dec})</b>
    <hr/>
    <b>Red Shift:</b>{red_shift}<br/>
    <b>Photometry:</b>

  </div>
);

export default Source;
