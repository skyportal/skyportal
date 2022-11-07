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

const SpectrumAnalysisForm = ({ obj_id }) => {
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
      sourceActions.submitSpectrumAnalysis(obj_id, data)
    );
    if (result.status === "success") {
      dispatch(showNotification("Spectrum analysis submitted"));
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
        title: "Spectrum Date [UTC]",
        default: defaultDate,
      },
      image_data: {
        type: "string",
        format: "data-url",
        title: "Spectrum data file",
        description: "Spectrum data file",
      },
      fluxcal_data: {
        type: "string",
        format: "data-url",
        title: "Flux calibration data file",
        description: "Flux calibration data file",
      },
    },
    required: ["obstime", "image_data"],
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

SpectrumAnalysisForm.propTypes = {
  obj_id: PropTypes.number.isRequired,
};

export default SpectrumAnalysisForm;
