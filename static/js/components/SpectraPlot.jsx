import React, { useEffect } from "react";
import PropTypes from "prop-types";

import Plot from "react-plotly.js";

import Slider from "@mui/material/Slider";
import MuiInput from "@mui/material/Input";
import Typography from "@mui/material/Typography";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";

import Button from "./Button";

const c = 299792.458; // km/s

const lines = [
  {
    color: "#ff0000",
    name: "H",
    x: [3970, 4102, 4341, 4861, 6563, 10052, 10941, 12822, 18756],
  },
  {
    color: "#002157",
    name: "He I",
    x: [3889, 4471, 5876, 6678, 7065, 10830, 20580],
  },
  {
    color: "#003b99",
    name: "He II",
    x: [3203, 4686, 5411, 6560, 6683, 6891, 8237, 10124],
  },
  {
    color: "#8a2be2",
    name: "C I",
    x: [8335, 9093, 9406, 9658, 10693, 11330, 11754, 14543],
  },
  {
    color: "#570199",
    name: "C II",
    x: [
      3919, 3921, 4267, 5145, 5890, 6578, 7231, 7236, 9234, 9891, 17846, 18905,
    ],
  },
  {
    color: "#a30198",
    name: "C III",
    x: [4647, 4650, 5696, 6742, 8500, 8665, 9711],
  },
  { color: "#ff0073", name: "C IV", x: [4658, 5801, 5812, 7061, 7726, 8859] },
  {
    color: "#01fee1",
    name: "N II",
    x: [3995, 4631, 5005, 5680, 5942, 6482, 6611],
  },
  { color: "#01fe95", name: "N III", x: [4634, 4641, 4687, 5321, 5327, 6467] },
  { color: "#00ff4d", name: "N IV", x: [3479, 3483, 3485, 4058, 6381, 7115] },
  { color: "#22ff00", name: "N V", x: [4604, 4620, 4945] },
  {
    color: "#007236",
    name: "O I",
    x: [6158, 7772, 7774, 7775, 8446, 9263, 11290, 13165],
  },
  { color: "#007236", name: "[O I]", x: [5577, 6300, 6363] },
  {
    color: "#00a64d",
    name: "O II",
    x: [3390, 3377, 3713, 3749, 3954, 3973, 4076, 4349, 4416, 4649, 6641, 6721],
  },
  { color: "#b9d2c5", name: "[O II]", x: [3726, 3729] },
  { color: "#aeefcc", name: "[O III]", x: [4363, 4959, 5007] },
  { color: "#03d063", name: "O V", x: [3145, 4124, 4930, 5598, 6500] },
  { color: "#01e46b", name: "O VI", x: [3811, 3834] },
  { color: "#aba000", name: "Na I", x: [5890, 5896, 8183, 8195] },
  {
    color: "#8c6239",
    name: "Mg I",
    x: [3829, 3832, 3838, 4571, 4703, 5167, 5173, 5184, 5528, 8807],
  },
  {
    color: "#bf874e",
    name: "Mg II",
    x: [
      2796, 2798, 2803, 4481, 7877, 7896, 8214, 8235, 9218, 9244, 9632, 10092,
      10927, 16787,
    ],
  },
  { color: "#6495ed", name: "Si I", x: [10585, 10827, 12032, 15888] },
  { color: "#5674b9", name: "Si II", x: [4128, 4131, 5958, 5979, 6347, 6371] },
  { color: "#ffe4b5", name: "S I", x: [9223, 10457, 13809, 18940, 22694] },
  {
    color: "#a38409",
    name: "S II",
    x: [5433, 5454, 5606, 5640, 5647, 6715, 13529, 14501],
  },
  { color: "#009000", name: "Ca I", x: [19453, 19753] },
  {
    color: "#005050",
    name: "Ca II",
    x: [
      3159, 3180, 3706, 3737, 3934, 3969, 8498, 8542, 8662, 9931, 11839, 11950,
    ],
  },
  { color: "#859797", name: "[Ca II]", x: [7292, 7324] },
  {
    color: "#009090",
    name: "Mn I",
    x: [12900, 13310, 13630, 13859, 15184, 15263],
  },
  { color: "#cd5c5c", name: "Fe I", x: [11973] },
  {
    color: "#f26c4f",
    name: "Fe II",
    x: [4303, 4352, 4515, 4549, 4924, 5018, 5169, 5198, 5235, 5363],
  },
  { color: "#f9917b", name: "Fe III", x: [4397, 4421, 4432, 5129, 5158] },
  {
    color: "#ffe4e1",
    name: "Co II",
    x: [
      15759, 16064, 16361, 17239, 17462, 17772, 21347, 22205, 22497, 23613,
      24596,
    ],
  },
  {
    color: "#a55031",
    name: "WR WN",
    x: [
      4058, 4341, 4537, 4604, 4641, 4686, 4861, 4945, 5411, 5801, 6563, 7109,
      7123, 10124,
    ],
  },
  {
    color: "#b9a44f",
    name: "WR WC/O",
    x: [
      3811, 3834, 3886, 4341, 4472, 4647, 4686, 4861, 5598, 5696, 5801, 5876,
      6563, 6678, 6742, 7065, 7236, 7726, 9711,
    ],
  },
  {
    color: "#8357bd",
    name: "Galaxy",
    x: [
      2025, 2056, 2062, 2066, 2249, 2260, 2343, 2374, 2382, 2576, 2586, 2594,
      2599, 2798, 2852, 3727, 3934, 3969, 4341, 4861, 4959, 5007, 5890, 5896,
      6548, 6563, 6583, 6717, 6731,
    ],
  },
  { color: "#e5806b", name: "Tellurics-1", x: [6867, 6884] },
  { color: "#e5806b", name: "Tellurics-2", x: [7594, 7621] },
  {
    color: "#6dcff6",
    name: "Sky Lines",
    x: [
      4168, 4917, 4993, 5199, 5577, 5890, 6236, 6300, 6363, 6831, 6863, 6923,
      6949, 7242, 7276, 7316, 7329, 7341, 7359, 7369, 7402, 7437, 7470, 7475,
      7480, 7524, 7570, 7713, 7725, 7749, 7758, 7776, 7781, 7793, 7809, 7821,
      7840, 7853, 7869, 7879, 7889, 7914, 7931, 7947, 7965, 7978, 7993, 8015,
      8026, 8063, 8281, 8286, 8299, 8311, 8346, 8365, 8384, 8399, 8418, 8432,
      8455, 8468, 8496, 8507, 8542, 8552, 8632, 8660, 8665, 8768, 8781, 8795,
      8831, 8854, 8871, 8889, 8907, 8923, 8947, 8961, 8991, 9004, 9040, 9051,
      9093, 9103, 9158,
    ],
  },
];

