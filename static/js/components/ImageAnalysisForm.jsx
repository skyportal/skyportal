import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
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

const useStyles = makeStyles(() => ({
  SelectItem: {
    whiteSpace: "break-spaces",
  },
}));

const ImageAnalysisForm = ({ obj_id }) => {
  const classes = useStyles();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { enum_types } = useSelector((state) => state.enum_types);
  const dispatch = useDispatch();

  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);

  const defaultDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");

  const handleSubmit = async ({ formData }) => {
    const data = { ...formData };
    data.instrument_id = selectedInstrumentId;
    data.obstime = data.obstime.replace("+00:00", "").replace(".000Z", "");

    const result = await dispatch(
      sourceActions.submitImageAnalysis(obj_id, data)
    );
    if (result.status === "success") {
      dispatch(showNotification("Image analysis submitted"));
    }
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

  const catalogs = ["ps1", "gaiaedr3", "skymapper", "sdss", "usnob1", "gsc"];
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
      catalog_limiting_magnitude: {
        type: "number",
        title: "Limiting magnitude cutoff for catalog",
        default: 21,
      },
      template: {
        type: "string",
        title: "Template",
        default: "PanSTARRS/DR1/g",
        enum: templates,
      },
      saturation: {
        type: "number",
        title: "Saturation [counts]",
        default: 50000,
      },
      image_data: {
        type: "string",
        format: "data-url",
        title: "Image data file",
        description: "Image data file",
      },
    },
    required: ["obstime", "filter", "image_data"],
    dependencies: {
      crossmatch_catalog: {
        oneOf: [
          {
            properties: {
              crossmatch_catalog: {
                enum: ["ps1"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["gmag", "rmag", "imag", "zmag"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["gmag", "rmag", "imag", "zmag"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
          {
            properties: {
              crossmatch_catalog: {
                enum: ["gaiaedr3"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["Gmag", "BPmag", "RPmag"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["Gmag", "BPmag", "RPmag"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
          {
            properties: {
              crossmatch_catalog: {
                enum: ["usnob1"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["R1mag", "B1mag"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["R1mag", "B1mag"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
          {
            properties: {
              crossmatch_catalog: {
                enum: ["gsc"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["Rmag", "Bjmag", "Vmag", "Imag"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["Rmag", "Bjmag", "Vmag", "Imag"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
          {
            properties: {
              crossmatch_catalog: {
                enum: ["skymapper"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["uPSF", "vPSF", "gPSF", "rPSF", "iPSF", "zPSF"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["uPSF", "vPSF", "gPSF", "rPSF", "iPSF", "zPSF"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
          {
            properties: {
              crossmatch_catalog: {
                enum: ["sdss"],
              },
              crossmatch_catalog_filter_1: {
                type: "string",
                enum: ["umag", "gmag", "rmag", "imag", "zmag"],
                title: "Crossmatch catalog filter (in closest band)",
              },
              crossmatch_catalog_filter_2: {
                type: "string",
                enum: ["umag", "gmag", "rmag", "imag", "zmag"],
                title:
                  "Crossmatch catalog filter (in second band for color term)",
              },
            },
          },
        ],
      },
    },
  };

  return (
    <div>
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
