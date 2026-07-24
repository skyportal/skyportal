// Full prebuilt Plotly bundle, used by the source statistics page for its
// WebGL 2D scatter (scattergl, fast with tens of thousands of points) and 3D
// scatter3d views. Imported as the prebuilt dist (not plotly.js/lib/*) because
// the source modules require Plotly's own CSS/glsl build config that rspack
// lacks; loaded only on that lazy route, so it stays out of the main bundle.
import Plotly from "plotly.js/dist/plotly.min.js";

export default Plotly;
