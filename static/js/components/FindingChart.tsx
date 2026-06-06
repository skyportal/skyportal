import { makeStyles } from "tss-react/mui";
import { type Ref, useEffect, useRef, useState } from "react";
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

import { showNotification } from "baselayer/components/Notifications";
import { Tooltip } from "@mui/material";
import { useAppDispatch } from "../types/hooks";
import { useLazyGetSourceFinderChartQuery } from "../ducks/source";
import Button from "./Button";

const initialFormState = {
  imagesource: "ps1",
  facility: "Keck",
  positionsource: "ztfref",
  findersize: 4.0,
  numoffset: 3,
};

const useStyles = makeStyles()(() => ({
  media: {
    maxWidth: "100%",
    width: "95%",
  },
  spinner: {
    position: "relative",
    margin: "auto",
    width: "50%",
    fontWeight: "bold",
    fontSize: "1.25rem",
    textAlign: "center",
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
  labels: {
    height: "0.5rem",
    padding: 0,
    margin: 0,
  },
}));

interface FinderImageProps {
  id: string;
  image: string;
  classes: { media: string };
  componentRef: Ref<HTMLImageElement>;
}

const FinderImage = ({
  id,
  image,
  classes,
  componentRef,
}: FinderImageProps) => {
  const { src } = useImage({
    srcList: image,
  });
  return (
    <img alt={`${id}`} src={src} className={classes.media} ref={componentRef} />
  );
};

const PlaceHolder = () => {
  const { classes } = useStyles();
  return (
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
};

const FindingChart = () => {
  const dispatch = useAppDispatch();
  const [getSourceFinderChart] = useLazyGetSourceFinderChartQuery();
  const { classes } = useStyles();
  const {
    handleSubmit,
    getValues,
    control,

    formState: { errors },
  } = useForm();
  const { id } = useParams();

  const [params, setParams] = useState({ ...initialFormState });

  const [image, setImage] = useState<any>(null);
  const [publicUrl, setPublicUrl] = useState<any>(null);

  const componentRef = useRef<any>(null);

  useEffect(() => {
    const fetchImage = async () => {
      if (!id) return;
      const formData = {
        type: "png",
        image_source: `${params?.imagesource}`,
        use_ztfref: `${params?.positionsource === "ztfref"}`,
        imsize: `${params?.findersize}`,
        num_offset_stars: `${params?.numoffset}`,
        facility: `${params?.facility}`,
        as_json: "true",
      };
      try {
        const data: any = await getSourceFinderChart({
          id,
          params: formData,
        }).unwrap();
        const img_data = data?.finding_chart;
        const url = data?.public_url;
        if (!img_data) {
          console.error("No image data returned from server");
          return;
        }
        setImage(`data:image/png;base64,${img_data}`);
        setPublicUrl(url);
      } catch (err) {
        console.error("Error fetching image:", err);
      }
    };
    fetchImage();
  }, [params]);

  const onSubmit = () => {
    setImage(null);
    const formData = {
      ...initialFormState,
      ...getValues(),
    };
    setParams(formData as any);
  };

  const rules = { required: true, min: 2, max: 15, type: "number", step: 0.5 };

  const handlePrint = useReactToPrint({
    contentRef: componentRef,
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
          <Grid size={{ xs: 12, md: 10 }}>
            <Card>
              <CardContent style={{ textAlign: "center" }}>
                <div>
                  {image ? (
                    <FinderImage
                      id={id as string}
                      image={image}
                      classes={classes}
                      componentRef={componentRef}
                    />
                  ) : (
                    <PlaceHolder />
                  )}
                </div>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Card>
              <CardContent>
                <div>
                  <form
                    onSubmit={handleSubmit(onSubmit)}
                    className={classes.form}
                  >
                    <FormControl>
                      <InputLabel id="ImageSourceSelect">
                        Primary Image Source
                      </InputLabel>
                      <p className={classes.labels} />
                      <Controller
                        {...({ labelid: "ImageSourceSelectLabel" } as any)}
                        name="imagesource"
                        control={control}
                        defaultValue={params.imagesource}
                        render={({ field: { onChange, value } }) => (
                          <Select
                            labelId="ImageSourceSelectLabel"
                            value={value}
                            onChange={onChange}
                            style={{ minWidth: "100%" }}
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
                      <InputLabel id="PositionLabel">
                        Offset Position Origin
                      </InputLabel>
                      <p className={classes.labels} />
                      <Controller
                        {...({ labelid: "PositionLabel" } as any)}
                        name="positionsource"
                        control={control}
                        defaultValue={params.positionsource}
                        render={({ field: { onChange, value } }) => (
                          <Select
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
                      <p className={classes.labels} />
                      <Controller
                        {...({ labelid: "FacilityLabel" } as any)}
                        name="facility"
                        control={control}
                        defaultValue={params.facility}
                        render={({ field: { onChange, value } }) => (
                          <Select
                            labelId="FacilitySelectLabel"
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
                      <InputLabel id="SizeSelect">
                        Image Size (arcmin)
                      </InputLabel>
                      <p className={classes.labels} />
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
                            style={{ minWidth: "100%" }}
                            onChange={onChange}
                            value={value}
                          />
                        )}
                        name="findersize"
                        control={control}
                        defaultValue={params.findersize}
                        rules={rules}
                      />
                      {errors["findersize"] && (
                        <p>Enter a number between 2 and 15</p>
                      )}
                    </FormControl>
                    <FormControl>
                      <InputLabel id="HowMany"># of Offset Stars</InputLabel>
                      <p className={classes.labels} />
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
                            style={{ minWidth: "100%" }}
                            onChange={onChange}
                            value={value}
                          />
                        )}
                        name="numoffset"
                        control={control}
                        defaultValue={params.numoffset}
                      />
                      {errors["numoffset"] && (
                        <p>Enter an integer between 0 and 5</p>
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
                    <Tooltip title="The public link is only valid temporarily.">
                      <Button
                        secondary
                        onClick={() => {
                          navigator.clipboard.writeText(publicUrl);
                          dispatch(
                            showNotification(
                              "Public link copied to clipboard!",
                            ),
                          );
                        }}
                        disabled={!publicUrl}
                      >
                        Share Link
                      </Button>
                    </Tooltip>
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
