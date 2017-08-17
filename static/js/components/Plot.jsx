import React, { Component } from 'react';
import PropTypes from 'prop-types';

// eslint-disable-next-line import/extensions
import "../../../node_modules/bokehjs/build/js/bokeh.js";
// eslint-disable-next-line import/extensions
import "../../../node_modules/bokehjs/build/css/bokeh.css";
// eslint-disable-next-line import/extensions
import "../../../node_modules/bokehjs/build/js/bokeh-widgets.js";
// eslint-disable-next-line import/extensions
import "../../../node_modules/bokehjs/build/css/bokeh-widgets.css";


function bokeh_render_plot(node, docs_json, render_items, custom_model_js) {
  // Create bokeh div element
  const bokeh_div = document.createElement("div");
  const inner_div = document.createElement("div");
  bokeh_div.setAttribute("class", "bk-root");
  inner_div.setAttribute("class", "bk-plotdiv");
  inner_div.setAttribute("id", render_items[0].elementid);
  bokeh_div.appendChild(inner_div);
  node.appendChild(bokeh_div);

  // eslint-disable-next-line no-eval
  eval(custom_model_js);

  // Generate plot
  // eslint-disable-next-line no-undef
  Bokeh.safely(() => {
    // eslint-disable-next-line no-undef
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

  async componentWillMount() {
    const plotData = await this.props.fetchPlotData(this.props.url);
    if (plotData) {
      this.setState({ plotData, error: false });
    } else {
      this.setState({ error: true });
    }
  }

  render() {
    const { plotData, error } = this.state;
    if (error) {
      return <b>Error: Could not fetch plotting data</b>;
    }
    if (!plotData) {
      return <b>Please wait while we load your plotting data...</b>;
    }

    const { docs_json, render_items, custom_model_js } = plotData;

    return (
      <div
        ref={
          (node) => {
            if (node) {
              bokeh_render_plot(
                node,
                JSON.parse(docs_json),
                JSON.parse(render_items),
                custom_model_js
              );
            }
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
