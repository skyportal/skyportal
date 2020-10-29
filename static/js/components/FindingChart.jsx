import React, { useRef, useState, Suspense } from "react";
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

const FindingChart = () => {
  const classes = useStyles();
  const { handleSubmit, getValues, errors, control } = useForm();
  const { id } = useParams();

  const [params, setParams] = useState({
    imagesource: "desi",
    useztfref: true,
    findersize: 4.0,
    numoffset: 3,
  });

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
    <div className={classes.spinner}>
      <TextLoop>
        <span>Downloading image</span>
        <span>Querying for offset stars</span>
        <span>Reprojecting Image</span>
        <span>Rendering finder</span>
      </TextLoop>{" "}
      <br /> <br />
      <CircularProgress color="primary" />
    </div>
  );

  function FinderImage() {
    const { src } = useImage({
      srcList: url,
    });
    return <img alt={`${id}`} src={src} className={classes.media} />;
  }

  const onSubmit = () => {
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setParams(formData);
  };

  const rules = { required: true, min: 2, max: 15, type: "number", step: 0.5 };

  const handlePrint = useReactToPrint({
    content: () => componentRef.current,
    documentTitle: `finder_${id}.pdf`,
    pageStyle: "@page {size: landscape}",
  });

  return (
    <>
      <div>
        <div>
          <Typography variant="h5" gutterBottom>
            Interactive Finder for{" "}
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
                  <Suspense fallback={placeholder}>
                    <FinderImage />
                  </Suspense>
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
                      <Grid item xs={8}>
                        <Button
                          variant="contained"
                          color="default"
                          className={classes.button}
                          startIcon={<PrintIcon />}
                          onClick={handlePrint}
                        >
                          Print
                        </Button>
                      </Grid>
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

export default FindingChart;
