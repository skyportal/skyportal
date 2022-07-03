import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";
import dataUriToBuffer from "data-uri-to-buffer";
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
    formData.instrument_id = selectedInstrumentId;
    formData.obstime = formData.obstime
      .replace("+00:00", "")
      .replace(".000Z", "");

    if (Object.keys(formData).includes("image_file")) {
      formData.image_data = dataUriToBuffer(formData.image_file).toString();
    }
    const result = await dispatch(
      sourceActions.submitImageAnalysis(obj_id, formData)
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
      image_file: {
        type: "string",
        format: "data-url",
        title: "Image data file",
        description: "Image data file",
      },
    },
    required: ["obstime", "filter", "image_file"],
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
