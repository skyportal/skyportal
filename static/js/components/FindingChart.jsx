import makeStyles from "@mui/styles/makeStyles";
import React, { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import PrintIcon from "@mui/icons-material/Print";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import FormControl from "@mui/material/FormControl";
import Grid from "@mui/material/Grid";
import Input from "@mui/material/Input";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";

import { Controller, useForm } from "react-hook-form";
import { useImage } from "react-image";
import TextLoop from "react-text-loop";
import { useReactToPrint } from "react-to-print";
import Button from "./Button";
import Box from "@mui/material/Box";

const initialFormState = {
  imagesource: "ps1",
  facility: "Keck",
  positionsource: "ztfref",
  findersize: 4.0,
  numoffset: 3,
};

const useStyles = makeStyles((theme) => ({
  media: {
    maxWidth: "100%",
    width: "95%",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    justifyContent: "center",
    minWidth: "100%",
    // make sure the children elements use 100% of the available width
    "& > *": {
      width: "100%",
    },
    // make sure there is a 0.5rem gap between the children elements
    gap: "1.5rem",
  },
}));

const PlaceHolder = () => (
  <Box sx={{ textAlign: "center", fontWeight: "bold", fontSize: "1.25rem" }}>
    <TextLoop>
      <span>Downloading image</span>
      <span>Querying for offset stars</span>
      <span>Reprojecting Image</span>
      <span>Rendering finder</span>
    </TextLoop>
    <div>
      <CircularProgress color="primary" sx={{ marginTop: "2rem" }} />
    </div>
  </Box>
);

const FindingChart = () => {
  const classes = useStyles();
  const {
    handleSubmit,
    getValues,
    control,
    formState: { errors },
  } = useForm();
  const { id } = useParams();

  const [params, setParams] = useState({ ...initialFormState });

  const [image, setImage] = useState(null);

  const componentRef = useRef();

  useEffect(() => {
    const fetchImage = async () => {
      const url = new URL(`/api/sources/${id}/finder`, window.location.href);
      url.search = new URLSearchParams({
        type: "png",
        image_source: `${params.imagesource}`,
        use_ztfref: `${params.positionsource === "ztfref"}`,
        imsize: `${params.findersize}`,
        num_offset_stars: `${params.numoffset}`,
        facility: `${params.facility}`,
      });
      const response = await fetch(url);
      if (response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        setImage(imageUrl);
      } else {
        console.error("Error fetching image:", response.statusText);
      }
    };
    fetchImage();
  }, [params]);

  function FinderImage() {
    const { src } = useImage({
      srcList: image,
    });
    return (
      <img
        alt={`${id}`}
        src={src}
        className={classes.media}
        ref={componentRef}
      />
    );
  }

  const onSubmit = () => {
    setImage(null);
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setParams(formData);
  };

  const handlePrint = useReactToPrint({
    contentRef: componentRef,
    documentTitle: `finder_${id}.pdf`,
    pageStyle: "@page {size: landscape}",
  });

  return (
    <div>
      <Typography variant="h5" gutterBottom>
        Interactive Finder for{" "}
        <Link to={`/source/${id}`} role="link">
          {id}
        </Link>
      </Typography>
      <Grid
        container
        direction="row"
        justifyContent="flex-start"
        alignItems="flex-start"
        spacing={1}
      >
        <Grid item xs={12} md={10}>
          <Card>
            <CardContent style={{ textAlign: "center" }}>
              {image ? <FinderImage /> : <PlaceHolder />}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={2}>
          <Card>
            <CardContent>
              <form onSubmit={handleSubmit(onSubmit)} className={classes.form}>
                <FormControl>
                  <InputLabel id="ImageSourceSelectLabel">
                    Primary Image Source
                  </InputLabel>
                  <Controller
                    name="imagesource"
                    control={control}
                    defaultValue={params.imagesource}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        labelId="ImageSourceSelectLabel"
                        label="Primary Image Source"
                        value={value}
                        onChange={onChange}
                      >
                        <MenuItem value="desi">DESI DR8</MenuItem>
                        <MenuItem value="ztfref">ZTF Ref Image</MenuItem>
                        <MenuItem value="dss">DSS2</MenuItem>
                        <MenuItem value="ps1">PS1</MenuItem>
                      </Select>
                    )}
                  />
                </FormControl>
                <FormControl>
                  <InputLabel id="PositionSelectLabel">
                    Offset Position Origin
                  </InputLabel>
                  <Controller
                    name="positionsource"
                    control={control}
                    defaultValue={params.positionsource}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        label="Offset Position Origin"
                        labelId="PositionSelectLabel"
                        value={value}
                        onChange={onChange}
                        style={{ minWidth: "100%" }}
                      >
                        <MenuItem value="ztfref">ZTF Ref</MenuItem>
                        <MenuItem value="gaia">Gaia DR3</MenuItem>
                      </Select>
                    )}
                  />
                </FormControl>
                <FormControl>
                  <InputLabel id="FacilityLabel">Facility</InputLabel>
                  <Controller
                    name="facility"
                    control={control}
                    defaultValue={params.facility}
                    render={({ field: { onChange, value } }) => (
                      <Select
                        label="Facility"
                        labelid="FacilityLabel"
                        value={value}
                        onChange={onChange}
                        style={{ minWidth: "100%" }}
                      >
                        <MenuItem value="Keck">Keck</MenuItem>
                        <MenuItem value="Shane">Shane</MenuItem>
                        <MenuItem value="P200">P200</MenuItem>
                        <MenuItem value="P200-NGPS">P200 (NGPS)</MenuItem>
                      </Select>
                    )}
                  />
                </FormControl>
                <FormControl>
                  <InputLabel id="SizeSelect">Image Size (arcmin)</InputLabel>
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <Input
                        type="number"
                        margin="dense"
                        inputProps={{
                          "aria-labelledby": "SizeSelect",
                          step: 0.5,
                        }}
                        onChange={onChange}
                        value={value}
                      />
                    )}
                    name="findersize"
                    control={control}
                    defaultValue={params.findersize}
                    rules={{ required: true, min: 2, max: 15, step: 0.5 }}
                  />
                  {errors.findersize && (
                    <Typography color="error" variant="caption">
                      Enter a number between 2 and 15
                    </Typography>
                  )}
                </FormControl>
                <FormControl>
                  <InputLabel id="HowMany"># of Offset Stars</InputLabel>
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <Input
                        type="number"
                        margin="dense"
                        inputProps={{ "aria-labelledby": "HowMany", step: 1 }}
                        style={{ minWidth: "100%" }}
                        onChange={onChange}
                        value={value}
                      />
                    )}
                    name="numoffset"
                    control={control}
                    defaultValue={params.numoffset}
                    rules={{ required: true, min: 1, max: 4, step: 1 }}
                  />
                  {errors.numoffset && (
                    <Typography color="error" variant="caption">
                      Enter an integer between 1 and 4
                    </Typography>
                  )}
                </FormControl>
                <Button primary type="submit" name="finderButton">
                  Update
                </Button>
                <Button
                  secondary
                  endIcon={<PrintIcon />}
                  onClick={handlePrint}
                  disabled={!image}
                >
                  Print
                </Button>
              </form>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </div>
  );
};

export default FindingChart;