function median(values) {
  if (values.length === 0) throw new Error("No inputs");

  const sorted = [...values].sort((a, b) => a - b);

  const half = Math.floor(sorted.length / 2);

  if (sorted.length % 2) return sorted[half];

  return (sorted[half - 1] + sorted[half]) / 2.0;
}

const SpectraPlot = ({ spectra, redshift = 0, mode = "desktop" }) => {
  const [data, setData] = React.useState(null);
  // const [binnedData, setBinnedData] = React.useState(null);
  const [plotData, setPlotData] = React.useState(null);
  const [selectedLines, setSelectedLines] = React.useState([]);
  const [vExpInput, setVExpInput] = React.useState(0);
  const [redshiftInput, setRedshiftInput] = React.useState(redshift || 0);
  const [types, setTypes] = React.useState([]);
  const [tabIndex, setTabIndex] = React.useState(0);

  const findTypes = (spectraData) => {
    let spectrumTypes = [];
    spectraData.forEach((spectrum) => {
      if (
        spectrum.type &&
        spectrum.type !== "" &&
        !(spectrum.type in spectrumTypes)
      ) {
        spectrumTypes.push(spectrum.type);
      }
    });
    // remove duplicates
    spectrumTypes = [...new Set(spectrumTypes)];

    // sort by alphabetical order descending
    spectrumTypes.sort((a, b) => {
      if (a < b) {
        return 1;
      }
      return -1;
    });
    return spectrumTypes;
  };

  const prepareSpectra = (spectraData) => {
    // TODO
    // iterate through each spectrum
    // for each, normalize the fluxes to the median flux
    // normfac = np.nanmedian(np.abs(s.fluxes))
    // normfac = normfac if normfac != 0.0 else 1e-20

    const newSpectra = spectraData.map((spectrum) => {
      const newSpectrum = { ...spectrum };
      let normfac = Math.abs(median(newSpectrum.fluxes));
      normfac = normfac !== 0.0 ? normfac : 1e-20;
      newSpectrum.fluxes_normed = newSpectrum.fluxes.map(
        (flux) => flux / normfac
      );
      return newSpectrum;
    });

    return newSpectra;
  };

  const createTraces = (spectraData, spectrumTypes, tabValue) => {
    // for now (testing), we just grab the first spectrum

    if (spectraData !== null) {
      const traces = spectraData.map((spectrum) => {
        const name = `${spectrum.instrument_name}/${
          spectrum.observed_at.split("T")[0]
        }`;
        const trace = {
          x: spectrum.wavelengths,
          y: spectrum.fluxes_normed,
          type: "scatter",
          mode: "lines",
          name,
          line: {
            shape: "hvh",
          },
          // legendgroup: name,
        };

        if (spectrumTypes?.length > 0) {
          if (spectrum.type === spectrumTypes[tabValue]) {
            trace.visible = true;
          } else {
            trace.visible = false;
          }
        }
        return trace;
      });
      return traces;
    }
    return [];
  };

  const maxFlux = () => {
    if (data !== null) {
      const maxFluxes = data.map((spectrum) =>
        Math.max(...spectrum.fluxes_normed)
      );
      return Math.max(...maxFluxes);
    }
    return 1;
  };

  useEffect(() => {
    const spectrumTypes = findTypes(spectra);
    setTypes(spectrumTypes);
    const newSpectra = prepareSpectra(spectra);
    setData(newSpectra);
    const traces = createTraces(newSpectra, spectrumTypes, 0);
    setPlotData(traces);
  }, [spectra]);

  useEffect(() => {
    if (plotData !== null && types?.length > 0) {
      // if tabIndex has changes, we make invisible all traces that are not of the type of the new tab
      const type = types[tabIndex];
      const newPlotData = [...plotData];
      for (let i = 0; i < newPlotData.length; i += 1) {
        const spectrumType = data[i].type;
        if (spectrumType !== type) {
          newPlotData[i].visible = false;
        } else {
          newPlotData[i].visible = true;
        }
      }
      setPlotData(newPlotData);
    }
  }, [tabIndex]);

  const ShowOrHideAllSpectra = (showOrHide) => {
    if (plotData !== null) {
      const type = types[tabIndex] || types[0];
      const newPlotData = [...plotData];
      for (let i = 0; i < newPlotData.length; i += 1) {
        const spectrumType = data[i].type;
        if (spectrumType === type) {
          if (showOrHide === "show") {
            newPlotData[i].visible = true;
          } else {
            newPlotData[i].visible = false;
          }
        }
      }
      setPlotData(newPlotData);
    }
  };

  const handleChangeTab = (event, newValue) => {
    setTabIndex(newValue);
  };

  return (
    <div style={{ width: "100%", height: "100%" }}>
      {types?.length > 0 && (
        <Tabs
          value={tabIndex}
          onChange={handleChangeTab}
          aria-label="gcn_tabs"
          variant="scrollable"
          xs={12}
          sx={{
            display: {
              maxWidth: "95vw",
              width: "100&",
              "& > button": { lineHeight: "1.5rem" },
            },
          }}
        >
          {types.map((type) => (
            <Tab label={type} key={type} />
          ))}
        </Tabs>
      )}
      <div style={{ width: "100%", height: "60vh", overflowX: "scroll" }}>
        <Plot
          data={plotData}
          layout={{
            xaxis: {
              title: "Wavelength (Å)",
            },
            yaxis: {
              title: "Flux (erg/s/cm²/Å)",
              rangemode: "nonnegative",
            },
            legend: {
              orientation: mode === "desktop" ? "v" : "h",
              yanchor: "top",
              y: mode === "desktop" ? 1 : -0.15,
            },
            showlegend: true,
            autosize: true,
            margin: {
              l: 60,
              r: 15,
              b: 50,
              t: 30,
            },
            // plot_bgcolor: '#EFF2F5',
            // paper_bgcolor: '#EFF2F5'
            shapes: selectedLines
              .map((line) =>
                line.x.map((x) => {
                  const shiftedX =
                    (x * (1 + parseFloat(redshiftInput, 10))) /
                    (1 + parseFloat(vExpInput, 10) / c);
                  return {
                    type: "line",
                    xref: "x",
                    yref: "y",
                    x0: shiftedX,
                    y0: 0,
                    x1: shiftedX,
                    y1: maxFlux(),
                    line: {
                      color: line.color,
                      width: 1,
                    },
                  };
                })
              )
              .flat(),
          }}
          config={{
            // scrollZoom: true,
            displaylogo: false,
          }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </div>
      <div
        style={{
          display: "grid",
          gridAutoFlow: "column",
          gridTemplateRows:
            mode === "desktop" ? "repeat(7, 1fr)" : "repeat(14, 1fr)",
          gap: "0.5rem",
          width: "100%",
          margin: "0.5rem",
          marginTop: "1rem",
          marginBottom: "1rem",
        }}
      >
        {/* we want to display a grid with buttons to toggle each of the lines */}
        {/* the buttons should have a rectangle of the color of the lines, and then the button itself with the name of the line */}
        {lines.map((line) => (
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              width: "fit-content",
            }}
            key={line.name}
          >
            <div
              style={{
                width: "0.6rem",
                height: "1.4rem",
                backgroundColor: line.color,
                marginRight: "0.5rem",
              }}
            />
            <Button
              key={line.wavelength}
              onClick={() => {
                if (selectedLines.includes(line)) {
                  setSelectedLines(selectedLines.filter((l) => l !== line));
                } else {
                  setSelectedLines([...selectedLines, line]);
                }
              }}
              variant="contained"
              secondary
              size="small"
              style={{
                whiteSpace: "nowrap",
                maxHeight: "1.4rem",
                backgroundColor: selectedLines.includes(line)
                  ? line.color
                  : "#ffffff",
                color: selectedLines.includes(line) ? "#ffffff" : "#000000",
              }}
            >
              {line.name}
            </Button>
          </div>
        ))}
      </div>
      <div
        style={{
          minHeight: "2rem",
          display: "flex",
          flexDirection: mode === "desktop" ? "row" : "column",
          justifyContent: "flex-start",
          alignItems: "center",
          gap: "2rem",
          width: "100%",
          margin: "0.5rem",
          marginTop: "1rem",
          marginBottom: "1rem",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Velocity Expansion (km/s)</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={vExpInput}
              onChange={(e, newValue) => setVExpInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={1}
              min={0}
              max={30000}
            />
            <MuiInput
              value={vExpInput}
              onChange={(e) => setVExpInput(e.target.value)}
              margin="dense"
              inputProps={{
                step: 1,
                min: 0,
                max: 30000,
                type: "number",
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "7rem" }}
            />
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-start",
            alignItems: "left",
            gap: 0,
            width: "100%",
            margin: "0.5rem",
            marginBottom: 0,
          }}
        >
          <Typography id="input-slider">Redshift</Typography>
          <div
            style={{
              display: "flex",
              flexDirection: "row",
              justifyContent: "flex-start",
              alignItems: "center",
              gap: "1rem",
              width: "100%",
            }}
          >
            <Slider
              value={redshiftInput}
              onChange={(e, newValue) => setRedshiftInput(newValue)}
              aria-labelledby="input-slider"
              valueLabelDisplay="auto"
              step={0.0001}
              min={0}
              max={3}
            />
            <MuiInput
              value={redshiftInput}
              onChange={(e) => setRedshiftInput(e.target.value)}
              margin="dense"
              inputProps={{
                step: 0.0001,
                min: 0,
                max: 3.0,
                type: "number",
                "aria-labelledby": "input-slider",
              }}
              style={{ width: "7rem" }}
            />
          </div>
        </div>
      </div>
      <div
        style={{
          minHeight: "2rem",
          display: "flex",
          flexDirection: "row",
          justifyContent: "flex-start",
          alignItems: "center",
          gap: "0.5rem",
          width: "100%",
          margin: "0.5rem",
          marginTop: "1rem",
          marginBottom: "1rem",
        }}
      >
        <Button
          onClick={() => ShowOrHideAllSpectra("show")}
          variant="contained"
          color="primary"
          size="small"
        >
          Show All
        </Button>
        <Button
          onClick={() => ShowOrHideAllSpectra("hide")}
          variant="contained"
          color="primary"
          size="small"
        >
          Hide All
        </Button>
      </div>
    </div>
  );
};

SpectraPlot.propTypes = {
  spectra: PropTypes.arrayOf(
    PropTypes.shape({
      observed_at: PropTypes.string,
      instrument_name: PropTypes.string,
      wavelengths: PropTypes.arrayOf(PropTypes.number),
      fluxes: PropTypes.arrayOf(PropTypes.number),
    })
  ).isRequired,
  redshift: PropTypes.number,
  mode: PropTypes.string,
};

SpectraPlot.defaultProps = {
  redshift: 0,
  mode: "desktop",
};

export default SpectraPlot;
