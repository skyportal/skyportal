import React from 'react';
import PropTypes from 'prop-types';

// These imports are necessary to initialize Bokeh + its extensions

// eslint-disable-next-line import/extensions
import "bokehjs/bokeh.js";
// eslint-disable-next-line import/extensions
import "bokehcss/bokeh.css";
// eslint-disable-next-line import/extensions
import "bokehjs/bokeh-widgets.js";
// eslint-disable-next-line import/extensions
import "bokehcss/bokeh-widgets.css";


function bokeh_render_plot(node, docs_json, render_items, custom_model_js) {
  // Create bokeh div element
  const bokeh_div = document.createElement("div");
  const inner_div = document.createElement("div");
  bokeh_div.setAttribute("class", "bk-root");
  inner_div.setAttribute("class", "bk-plotdiv");
  inner_div.setAttribute("id", render_items[0].elementid);
  bokeh_div.appendChild(inner_div);
  while (node.hasChildNodes()) { node.removeChild(node.lastChild); }
  node.appendChild(bokeh_div);

  // We have to give the Bokeh-generated JS snippet access to Bokeh.
  // We do that by attaching Bokeh to the (global) Window object, and then
  // modifying "this" (used by the universal module initializer) to point
  // to it.
  //
  // The next statement may seem strange, since "Bokeh" is not defined; but the import
  // above and/or webpack handles that for us.

  // eslint-disable-next-line no-undef
  window.Bokeh = Bokeh;
  custom_model_js = custom_model_js.replace('this', 'root');
  // eslint-disable-next-line no-eval
  eval(`const root = { Bokeh: window.Bokeh }; ${custom_model_js}`);

  // Generate plot
  // eslint-disable-next-line no-undef
  Bokeh.safely(() => {
    // eslint-disable-next-line no-undef
    Bokeh.embed.embed_items(docs_json, render_items);
  });
}

const Plot = (props) => {
  const { plotData, error } = props;
  if (error) {
    return (
      <b>
        Error: Could not fetch plotting data
      </b>
    );
  }
  if (!plotData) {
    return (
      <b>
        Please wait while we load your plotting data...
      </b>
    );
  }
  if (!plotData.docs_json) {
    return (
      <b>
        <i>
          No data to plot.
        </i>
      </b>
    );
  }

  const { docs_json, render_items, custom_model_js } = plotData;

  return (
    <div
      className={props.className}
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
};


Plot.propTypes = {
  plotData: PropTypes.object,
  error: PropTypes.bool,
  className: PropTypes.string
};

Plot.defaultProps = {
  plotData: null,
  error: false,
  className: ""
};

export default Plot;
