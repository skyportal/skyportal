/* eslint-disable */
// import * as Bokeh from "@bokeh/bokehjs";

// import * as Models from "../components/BokehModels";
// Bokeh.Models.register_models(Models);
let bokehJSON;
fetch(
  `/api/internal/plot/spectroscopy/${sourceId}?width=800&height=600&onTopSpectraId=${this.item}`
)
  .then((res) => res.json())
  .then((data) => {
    console.log(data);
    console.log(data.data.bokehJSON);
    bokehJSON = data.data.bokehJSON;
  });
console.log(bokehJSON);
window.Bokeh = Bokeh;
if (bokehJSON) {
  Bokeh.embed.embed_item(bokehJSON, "bokeh-spectroscopy");
}
