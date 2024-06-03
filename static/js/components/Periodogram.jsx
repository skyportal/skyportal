import React, { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import { Link, useParams } from "react-router-dom";
import makeStyles from "@mui/styles/makeStyles";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import Slider from "@mui/material/Slider";
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Dygraph from "dygraphs";
import { showNotification } from "baselayer/components/Notifications";

import TextLoop from "react-text-loop";
import { Controller, useForm } from "react-hook-form";
import { add, dot, dotMultiply, quantileSeq, transpose } from "mathjs";
import Button from "./Button";

import * as photometryActions from "../ducks/photometry";

const useStyles = makeStyles((theme) => ({
  copyb: {
    display: "block",
    border: "1px solid blue",
  },
  dygraphChart: {
    position: "relative",
    left: "1rem",
    right: "1rem",
    top: "1rem",
    bottom: "1rem",
    minWidth: "100%",
    maxHeight: "100%",
  },
  dygraphLegend: {
    left: "10rem !important",
    textAlign: "right",
    background: "none",
  },
  media: {
    maxWidth: "100%",
    width: "95%",
  },
  button: {
    margin: theme.spacing(1),
  },
  paper: {
    width: "100%",
    padding: theme.spacing(1),
    textAlign: "left",
    color: theme.palette.text.primary,
  },
  items: {
    maxWidth: "100%",
    width: "10rem",
    fullWidth: "true",
    display: "flex",
    wrap: "nowrap",
  },
  spinner: {
    position: "relative",
    margin: "auto",
    width: "50%",
    fontWeight: "bold",
    fontSize: "1.25rem",
    textAlign: "center",
  },
  labels: {
    fontSize: "0.75rem",
  },
  clipboard: {
    fontSize: "0.5rem",
  },
}));

// Generalised Lomb-Scargle periodogram: https://github.com/mzechmeister/GLS/tree/master/javascript
function GLS(t_data_uf, y_data_uf, kwa) {
  let k;
  let i;
  const w = [];
  let wsum = 0;
  let kbest = 0;
  const kwargs = kwa || {};
  const ofac = kwargs.ofac || 20;
  const twopi = 2.0 * Math.PI;
  const nmax = kwargs.nmax || 3e5;
  let C;
  let D;
  let S;
  let YC;
  let YS;
  let CC;
  let SS;
  let CS;
  let sinx;
  let cosx;
  let omega;
  let wi;

  /* eslint-disable react/destructuring-assignment  */
  const goodi = t_data_uf
    ?.map((e, ind) =>
      !(
        Number.isNaN(e) ||
        e == null ||
        Number.isNaN(y_data_uf[ind]) ||
        y_data_uf[ind] == null
      )
        ? ind
        : undefined,
    )
    ?.filter((x) => x);
  /* eslint-enable react/destructuring-assignment  */

  const t_data = goodi.map((ind) => t_data_uf[ind]); // eslint-disable-line react/destructuring-assignment
  const y_data = goodi.map((ind) => y_data_uf[ind]); // eslint-disable-line react/destructuring-assignment
  const e_y = goodi.map((ind) => kwa.e_y[ind]);

  const tmin = Math.min.apply(null, t_data);
  const t = add(t_data, -tmin);

  // sorted time vector and the time differences between successive obs
  const tsort = [...t].sort((a, b) => a - b);
  const diffs = tsort
    ?.slice(1)
    ?.map((x, q) => x - tsort[q])
    ?.filter((val) => val !== 0);
  const tbase = Math.max.apply(null, t);

  i = t.length;
  const nt = t.length;

  // not enough data to determine a periodogram. Send back something
  // so we do not render the plots
  if (nt < 10) {
    return { p: [], f: [], k: 1, fbest: null, tbase };
  }
  // eslint-disable-next-line no-plusplus
  while (i--) {
    w[i] = e_y ? 1 / e_y[i] / e_y[i] : 1;
    wsum += w[i];
  }

  // normalize weights, now "wsum=1"
  i = nt;
  // eslint-disable-next-line no-plusplus
  while (i--) w[i] /= wsum;

  const ymean = dot(w, y_data);
  const y = add(y_data, -ymean);
  const wy = dotMultiply(w, y);
  const YY = dot(wy, y); // Eq.(10), variance for the zero mean data

  // frequency sampling depends on the time span, default for start frequency
  let df = 1 / tbase / ofac;
  // chose as delta_t which is the min of mean time sampling, 75%-tile of the time differences, or fixed low-end
  const delta_t = Math.min(
    tbase / (nt - 1),
    quantileSeq(diffs, 0.75, false),
    0.05 * ofac,
  );

  let fbeg = parseFloat(kwargs.fbeg || (df * ofac) / 2);
  let fend = parseFloat(kwargs.fend || (0.5 * ofac) / delta_t);
  let nf = Math.floor((fend - fbeg) / df) + 1; // size of frequency grid

  // ensure that we're only doing as many as 300,000 calculations (~<5 seconds)
  // bump down the frequency binning (df) and shrink the start and ending limits
  while (nf > nmax) {
    df *= 1.05;
    fbeg *= 1.25;
    fend /= 1.05;
    nf = Math.floor((fend - fbeg) / df) + 1;
  }

  const f = new Array(nf);
  const p = new Array(nf);

  // eslint-disable-next-line no-plusplus
  for (k = 0; k < nf; k++) {
    f[k] = fbeg + k * df;
    omega = twopi * f[k];
    C = 0;
    S = 0;
    YC = 0;
    YS = 0;
    CC = 0;
    SS = 0;
    CS = 0;
    // eslint-disable-next-line no-plusplus
    for (i = 0; i < nt; i++) {
      wi = w[i];
      cosx = Math.cos(omega * t[i]);
      sinx = Math.sin(omega * t[i]);
      if (!kwargs.ls) {
        C += wi * cosx; // Eq.(8)
        S += wi * sinx; // Eq.(9)
      }
      YC += wy[i] * cosx; // Eq.(11) simplifies, since Y should be 0 (mean was subtracted)
      YS += wy[i] * sinx; // Eq.(12)   -"-
      CC += wi * cosx * cosx; // Eq.(13)
      CS += wi * cosx * sinx; // Eq.(15)
    }
    SS = 1 - CC; // Eq.(14)
    SS -= S * S; // Eq.(14)
    CC -= C * C; // Eq.(13)
    CS -= C * S; // Eq.(15)
    D = CC * SS - CS * CS; // Eq.(6)

    // A[k] = (YC*SS-YS*CS) / D
    // B[k] = (YS*CC-YC*CS) / D
    // off[k] = -A[k]*C-B[k]*S

    p[k] =
      ((SS * YC * YC) / D + (CC * YS * YS) / D - (2 * CS * YC * YS) / D) / YY; // Eq.(5)
    if (p[k] > p[kbest]) {
      kbest = k;
    }
  }
  return { p, f, k: kbest, fbest: f[kbest], tbase };
}

const Periodogram = () => {
  const classes = useStyles();
  const { handleSubmit, control, register } = useForm();
  const { id } = useParams();
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[id]);
  const [bestp, setBestp] = useState(null);
  const [run, setRun] = useState(false);
  const [plotted, setPlotted] = useState(false);

  const [establishedfilters, setEstablishedfilters] = useState(false);
  const [periodmultiplier, setPeriodmultiplier] = useState(1.0);

  const [instruments, setInstruments] = useState([]);
  const [filters, setFilters] = useState([]);
  const [mjdmin, setMjdmin] = useState(0);
  const [mjdmax, setMjdmax] = useState(70000);

  const [params, setParams] = useState({
    instrument: null,
    filter: null,
    ofac: "20",
    nmax: 300000,
    fmin: null,
    fmax: null,
  });

  const dataplotRef = useRef();
  const glsplotRef = useRef();
  const phaseplotRef = useRef();

  // plotting functions
  function plotline(graph, x) {
    const lines = [
      [1.0, "rgb(255,0,0,0.9)", 3],
      [0.5, "rgb(200,50,50,0.6)", 1],
      [3.0, "rgb(200,50,50,0.5)", 1],
      [2.0, "rgb(200,50,50,0.6)", 1],
      [4.0, "rgb(200,50,50,0.4)", 1],
    ];

    graph.updateOptions({
      underlayCallback(canvas) {
        for (let i = 0; i < lines.length; i += 1) {
          const loc = Math.log10(x * lines[i][0]);
          canvas.beginPath();
          canvas.moveTo(graph.toDomXCoord(loc), graph.toDomYCoord(0));
          canvas.lineTo(graph.toDomXCoord(loc), graph.toDomYCoord(10));
          [canvas.strokeStyle, canvas.lineWidth] = [lines[i][1], lines[i][2]];
          canvas.stroke();
        }
      },
    });
  }

  function onZoom(minDate, maxDate) {
    // capture the time range of the zoom, so that we can
    // run L-S on only data in this range
    setMjdmin(Math.min(minDate, maxDate));
    setMjdmax(Math.max(minDate, maxDate));
    // rerun with the new time window
    setRun(false);
  }

  function plotdata(times, mags, me) {
    const dat = transpose([times, mags])
      .map((x, i) => [x[0], [x[1], me[i]]])
      .sort((a, b) => b[0] - a[0]);
    const filteredy = mags?.filter((n) => n);
    // eslint-disable-next-line no-new
    new Dygraph(dataplotRef.current, dat, {
      drawPoints: true,
      strokeWidth: 0,
      animatedZooms: true,
      labels: ["time", "mag"],
      errorBars: true,
      valueRange: [Math.max(...filteredy) + 0.1, Math.min(...filteredy) - 0.1],
      dateWindow: [Math.min(...times) - 6, Math.max(...times) + 6],
      zoomCallback: onZoom,
      legend: "never",
    });
  }

  function plotphased(times, mags, p, title) {
    // Create graph with native array as data source
    const pp = [...times.map((x) => x % p), ...times.map((x) => (x % p) + p)];
    const filteredy = mags?.filter((n) => n);
    // eslint-disable-next-line no-new
    new Dygraph(phaseplotRef.current, transpose([pp, [...mags, ...mags]]), {
      drawPoints: true,
      strokeWidth: 0,
      labels: ["phase", "mag"],
      valueRange: [Math.max(...filteredy) + 0.1, Math.min(...filteredy) - 0.1],
      dateWindow: [0, 2 * p],
      title,
      legend: "never",
    });
  }

  function plotGLS(linear_freqs, linear_power, kwargs) {
    // Create graph with native array as data source

    // order by period ([day])
    const periods_all = linear_freqs.map((x) => Math.log10(1.0 / x)).reverse();
    const power_all = linear_power.reverse();

    // select only the range we want (< periodmax)
    const goodi = periods_all
      ?.map((e, i) => (e < kwargs.periodmax ? i : undefined))
      ?.filter((x) => x);
    const periods = goodi?.map((i) => periods_all[i]);
    const power = goodi?.map((i) => power_all[i]);

    const graph = new Dygraph(glsplotRef.current, transpose([periods, power]), {
      clickCallback(e) {
        const x = e.offsetX;
        const y = e.offsetY;
        const dataXY = graph.toDataCoords(x, y);
        setBestp(10 ** dataXY[0]);
      },
      axes: {
        x: { logscale: false },
        y: {},
      },
      strokeWidth: 2,
      animatedZooms: true,
      xlabel: "log Period [day]",
      ylabel: "Power",
      legend: "never",
      labels: ["log Period [day]", "Power"],
    });

    plotline(graph, kwargs.periodbest);
  }

  useEffect(() => {
    if (!photometry) {
      dispatch(photometryActions.fetchSourcePhotometry(id));
    }
    if (photometry && !establishedfilters) {
      const insts = [...new Set(photometry.map((x) => x.instrument_name))];
      const filts = [...new Set(photometry.map((x) => x.filter))];
      setInstruments(insts);
      setFilters(filts);
      if (insts.length > 0 && filts.length > 0) {
        setParams({ instrument: insts[0], filter: filts[0] });
      }
      setEstablishedfilters(true);
    }

    if (photometry && establishedfilters && !run) {
      const data = photometry.filter(
        (x) =>
          x.filter === params.filter && x.instrument_name === params.instrument,
      );
      if (data.length > 0) {
        const times = data.map((x) => x.mjd);
        const mag = data.map((x) => x.mag);
        const magerr = data.map((x) => x.magerr);
        if (!plotted) {
          plotdata(times, mag, magerr);
          setPlotted(true);
        }

        // filtered times
        const ftimes = times.filter((x) => x >= mjdmin && x <= mjdmax);
        const fmag = mag.filter(
          (x, i) => times[i] >= mjdmin && times[i] <= mjdmax,
        );
        const fmagerr = magerr.filter(
          (x, i) => times[i] >= mjdmin && times[i] <= mjdmax,
        );

        const gls = GLS(ftimes, fmag, {
          e_y: fmagerr,
          ofac: parseInt(params.ofac, 20),
          fbeg: parseFloat(params.fmin),
          fend: parseFloat(params.fmax),
          nmax: parseFloat(params.nmax),
          ls: null,
        });

        if (gls.fbest != null) {
          plotGLS(gls.f, gls.p, {
            periodbest: 1 / gls.fbest,
            periodmax: gls.tbase / 3.5,
          });
          setBestp(1 / gls.fbest);
          setRun(true);
        }
      }
    }
    if (run) {
      const data = photometry.filter(
        (x) =>
          x.filter === params.filter &&
          x.instrument_name === params.instrument &&
          x.mjd >= mjdmin &&
          x.mjd <= mjdmax,
      );
      const times = data.map((x) => x.mjd);
      const mag = data.map((x) => x.mag);
      const title = `P=${bestp * periodmultiplier.toFixed(8)} d (${
        params.instrument
      }: ${params.filter})`;
      if (times.length > 0) {
        plotphased(times, mag, bestp * periodmultiplier, title);
      } else {
        dispatch(
          showNotification(
            "No data for this combination of instrument/filter.",
          ),
        );
      }
    }
  }, [
    id,
    photometry,
    params,
    establishedfilters,
    bestp,
    run,
    periodmultiplier,
    dispatch,
  ]);

  const componentRef = useRef();

  const initialFormState = {
    ...params,
  };

  const onSubmit = (formstate) => {
    const formData = {
      ...initialFormState,
      ...formstate,
    };
    setMjdmin(0);
    setMjdmax(70000);
    setPeriodmultiplier(1.0);
    setParams(formData);
    setPlotted(false);
    setRun(false);
  };

  function copyPeriod() {
    try {
      navigator.clipboard.writeText(
        `${(periodmultiplier * bestp).toFixed(15)}`,
      );
      dispatch(
        showNotification(
          `Copied period (${(periodmultiplier * bestp).toFixed(
            8,
          )} d) to clipboard.`,
        ),
      );
    } catch (err) {
      dispatch(showNotification("Could not copy period to clipboard."));
    }
  }

  const marks = [
    {
      value: 0.5,
      label: "½×",
    },
    {
      value: 1,
      label: "1×",
    },
    {
      value: 2.0,
      label: "2×",
    },
    {
      value: 3,
      label: "3×",
    },
  ];

  function valuetext(value) {
    return `${value}×`;
  }

  const handleMultiplierChange = (e, val) => {
    setPeriodmultiplier(val);
  };

  return (
    <>
      <div>
        <div>
          <Typography variant="h5" gutterBottom>
            Interactive Periodogram for{" "}
            <Link to={`/source/${id}`} role="link">
              {id}
            </Link>
          </Typography>
        </div>
        <Grid
          container
          direction="row"
          justifyContent="flex-start"
          alignItems="flex-start"
          spacing={1}
        >
          <Grid item xs={10}>
            <Card>
              <CardContent ref={componentRef}>
                <div>
                  {photometry ? (
                    <div ref={dataplotRef} className={classes.dygraphChart} />
                  ) : (
                    <div className={classes.spinner}>
                      <TextLoop>
                        <span>Downloading photometry</span>
                        <span>Determining filters</span>
                        <span>Showing selected filter</span>
                      </TextLoop>{" "}
                      <br /> <br />
                      <CircularProgress color="primary" />
                    </div>
                  )}
                </div>
                <div>
                  <p />
                  <div ref={glsplotRef} className={classes.dygraphChart} />
                </div>
                <div>
                  <p />
                  <div
                    data-testid="phaseplot"
                    ref={phaseplotRef}
                    className={classes.dygraphChart}
                  />
                </div>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={2} xm={2}>
            <Card>
              <CardContent className={classes.items}>
                <div>
                  <form onSubmit={handleSubmit(onSubmit)}>
                    <Grid
                      container
                      direction="column"
                      justifyContent="space-evenly"
                      alignItems="flex-start"
                      spacing={2}
                    >
                      {params.instrument && (
                        <Grid item xs={12}>
                          <FormControl>
                            <InputLabel
                              className={classes.items}
                              id="InstrumentSourceSelectLabel"
                            >
                              Instrument
                            </InputLabel>
                            <p />
                            <Controller
                              labelId="InstrumentSourceSelectLabel"
                              name="instrument"
                              control={control}
                              defaultValue={params.instrument}
                              className={classes.items}
                              render={() => (
                                <Select>
                                  {instruments.map((instrument) => (
                                    <MenuItem
                                      key={instrument}
                                      value={instrument}
                                    >
                                      {instrument}
                                    </MenuItem>
                                  ))}
                                </Select>
                              )}
                            />
                          </FormControl>
                        </Grid>
                      )}
                      {params.filter && (
                        <>
                          <Grid item xs={12}>
                            <FormControl>
                              <InputLabel
                                className={classes.items}
                                id="FilterSourceSelectLabel"
                              >
                                Filter
                              </InputLabel>
                              <p />
                              <Controller
                                labelId="FilterSourceSelectLabel"
                                name="filter"
                                control={control}
                                defaultValue={params.filter}
                                className={classes.items}
                                render={() => (
                                  <Select>
                                    {filters.map((filt) => (
                                      <MenuItem key={filt} value={filt}>
                                        {filt}
                                      </MenuItem>
                                    ))}
                                  </Select>
                                )}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={12}>
                            <FormControl>
                              <Controller
                                render={({ field: { onChange, value } }) => (
                                  <TextField
                                    size="small"
                                    label="Oversampling Factor"
                                    name="ofac"
                                    type="number"
                                    inputRef={register("ofac")}
                                    className={classes.items}
                                    onChange={onChange}
                                    value={value}
                                  />
                                )}
                                name="ofac"
                                control={control}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={12}>
                            <FormControl>
                              <Controller
                                render={({ field: { onChange, value } }) => (
                                  <TextField
                                    size="small"
                                    label="Maximum number of frequencies"
                                    name="nmax"
                                    type="number"
                                    inputRef={register("nmax")}
                                    className={classes.items}
                                    onChange={onChange}
                                    value={value}
                                  />
                                )}
                                name="nmax"
                                control={control}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={12}>
                            <FormControl>
                              <Controller
                                render={({ field: { onChange, value } }) => (
                                  <TextField
                                    size="small"
                                    label="Minimum Frequency [1/day]"
                                    name="fmin"
                                    type="number"
                                    inputRef={register("fmin")}
                                    className={classes.items}
                                    onChange={onChange}
                                    value={value}
                                  />
                                )}
                                name="fmin"
                                control={control}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={12}>
                            <FormControl>
                              <Controller
                                render={({ field: { onChange, value } }) => (
                                  <TextField
                                    size="small"
                                    label="Maximum Frequency [1/day]"
                                    name="fmax"
                                    type="number"
                                    inputRef={register("fmax")}
                                    className={classes.items}
                                    onChange={onChange}
                                    value={value}
                                  />
                                )}
                                name="fmax"
                                control={control}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={8}>
                            <Button
                              primary
                              type="submit"
                              name="periodogramButton"
                              className={classes.button}
                            >
                              Recalculate
                            </Button>
                          </Grid>
                          <Grid item xs={12}>
                            <Typography gutterBottom>
                              Change the parameters above then recalculate. When
                              you zoom to a new time range in the top plot the
                              L-S periodogram is calculated for that range. The
                              red vertical lines show the best peak and
                              harmonics. Click the middle plot to fold on that
                              frequency.
                            </Typography>
                          </Grid>
                          <Grid item xs={12}>
                            <Typography id="period-slider" gutterBottom>
                              Period multiplier
                            </Typography>
                            <Slider
                              value={periodmultiplier}
                              getAriaValueText={valuetext} // eslint-disable-line react/jsx-no-bind
                              aria-labelledby="period-slider"
                              step={null}
                              max={3}
                              min={0.5}
                              marks={marks}
                              valueLabelDisplay="auto"
                              onChange={handleMultiplierChange}
                            />
                          </Grid>
                          <Grid item xs={12}>
                            {bestp && (
                              <>
                                <Typography>
                                  P=
                                  <span data-testid="bestp" className="bestp">
                                    {(periodmultiplier * bestp).toFixed(6)}
                                  </span>{" "}
                                  d
                                </Typography>
                                <Button
                                  secondary
                                  onClick={() => copyPeriod()}
                                  className={classes.clipboard}
                                >
                                  Copy period to clipboard
                                </Button>
                              </>
                            )}
                          </Grid>
                        </>
                      )}

                      <p />
                    </Grid>
                  </form>
                </div>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </div>
    </>
  );
};

export default Periodogram;
