import React from 'react'
import PlotContainer from '../containers/PlotContainer'


const Source = ({ ra, dec, red_shift, id }) => {
  if (id === undefined) {
    return <div>Source not found</div>
  } else {
    return (
      <div>
        <hr/>
        <b>{id} (location: {ra}, {dec})</b>
        <hr/>
        <b>Red Shift: </b>{red_shift}<br/>
        <b>Photometry:</b><br/>
        <PlotContainer url={`/plot_photometry/${id}`}/>
        <b>Spectroscopy:</b><br/>
        <PlotContainer url={`/plot_spectroscopy/${id}`}/>
    </div>
    )
  }
};


export default Source;
