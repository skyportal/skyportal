import React, { useRef, useState, Suspense, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";

import { Link, useParams } from "react-router-dom";
import { makeStyles } from "@material-ui/core/styles";

import Select from "@material-ui/core/Select";
import Switch from "@material-ui/core/Switch";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import CircularProgress from "@material-ui/core/CircularProgress";
import FormControl from "@material-ui/core/FormControl";
import Button from "@material-ui/core/Button";
import Input from "@material-ui/core/Input";
import Grid from "@material-ui/core/Grid";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Typography from "@material-ui/core/Typography";
import PrintIcon from "@material-ui/icons/Print";

import TextLoop from "react-text-loop";
import { useImage } from "react-image";
import { useForm, Controller } from "react-hook-form";
import { useReactToPrint } from "react-to-print";

import * as photometryActions from "../ducks/photometry";
import Dygraph from 'dygraphs';

const useStyles = makeStyles((theme) => ({
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


const isFloat = (x) =>
  typeof x === "number" && Number.isFinite(x) && Math.floor(x) !== x;

function transpose(mat) {
// transpose matrix
return mat[0].map(function(col, i) {
  return mat.map(function(row) {
    return row[i]
  })
});
};

function plotdata(xx,yy) {
// Create graph with native array as data source
//data =  [ [1,10], [2,20], [3,50], [4,70] ];
  const g = new Dygraph(document.getElementById("dataplot"), transpose([xx, yy]), {drawPoints: true, strokeWidth: 0, labels: [ "t", "y" ],
    axes: {y: {valueRange: [Math.max(yy) + 0.1, Math.min(yy) - 0.1] }}});
};

function glsclick(e, x, pts) {
        s.innerHTML += "<b>Click</b> " + pts_info(e,x,pts) + "<br/>";
};

function plotline(g, x) {

  const area = g.getArea();
  const range = g.xAxisRange();

  const lines = [ [1.0, 'rgb(255,0,0,0.5)'], [0.5, 'rgb(200,15,15,0.8)'],
          [3.0, 'rgb(200,0,0,0.5)'], [2.0, 'rgb(200,15,15,0.5)'],
          [4.0, 'rgb(200,15,15,0.5)']];


    g.updateOptions( {underlayCallback: function(canvas, area, gg) {
          for (var i = 0; i < lines.length; i++) {
            const loc = area.x + (Math.log10(x*lines[i][0]) - Math.log10(range[0])) / (Math.log10(range[1]) - Math.log10(range[0])) * area.w;
            canvas.beginPath();
            canvas.moveTo(loc,gg.toDomYCoord(0));
            canvas.lineTo(loc,gg.toDomYCoord(10));
            console.log(loc);
            canvas.strokeStyle = lines[i][1];
            canvas.lineWidth = 3;
            canvas.stroke();
          }
    }});
};

function plotGLS(xx,yy, kwargs) {

  // Create graph with native array as data source
  const periods = xx.map(x => 1.0/x).reverse();
  const power = yy.reverse();
  console.log(kwargs.periodbest);
  const g = new Dygraph(document.getElementById("GLSplot"), transpose([periods, power]),
              {labels: [ "t", "p" ],
               clickCallback: glsclick,
               "axes": {
                  "x": {"logscale": true},
                }
              });
  plotline(g, kwargs.periodbest);
};

function dot(x, y) {
   var i=x.length, sum=0.;
   while(i--) sum += x[i] * y[i];
   return sum;
};

function add(x, a) {
   var i=x.length, xa=[];
   while(i--) xa[i] = x[i] + a;
   return xa;
};

function mul(x, y) {
   var i=y.length, xy=[];
   if (x.length==i) {
      while(i--) xy[i] = x[i] * y[i];
   } else {
      while(i--) xy[i] = x * y[i];
   };
   return xy;
};

function GLS(t_data, y_data, kwargs) {
   var k, i, nt, t, tmin, tbase, ymean, y, w=[], wy, wsum=0.;
   var df, delta_t, fbeg, fend, nf;
   var f, p, kbest=0;
   var kwargs = kwargs || {};
   var ofac = kwargs.ofac || 20.;
   var twopi = 2.0 * Math.PI;
   var YY, C, D, S, YC, YS, CC, SS, CS, sinx, cosx, omega, wi;

   tmin = Math.min.apply(null, t_data);
   t = add(t_data, -tmin);
   tbase = Math.max.apply(null, t);

   i = nt = t.length;
   while(i--) wsum += w[i]= (kwargs.e_y? 1./kwargs.e_y[i]/kwargs.e_y[i] : 1.);

   // normalize weights, now "wsum=1"
   i = nt;
   while(i--) w[i] /= wsum;

   ymean = dot(w, y_data);
   y = add(y_data, -ymean);
   wy = mul(w, y);
   YY = dot(wy, y);    // Eq.(10), variance for the zero mean data

   df = 1. / tbase / ofac;       // frequency sampling depends on the time span, default for start frequency
   delta_t = tbase / (nt-1);     // mean time sampling
   fbeg = parseFloat(kwargs.fbeg || df);
   fend = parseFloat(kwargs.fend || 0.5 * ofac / delta_t);
   console.log(fbeg);
   console.log(fend);
   console.log(tbase);
   console.log(nt);
   nf = Math.floor((fend-fbeg)/df)+1;  // size of frequency grid

   f = new Array(nf);
   p = new Array(nf);

   for(k=0; k<nf; k++) {
      f[k] = fbeg + k * df;
      omega = twopi * f[k];
      C = 0.;
      S = 0.;
      YC = 0.;
      YS = 0.;
      CC = 0.;
      SS = 0.;
      CS = 0.;
      for(i=0; i<nt; i++) {
         wi = w[i];
         cosx = Math.cos(omega * t[i]);
         sinx = Math.sin(omega * t[i]);
         if (!kwargs.ls) {
         C += wi * cosx;         // Eq.(8)
         S += wi * sinx;         // Eq.(9)
         };
         YC += wy[i] * cosx;     // Eq.(11) simplifies, since Y should be 0 (mean was subtracted)
         YS += wy[i] * sinx;     // Eq.(12)   -"-
         CC += wi * cosx * cosx; // Eq.(13)
         CS += wi * cosx * sinx; // Eq.(15)
      };
      SS = 1. - CC;           // Eq.(14)
      SS -= S * S;            // Eq.(14)
      CC -= C * C;            // Eq.(13)
      CS -= C * S;            // Eq.(15)
      D = CC*SS - CS*CS;      // Eq.(6)

// A[k] = (YC*SS-YS*CS) / D
// B[k] = (YS*CC-YC*CS) / D
// off[k] = -A[k]*C-B[k]*S

      p[k] = (SS*YC*YC/D + CC*YS*YS/D - 2.*CS*YC*YS/D) / YY;  // Eq.(5)
      if (p[k]>p[kbest]) {kbest = k;}
   };
   return {p:p, f:f, k:kbest, fbest:f[kbest], tbase:tbase}
};

const Periodogram = () => {
  const classes = useStyles();
  const { handleSubmit, getValues, errors, control } = useForm();
  const { id } = useParams();
  const dispatch = useDispatch();
  const photometry = useSelector((state) => state.photometry[id]);
  const times = null;
  const mag = null;

  const [params, setParams] = useState({
    imagesource: "desi",
    useztfref: true,
    findersize: 4.0,
    numoffset: 3,
  });

  useEffect(() => {
    if (!photometry) {
      dispatch(photometryActions.fetchSourcePhotometry(id));
    }
    if (photometry) {
      const data = photometry.filter(x => x.filter == 'ztfr');
      const times = data.map((x) => x.mjd);
      const mag = data.map((x) => x.mag);
      const magerr = data.map((x) => x.magerr);
      plotdata(times, mag);
      const gls = GLS(times,mag,{e_y: magerr, ofac:20, fbeg: null, fend: null, ls: null});
      console.log(gls.k, gls.fbest);
      plotGLS(gls.f,gls.p, {periodbest:1/gls.fbest, periodmax:gls.tbase/2});
    }
  }, [id, photometry, dispatch]);



  const componentRef = useRef();

  const initialFormState = {
    ...params,
  };

  const url = new URL(`/api/sources/${id}/finder`, window.location.href);
  url.search = new URLSearchParams({
    type: "png",
    image_source: `${params.imagesource}`,
    use_ztfref: `${params.useztfref}`,
    imsize: `${params.findersize}`,
    num_offset_stars: `${params.numoffset}`,
  });

  const placeholder = (
    <div id="dataplot">
    </div>
  );

  function FinderImage() {
    const { src } = useImage({
      srcList: url,
    });
    return <img alt={`${id}`} src={src} className={classes.media} />;
  }

  const onSubmit = () => {
    console.log("here");

    console.log("times", times)
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setParams(formData);

  };

  const rules = { required: true, min: 2, max: 15, type: "number", step: 0.5 };

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
                    <div id="dataplot"></div>
                </div>
                <div>
                    <p />
                    <div id="GLSplot"></div>
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
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel
                            className={classes.items}
                            id="ImageSourceSelect"
                          >
                            Primary Image Source
                          </InputLabel>
                          <p />
                          <Controller
                            as={Select}
                            labelid="ImageSourceSelectLabel"
                            name="imagesource"
                            control={control}
                            defaultValue={params.imagesource}
                            className={classes.items}
                          >
                            <MenuItem value="desi">DESI DR8</MenuItem>
                            <MenuItem value="ztfref">ZTF Ref Image</MenuItem>
                            <MenuItem value="dss">DSS2</MenuItem>
                          </Controller>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <InputLabel
                          id="PositionLabel"
                          className={classes.labels}
                        >
                          Offset Position Origin
                        </InputLabel>
                        <Grid
                          container
                          direction="row"
                          justify="flex-start"
                          alignItems="center"
                          spacing={1}
                        >
                          <Grid item>
                            <InputLabel
                              id="PositionLabell"
                              className={classes.labels}
                            >
                              Gaia DR2
                            </InputLabel>
                          </Grid>
                          <Grid item>
                            <Controller
                              as={<Switch size="small" color="default" />}
                              name="useztfref"
                              labelid="OffsetTypeSelect"
                              defaultValue={params.useztfref}
                              control={control}
                            />
                          </Grid>
                          <Grid item>
                            <InputLabel
                              id="PositionLabelr"
                              className={classes.labels}
                            >
                              ZTF Ref
                            </InputLabel>
                          </Grid>
                        </Grid>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel className={classes.items} id="SizeSelect">
                            Image Size (arcmin)
                          </InputLabel>
                          <Controller
                            as={
                              <Input
                                type="number"
                                margin="dense"
                                inputProps={{
                                  step: 0.5,
                                  min: 2,
                                  max: 15,
                                  type: "number",
                                  "aria-labelledby": "SizeSelect",
                                }}
                              />
                            }
                            name="findersize"
                            control={control}
                            defaultValue={params.findersize}
                            rules={rules}
                            className={classes.items}
                          />
                          {errors.findersize && (
                            <p>Enter a number between 2 and 15</p>
                          )}
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel className={classes.items} id="HowMany">
                            # of Offset Stars
                          </InputLabel>
                          <Controller
                            as={
                              <Input
                                type="number"
                                margin="dense"
                                inputProps={{
                                  step: 1,
                                  min: 0,
                                  max: 4,
                                  type: "number",
                                  "aria-labelledby": "HowMany",
                                }}
                              />
                            }
                            name="numoffset"
                            control={control}
                            defaultValue={params.numoffset}
                            className={classes.items}
                          />
                          {errors.numoffset && (
                            <p>Enter an integer between 0 and 5</p>
                          )}
                        </FormControl>
                      </Grid>
                      <p />
                      <Grid item xs={8}>
                        <Button
                          type="submit"
                          color="primary"
                          name="finderButton"
                          variant="contained"
                          className={classes.button}
                        >
                          Update
                        </Button>
                      </Grid>
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




