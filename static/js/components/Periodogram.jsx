import React, { useRef, useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import { Link, useParams } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";

import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import CircularProgress from "@material-ui/core/CircularProgress";
import FormControl from "@material-ui/core/FormControl";
import Button from "@material-ui/core/Button";
import Slider from "@material-ui/core/Slider";
import Input from "@material-ui/core/Input";
import Grid from "@material-ui/core/Grid";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Typography from "@material-ui/core/Typography";
import Dygraph from "dygraphs";
import { showNotification } from "baselayer/components/Notifications";

import TextLoop from "react-text-loop";
import { useForm, Controller } from "react-hook-form";
import { dot, dotMultiply, add, transpose } from "mathjs";

import * as photometryActions from "../ducks/photometry";

const useStyles = makeStyles((theme) => ({
  copyb: {
    display: "block",
    border: "1px solid blue",
  },
  dygraphChart: {
    position: "relative",
    left: "1px",
    right: "1px",
    top: "1px",
    bottom: "1px",
    minWidth: "100%",
    maxHeight: "100%",
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

  const goodi = t_data_uf
    .map((e, ind) =>
      !(
        Number.isNaN(e) ||
        e == null ||
        Number.isNaN(y_data_uf[ind]) ||
        y_data_uf[ind] == null
      )
        ? ind
        : undefined
    )
    .filter((x) => x);
  const t_data = goodi.map((ind) => t_data_uf[ind]);
  const y_data = goodi.map((ind) => y_data_uf[ind]);
  const e_y = goodi.map((ind) => kwa.e_y[ind]);

  const tmin = Math.min.apply(null, t_data);
  const t = add(t_data, -tmin);
  const tbase = Math.max.apply(null, t);

  i = t.length;
  const nt = t.length;
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

  const df = 1 / tbase / ofac; // frequency sampling depends on the time span, default for start frequency
  const delta_t = tbase / (nt - 1); // mean time sampling
  const fbeg = parseFloat(kwargs.fbeg || df);
  const fend = parseFloat(kwargs.fend || (0.5 * ofac) / delta_t);
  const nf = Math.floor((fend - fbeg) / df) + 1; // size of frequency grid

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
  const { handleSubmit, getValues, control } = useForm();
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
  });

  const placeholder = (
    <div className={classes.spinner}>
      <TextLoop>
        <span>Downloading photometry</span>
        <span>Determining filters</span>
        <span>Showing selected filter</span>
      </TextLoop>{" "}
      <br /> <br />
      <CircularProgress color="primary" />
    </div>
  );

  const dataplotRef = useRef();
  const glsplotRef = useRef();
  const phaseplotRef = useRef();

  // plotting functions
  function plotline(g, x) {
    const lines = [
      [1.0, "rgb(255,0,0,0.9)", 3],
      [0.5, "rgb(200,50,50,0.6)", 1],
      [3.0, "rgb(200,50,50,0.5)", 1],
      [2.0, "rgb(200,50,50,0.6)", 1],
      [4.0, "rgb(200,50,50,0.4)", 1],
    ];

    g.updateOptions({
      underlayCallback(canvas) {
        for (let i = 0; i < lines.length; i += 1) {
          const loc = Math.log10(x * lines[i][0]);
          canvas.beginPath();
          canvas.moveTo(g.toDomXCoord(loc), g.toDomYCoord(0));
          canvas.lineTo(g.toDomXCoord(loc), g.toDomYCoord(10));
          [canvas.strokeStyle, canvas.lineWidth] = [lines[i][1], lines[i][2]];
          canvas.stroke();
        }
      },
    });
  }

  function ma(minDate, maxDate) {
    setMjdmin(Math.min(minDate, maxDate));
    setMjdmax(Math.max(minDate, maxDate));
    // rerun with the new time window
    setRun(false);
  }

  function plotdata(xx, yy, me) {
    const dat = transpose([xx, yy])
      .map((x, i) => [x[0], [x[1], me[i]]])
      .sort((a, b) => b[0] - a[0]);
    const filteredy = yy.filter((n) => n);
    // eslint-disable-next-line no-new
    new Dygraph(dataplotRef.current, dat, {
      drawPoints: true,
      strokeWidth: 0,
      labels: ["time", "mag"],
      errorBars: true,
      valueRange: [Math.max(...filteredy) + 0.1, Math.min(...filteredy) - 0.1],
      dateWindow: [Math.min(...xx) - 6, Math.max(...xx) + 6],
      zoomCallback: ma,
    });
  }

  function plotphased(xx, yy, p, title) {
    // Create graph with native array as data source
    const pp = [...xx.map((x) => x % p), ...xx.map((x) => (x % p) + p)];
    // eslint-disable-next-line no-new
    new Dygraph(phaseplotRef.current, transpose([pp, [...yy, ...yy]]), {
      drawPoints: true,
      strokeWidth: 0,
      labels: ["phase", "mag"],
      valueRange: [Math.max(...yy) + 0.1, Math.min(...yy) - 0.1],
      dateWindow: [0, 2 * p],
      title,
    });
  }

  function plotGLS(xx, yy, kwargs) {
    // Create graph with native array as data source

    // order by period ([day])
    const periods_all = xx.map((x) => Math.log10(1.0 / x)).reverse();
    const power_all = yy.reverse();

    // select only the range we want (< periodmax)
    const goodi = periods_all
      .map((e, i) => (e < kwargs.periodmax ? i : undefined))
      .filter((x) => x);
    const periods = goodi.map((i) => periods_all[i]);
    const power = goodi.map((i) => power_all[i]);

    const g = new Dygraph(glsplotRef.current, transpose([periods, power]), {
      clickCallback(e) {
        const x = e.offsetX;
        const y = e.offsetY;
        const dataXY = g.toDataCoords(x, y);
        setBestp(10 ** dataXY[0]);
      },
      axes: {
        x: { logscale: false },
        y: {},
      },
      strokeWidth: 2,
      xlabel: "log Period [day]",
      ylabel: "Power",
      labels: ["log Period [day]", "Power"],
    });

    plotline(g, kwargs.periodbest);
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
          x.filter === params.filter && x.instrument_name === params.instrument
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
          (x, i) => times[i] >= mjdmin && times[i] <= mjdmax
        );
        const fmagerr = magerr.filter(
          (x, i) => times[i] >= mjdmin && times[i] <= mjdmax
        );

        const gls = GLS(ftimes, fmag, {
          e_y: fmagerr,
          ofac: parseInt(params.ofac, 10),
          fbeg: null,
          fend: null,
          ls: null,
        });

        plotGLS(gls.f, gls.p, {
          periodbest: 1 / gls.fbest,
          periodmax: gls.tbase / 3.5,
        });
        setBestp(1 / gls.fbest);
        setRun(true);
      }
    }
    if (run) {
      const data = photometry.filter(
        (x) =>
          x.filter === params.filter &&
          x.instrument_name === params.instrument &&
          x.mjd >= mjdmin &&
          x.mjd <= mjdmax
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
          showNotification("No data for this combination of instrument/filter.")
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

  const onSubmit = () => {
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setMjdmin(0);
    setMjdmax(70000);
    setPeriodmultiplier(1.0);
    setPlotted(false);
    setRun(false);
    setParams(formData);
  };

  const rules = { required: true, min: 1, max: 25, type: "number", step: 1 };

  function copyPeriod() {
    try {
      navigator.clipboard.writeText(
        `${(periodmultiplier * bestp).toFixed(15)}`
      );
      dispatch(
        showNotification(`Copied period (${bestp?.toFixed(8)} d) to clipboard.`)
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
    return `${value}`;
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
          justify="flex-start"
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
                    <div>{placeholder}</div>
                  )}
                </div>
                <div>
                  <p />
                  <div ref={glsplotRef} className={classes.dygraphChart} />
                </div>
                <div>
                  <p />
                  <div ref={phaseplotRef} className={classes.dygraphChart} />
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
                      justify="space-evenly"
                      alignItems="flex-start"
                      spacing={2}
                    >
                      {params.instrument && (
                        <Grid item xs={12}>
                          <FormControl>
                            <InputLabel
                              className={classes.items}
                              id="InstrumentSourceSelect"
                            >
                              Instrument
                            </InputLabel>
                            <p />
                            <Controller
                              as={Select}
                              labelid="InstrumentSourceSelectLabel"
                              name="instrument"
                              control={control}
                              defaultValue={params.instrument}
                              className={classes.items}
                            >
                              {instruments.map((instrument) => (
                                <MenuItem key={instrument} value={instrument}>
                                  {instrument}
                                </MenuItem>
                              ))}
                            </Controller>
                          </FormControl>
                        </Grid>
                      )}
                      {params.filter && (
                        <>
                          <Grid item xs={12}>
                            <FormControl>
                              <InputLabel
                                className={classes.items}
                                id="FilterSourceSelect"
                              >
                                Filter
                              </InputLabel>
                              <p />
                              <Controller
                                as={Select}
                                labelid="FilterSourceSelectLabel"
                                name="filter"
                                control={control}
                                defaultValue={params.filter}
                                className={classes.items}
                              >
                                {filters.map((filt) => (
                                  <MenuItem key={filt} value={filt}>
                                    {filt}
                                  </MenuItem>
                                ))}
                              </Controller>
                            </FormControl>
                          </Grid>
                          <Grid item xs={12}>
                            <FormControl>
                              <InputLabel
                                className={classes.items}
                                id="OFACSelect"
                              >
                                ofac
                              </InputLabel>
                              <Controller
                                as={<Input type="number" rules={rules} />}
                                name="ofac"
                                control={control}
                                defaultValue={params.ofac || "20"}
                                className={classes.items}
                              />
                            </FormControl>
                          </Grid>
                          <Grid item xs={8}>
                            <Typography id="period-slider" gutterBottom>
                              Period multiplier
                            </Typography>
                            <Slider
                              value={periodmultiplier}
                              getAriaValueText={valuetext}
                              aria-labelledby="period-slider"
                              step={null}
                              max={3}
                              min={0.5}
                              marks={marks}
                              valueLabelDisplay="auto"
                              onChange={handleMultiplierChange}
                            />
                          </Grid>
                          <Grid item xs={8}>
                            {bestp && (
                              <>
                                <Typography>
                                  P=
                                  <span className="bestp">
                                    {(periodmultiplier * bestp).toFixed(6)}
                                  </span>{" "}
                                  d
                                </Typography>
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="secondary"
                                  onClick={() => copyPeriod()}
                                >
                                  Copy period to clipboard
                                </Button>
                              </>
                            )}
                          </Grid>
                          <Grid item xs={8}>
                            <Button
                              type="submit"
                              color="primary"
                              name="finderButton"
                              variant="contained"
                              className={classes.button}
                            >
                              Recalculate
                            </Button>
                          </Grid>
                          <Typography gutterBottom>
                            Change the parameters above and/or zoom to a new
                            time range in the top plot, then recalculate. The
                            red vertical lines show the best peak and harmonics.
                            Click the middle plot to fold on that frequency.
                          </Typography>
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
