import React, { useState, Suspense } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useParams } from "react-router-dom";
import TextLoop from "react-text-loop";
import { useImage } from "react-image";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as sourceActions from "../ducks/source";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  SelectItem: {
    whiteSpace: "break-spaces",
  },
  linkButton: {
    textDecoration: "none",
    color: theme.palette.info.dark,
    fontWeight: "bold",
    verticalAlign: "baseline",
    backgroundColor: "transparent",
    border: "none",
    cursor: "pointer",
    display: "inline",
    margin: 0,
    padding: 0,
    "&:hover": {
      textDecoration: "underline",
    },
  },
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
}));


const ImageAnalysisForm = ({ obj_id }) => {
  const classes = useStyles();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedPostAnalysis, setSelectedPostAnalysis] = useState(null);
  
  const defaultDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  const { id } = useParams();
  let url = null;

  const placeholder = (
    <div className={classes.spinner}>
      <TextLoop>
        <span>Downloading image</span>
        <span>Querying for offset stars</span>
        <span>Reprojecting image</span>
        <span>Rendering preview</span>
      </TextLoop>{" "}
      <br /> <br />
      <CircularProgress color="primary" />
    </div>
  );

  function PreviewImage(url) {
    const { src } = useImage({
      srcList: url,
    });
    return <img alt={`${id}`} src={src} className={classes.media} />;
  }

  const handleSubmit = async ({ formData }) => {
    const data = { ...formData };
    data.instrument_id = selectedInstrumentId;
    data.obstime = data.obstime.replace("+00:00", "").replace(".000Z", "");

    if (selectedPostAnalysis === null) {
      data.post_analysis = "Post";
    }
    else {data.post_analysis = selectedPostAnalysis;}

    const result = await dispatch(
      sourceActions.submitImageAnalysis(obj_id, data)
    );
    if (result.status === "success") {
      dispatch(showNotification("Image analysis submitted"));
    }

    url = new URL(`/api/internal/sources/${id}/image_analysis`, window.location.href);
    url.search = new URLSearchParams({
    type: "png",
    });
  };


  if (enum_types.length === 0) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const handleSelectedPostAnalysis = (e) => {
    setSelectedPostAnalysis(e.target.value);
  };

  const catalogs = [
    "ps1",
    "gaiadr2",
    "gaiaedr3",
    "skymapper",
    "vsx",
    "apass",
    "sdss",
    "atlas",
    "usnob1",
    "gsc",
  ];
  const astrometric_refinement_method = ["scamp", "astropy", "astrometrynet"];
  const templates = ["PanSTARRS/DR1/g", "PanSTARRS/DR1/r", "PanSTARRS/DR1/i"];

  const imageAnalysisFormSchema = {
    type: "object",
    properties: {
      obstime: {
        type: "string",
        format: "date-time",
        title: "Image Date [UTC]",
        default: defaultDate,
      },
      filter: {
        type: "string",
        oneOf: instLookUp[selectedInstrumentId]?.filters.map((filter) => ({
          enum: [filter],
          title: `${filter}`,
        })),
        title: "Filter list",
        default: instLookUp[selectedInstrumentId]?.filters[0],
      },
      gain: {
        type: "number",
        title: "Gain",
        default: instLookUp[selectedInstrumentId]?.gain,
      },
      s_n_detection: {
        type: "number",
        title: "S/N Detection",
        default: 5,
      },
      s_n_blind_match: {
        type: "number",
        title: "S/N Blind Match",
        default: 20,
      },
      astrometric_refinement_cat: {
        type: "string",
        title: "Astrometric Refinement Catalog",
        default: "ps1",
        enum: catalogs,
      },
      astrometric_refinement_meth: {
        type: "string",
        title: "Astrometric Refinement Method",
        default: "astropy",
        enum: astrometric_refinement_method,
      },
      matching_radius: {
        type: "number",
        title: "Matching Radius (in arcsec)",
        default: 2,
      },
      crossmatch_catalog: {
        type: "string",
        title: "Crossmatch Catalog",
        default: "ps1",
        enum: catalogs,
      },
      template: {
        type: "string",
        title: "Template",
        default: "PanSTARRS/DR1/g",
        enum: templates,
      },
      image_data: {
        type: "string",
        format: "data-url",
        title: "Image data file",
        description: "Image data file",
      },
    },
    required: ["obstime", "filter", "image_data"],
  };

  return (
    <div>
      {(url !=null ) && 
      <div>
        <Suspense fallback={placeholder}>
          <PreviewImage url={url} />
        </Suspense>
      </div>
      }
      <div>
        <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="instrumentSelectLabel"
          value={selectedInstrumentId || ""}
          onChange={handleSelectedInstrumentChange}
          name="gcnPageInstrumentSelect"
          className={classes.SelectItem}
        >
          {instrumentList?.map((instrument) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.instrumentSelectItem}
            >
              {`${telLookUp[instrument.telescope_id]?.name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
      </div>
      <div>
        <InputLabel id="postAnalysisSelectLabel">Post or preview image analysis</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="postAnalysisSelectLabel"
          value={selectedPostAnalysis || ""}
          onChange={handleSelectedPostAnalysis}
          className={classes.SelectItem}
        >
            <MenuItem value = {"Post"}>Post</MenuItem>
            <MenuItem value = {"Preview"}>Preview</MenuItem>
        </Select>
      </div>
      <div>
        <Form
          schema={imageAnalysisFormSchema}
          validator={validator}
          onSubmit={handleSubmit}
          // eslint-disable-next-line react/jsx-no-bind
          liveValidate
        />
      </div>
    </div>
  );
};

ImageAnalysisForm.propTypes = {
  obj_id: PropTypes.number.isRequired,
};

export default ImageAnalysisForm;