import React, { Component } from 'react';
import PropTypes from 'prop-types';

import "../../../node_modules/bokehjs/build/js/bokeh.js";
import "../../../node_modules/bokehjs/build/css/bokeh.css";
import "../../../node_modules/bokehjs/build/js/bokeh-widgets.js";
import "../../../node_modules/bokehjs/build/css/bokeh-widgets.css";

function bokeh_render_plot(node, docs_json, render_items) {
  // Create bokeh div element
  var bokeh_div = document.createElement("div");
  var inner_div = document.createElement("div");
  bokeh_div.setAttribute("class", "bk-root" );
  inner_div.setAttribute("class", "bk-plotdiv");
  inner_div.setAttribute("id", render_items[0].elementid);
  bokeh_div.appendChild(inner_div);
  node.appendChild(bokeh_div);

  // Generate plot
  Bokeh.safely(function() {
    Bokeh.embed.embed_items(docs_json, render_items);
  });
}

class Plot extends Component {
  constructor(props) {
    super(props);
    this.state = {
      plotData: null
    };
  }

  async componentDidMount() {
    let plotData = await this.props.fetchPlotData(this.props.url);
    if (plotData) {
      this.setState({ plotData, error: false });
    } else {
      this.setState({ error: true });
    }
  }

  render() {
    let { plotData, error } = this.state;
    if (error) {
      return <b>Error: Could not fetch plotting data</b>
    }
    if (!plotData) {
      return <b>Please wait while we load your plotting data...</b>;
    }

    let { docs_json, render_items } = plotData;
    docs_json = JSON.parse(docs_json);
    render_items = JSON.parse(render_items);

    return (
      <div
          ref={
            (node) => {
              node && bokeh_render_plot(node, docs_json, render_items)
            }
          }
      />
    );
  }
}
Plot.propTypes = {
  url: PropTypes.string.isRequired,
  fetchPlotData: PropTypes.func.isRequired
};

export default Plot;
