import React, { useRef, useState, Suspense } from "react";
import { useParams } from "react-router-dom";

import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import { useImage } from "react-image";
import { useForm, Controller } from "react-hook-form";
import FormControl from "@material-ui/core/FormControl";
import Button from "@material-ui/core/Button";
import Checkbox from "@material-ui/core/Checkbox";
import Input from "@material-ui/core/Input";
import Grid from "@material-ui/core/Grid";
import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";

import Typography from "@material-ui/core/Typography";
import { useReactToPrint } from "react-to-print";
import PrintIcon from "@material-ui/icons/Print";

const useStyles = makeStyles((theme) => ({
  media: {
    width: "100%",
  },
  slider: {
    width: "5rem",
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
    fullWidth: "true",
    display: "flex",
    wrap: "nowrap",
  },
  nested: {
    paddingLeft: theme.spacing(1),
  },
  heading: {
    fontSize: "1.0625rem",
    fontWeight: 500,
  },
  accordion_details: {
    flexDirection: "column",
  },
  button_add: {
    maxWidth: "8.75rem",
  },
  formControl: {
    margin: theme.spacing(1),
    minWidth: "12rem",
  },
  selectEmpty: {
    marginTop: theme.spacing(2),
  },
  root: {
    minWidth: "18rem",
  },
  bullet: {
    display: "inline-block",
    margin: "0 2px",
    transform: "scale(0.8)",
  },
  title: {
    fontSize: "0.875rem",
  },
  big_font: {
    fontSize: "1rem",
  },
  pos: {
    marginBottom: "0.75rem",
  },
  header: {
    paddingBottom: 10,
  },
}));

const FindingChart = () => {
  const classes = useStyles();
  const { handleSubmit, getValues, errors, control } = useForm();
  const { id } = useParams();

  const [imagesource, setImageSource] = useState("desi");
  const [useztfref, setUseztfref] = useState(true);
  const [findersize, setFindersize] = useState(4.0);
  const [howmany, setHowmany] = useState(3);

  const componentRef = useRef();

  const initialFormState = {
    imagesource,
    useztfref,
    findersize,
    howmany,
  };

  const url = `/api/sources/${id}/finder?type=png&image_source=${imagesource}&use_ztfref=${useztfref}&imsize=${findersize}&how_many=${howmany}`;

  const placeholder = (
    <CircularProgress className={classes.media} color="secondary" />
  );

  function FinderImage() {
    const { src } = useImage({
      srcList: url,
    });
    return <img alt={`${id}`} src={src} className={classes.media} />;
  }

  const onSubmit = () => {
    console.log(getValues());
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setImageSource(formData.imagesource);
    setUseztfref(!formData.useztfref);
    setFindersize(formData.findersize);
    setHowmany(formData.howmany);
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
            {`Finder for ${id}`}
          </Typography>
        </div>
        <Grid
          container
          direction="row"
          justify="flex-start"
          alignItems="flex-start"
          spacing={1}
        >
          <Grid item xs={10} ref={componentRef}>
            <Card>
              <CardContent>
                <div>
                  <Suspense fallback={placeholder}>
                    <FinderImage />
                  </Suspense>
                </div>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={2}>
            <Card>
              <CardContent>
                <div>
                  <form onSubmit={handleSubmit(onSubmit)}>
                    <Grid
                      container
                      direction="column"
                      justify="space-evenly"
                      alignItems="flex-start"
                      spacing={4}
                    >
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel id="ImageSourceSelect">
                            Primary Image Source
                          </InputLabel>
                          <Controller
                            as={Select}
                            labelId="ImageSourceSelectLabel"
                            name="imagesource"
                            control={control}
                            defaultValue={imagesource}
                          >
                            <MenuItem value="desi">DESI DR8</MenuItem>
                            <MenuItem value="ztfref">ZTF Ref Image</MenuItem>
                            <MenuItem value="dss">DSS2</MenuItem>
                          </Controller>
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel id="PositionSelect">
                            Use DR2 positions?
                          </InputLabel>
                          <Controller
                            as={
                              <Checkbox
                                value={false}
                                aria-labelledby="PositionSelect"
                              />
                            }
                            labelId="PositionSelectLabel"
                            name="useztfref"
                            control={control}
                            defaultValue={!useztfref}
                          />
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel id="SizeSelect">
                            Image Size (arcmin)
                          </InputLabel>
                          <Controller
                            as={
                              <Input
                                type="number"
                                className={classes.slider}
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
                            defaultValue={findersize}
                            rules={rules}
                          />
                          {errors.findersize && (
                            <p>Enter a number between 2 and 15</p>
                          )}
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <FormControl>
                          <InputLabel id="HowMany">
                            # of Offset Stars
                          </InputLabel>
                          <Controller
                            as={
                              <Input
                                type="number"
                                className={classes.slider}
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
                            name="howmany"
                            control={control}
                            defaultValue={howmany}
                          />
                          {errors.howmany && (
                            <p>Enter an integer between 0 and 5</p>
                          )}
                        </FormControl>
                      </Grid>
                      <Grid item xs={12}>
                        <Button
                          type="submit"
                          color="primary"
                          name="finderButton"
                          variant="contained"
                          size="large"
                        >
                          Update
                        </Button>
                      </Grid>
                      <Grid item xs={12}>
                        <Button
                          variant="contained"
                          color="secondary"
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
