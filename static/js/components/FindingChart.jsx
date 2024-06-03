import React, { Suspense, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import makeStyles from "@mui/styles/makeStyles";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import Input from "@mui/material/Input";
import Grid from "@mui/material/Grid";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import PrintIcon from "@mui/icons-material/Print";

import TextLoop from "react-text-loop";
import { useImage } from "react-image";
import { Controller, useForm } from "react-hook-form";
import { useReactToPrint } from "react-to-print";
import Button from "./Button";

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
  const {
    handleSubmit,
    getValues,
    control,

    formState: { errors },
  } = useForm();
  const { id } = useParams();

  const [params, setParams] = useState({
    imagesource: "ps1",
    positionsource: "gaia",
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
    use_ztfref: `${params.positionsource === "ztfref"}`,
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
          justifyContent="flex-start"
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
                      justifyContent="space-evenly"
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
                            labelid="ImageSourceSelectLabel"
                            name="imagesource"
                            control={control}
                            defaultValue={params.imagesource}
                            className={classes.items}
                            render={({ field: { onChange, value } }) => (
                              <Select
                                labelId="ImageSourceSelectLabel"
                                value={value}
                                onChange={onChange}
                              >
                                <MenuItem value="desi">DESI DR8</MenuItem>
                                <MenuItem value="ztfref">
                                  ZTF Ref Image
                                </MenuItem>
                                <MenuItem value="dss">DSS2</MenuItem>
                                <MenuItem value="ps1">PS1</MenuItem>
                              </Select>
                            )}
                          />
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel
                            className={classes.items}
                            id="PositionLabel"
                          >
                            Offset Position Origin
                          </InputLabel>
                          <p />
                          <Controller
                            labelid="PositionLabel"
                            name="positionsource"
                            control={control}
                            defaultValue={params.positionsource}
                            className={classes.items}
                            render={({ field: { onChange, value } }) => (
                              <Select
                                labelId="PositionSelectLabel"
                                value={value}
                                onChange={onChange}
                              >
                                <MenuItem value="ztfref">ZTF Ref</MenuItem>
                                <MenuItem value="gaia">Gaia DR3</MenuItem>
                              </Select>
                            )}
                          />
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel className={classes.items} id="SizeSelect">
                            Image Size (arcmin)
                          </InputLabel>
                          <Controller
                            render={({ field: { onChange, value } }) => (
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
                                onChange={onChange}
                                value={value}
                              />
                            )}
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
                            render={({ field: { onChange, value } }) => (
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
                                onChange={onChange}
                                value={value}
                              />
                            )}
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
                          primary
                          type="submit"
                          name="finderButton"
                          className={classes.button}
                        >
                          Update
                        </Button>
                      </Grid>
                      <p />
                      <Grid item xs={8}>
                        <Button
                          secondary
                          className={classes.button}
                          endIcon={<PrintIcon />}
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
