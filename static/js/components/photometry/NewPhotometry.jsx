import React, { useState } from "react";
import PropTypes from "prop-types";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import { useDispatch, useSelector } from "react-redux";
import { showNotification } from "baselayer/components/Notifications";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { submitPhotometry } from "../../ducks/photometry";

const validateDate = (date) => {
  // use a regex to check if the date is written as YYYY-MM-DDThh:mm:ss
  const regex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
  return regex.test(date);
};

const UTCToMJD = (utc) => {
  // convert utc to MJD
  // if the date has anything after the seconds, remove it
  // and instead, add the .000Z to the end
  const utcDate = new Date(`${utc.split(".")[0]}.000Z`);
  const mjd = utcDate / 86400000 + 40587;
  return mjd;
};

const NewPhotometryForm = ({ obj_id }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const groups = useSelector((state) => state.groups.userAccessible);
  // only show instruments that have an imaging mode
  const sortedInstrumentList = [...instrumentList].filter((instrument) =>
    instrument.type.includes("imag"),
  );
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  if (instrumentList.length === 0) {
    return <h3>No instruments available...</h3>;
  }

  const instLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  instrumentList?.forEach((instrumentObj) => {
    instLookUp[instrumentObj.id] = instrumentObj;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const listmag = ["Vega", "AB"];

  const photoFormSchema = {
    type: "object",
    properties: {
      group_ids: {
        type: "array",
        items: {
          type: "number",
          anyOf: groups.map((group) => ({
            enum: [group.id],
            type: "number",
            title: group.name,
          })),
        },
        uniqueItems: true,
        title: "Share with Groups",
        default: [groups[0]?.id],
      },
      dateobs: {
        type: "string",
        title: "Observation date (YYYY-MM-DDThh:mm:ss or MJD)",
      },
      mag: {
        type: "number",
        title: "Magnitude",
      },
      magerr: {
        type: "number",
        title: "Magnitude error",
      },
      limiting_mag: {
        type: "number",
        title: "Limiting magnitude",
      },
      magsys: {
        type: "string",
        enum: listmag,
        title: "Magnitude system",
      },
      origin: {
        type: "string",
        title: "Origin",
      },
      nb_exposure: {
        type: "integer",
        title: "Number of exposures",
      },
      exposure_time: {
        type: "integer",
        title: "Exposure time [i.e. 60 or 300]",
      },
      altdata: {
        type: "string",
        title: 'Alternative json data (i.e. {"note": "poor subtraction"}',
      },
      // add a checkbox called 'coordinates' that is false by default
      // if it is checked, show the ra and dec fields
      coordinates: {
        type: "boolean",
        title: "Enter coordinates",
        default: false,
      },
      filter: {
        type: "string",
        enum: instLookUp[selectedInstrumentId]?.filters,
        title: "Filter",
      },
    },
    required: ["dateobs", "filter", "magsys"],
    dependencies: {
      coordinates: {
        oneOf: [
          {
            properties: {
              coordinates: {
                enum: [true],
              },
              ra: {
                type: "number",
                title: "RA",
              },
              dec: {
                type: "number",
                title: "Dec",
              },
            },
            required: ["ra", "dec"],
          },
        ],
      },
    },
  };

  // vanillaJS
  function isJSON(str) {
    try {
      return JSON.parse(str) && !!str;
    } catch (e) {
      return false;
    }
  }

  const validate = (formData, errors) => {
    if (formData.dateobs && !validateDate(formData.dateobs)) {
      if (Number.isNaN(parseFloat(formData.dateobs))) {
        errors.dateobs.addError(
          "Date must be in the format YYYY-MM-DDThh:mm:ss or MJD",
        );
      }
    }
    if (formData.nb_exposure && formData.nb_exposure < 0) {
      errors.nb_exposure.addError("Number of exposures cannot be negative");
    }
    if (formData.exposure_time && formData.exposure_time < 0) {
      errors.exposure_time.addError("Exposure time cannot be negative");
    }
    if (formData.exposure_time && !formData.nb_exposure) {
      errors.nb_exposure.addError(
        "Please enter a number of exposures when entering an exposure time",
      );
    }
    if (formData.nb_exposure && !formData.exposure_time) {
      errors.exposure_time.addError(
        "Please enter an exposure time when entering a number of exposures",
      );
    }
    if (
      sortedInstrumentList.some(
        (instrument) =>
          instrument.id === selectedInstrumentId &&
          instrument.filters.length === 0,
      )
    ) {
      errors.filter.addError("This instrument has no filters");
    }
    if (selectedInstrumentId && !formData.filter) {
      errors.filter.addError("Please select a filter");
    }
    if (!formData.mag && !formData.limiting_mag) {
      errors.mag.addError("Please enter a magnitude or a limiting magnitude");
    }
    if (formData.mag && !formData.magerr) {
      errors.magerr.addError("Please enter a magnitude error");
    }
    if (formData.mag && Number.isNaN(formData.mag)) {
      errors.mag.addError("Magnitude must be a number");
    }
    if (formData.magerr && Number.isNaN(formData.magerr)) {
      errors.magerr.addError("Magnitude error must be a number");
    }
    if (formData.limiting_mag && Number.isNaN(formData.limiting_mag)) {
      errors.magerr.addError("Limiting magnitude must be a number");
    }
    if (
      formData.coordinates === true &&
      (Number.isNaN(formData.ra) || Number.isNaN(formData.dec))
    ) {
      errors.ra.addError(
        "Please enter a valid RA and Dec when coordinates is checked",
      );
    }
    if (formData.altdata && !isJSON(formData.altdata)) {
      errors.altdata.addError("altdata must be JSON");
    }
    return errors;
  };

  const submit = (data) => {
    const {
      group_ids,
      dateobs,
      mag,
      magerr,
      limiting_mag,
      magsys,
      origin,
      nb_exposure,
      exposure_time,
      coordinates,
      filter,
      ra,
      dec,
      altdata,
    } = data.formData;
    let mjd = null;
    if (validateDate(dateobs)) {
      mjd = UTCToMJD(dateobs);
    } else {
      mjd = parseFloat(dateobs);
    }
    let altdata_json;
    try {
      altdata_json = JSON.parse(altdata);
    } catch (e) {
      altdata_json = {};
    }
    const payload = {
      mjd,
      obj_id,
      magsys,
      instrument_id: selectedInstrumentId,
      filter,
      altdata: altdata_json,
    };

    if (!Number.isNaN(mag)) {
      payload.mag = mag;
    }
    if (!Number.isNaN(magerr)) {
      payload.magerr = magerr;
    }
    if (!Number.isNaN(limiting_mag)) {
      payload.limiting_mag = limiting_mag;
    }
    if (
      nb_exposure !== undefined &&
      exposure_time !== undefined &&
      !Number.isNaN(nb_exposure) &&
      !Number.isNaN(exposure_time)
    ) {
      payload.altdata.exposure = `${nb_exposure}x${exposure_time}`;
    }

    if (group_ids) {
      payload.group_ids = group_ids;
    }

    if (coordinates === true) {
      payload.ra = ra;
      payload.dec = dec;
    }

    if (origin) {
      payload.origin = origin;
    }

    dispatch(submitPhotometry(payload)).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("Photometry added successfully"));
      } else {
        dispatch(showNotification("Error adding photometry"));
      }
    });
  };

  return (
    <div style={{ display: "flex", alignItems: "center" }}>
      {instrumentList?.length > 0 && groups?.length > 0 ? (
        <div>
          <div>
            <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              id="instrumentSelectLabel"
              value={selectedInstrumentId}
              onChange={handleSelectedInstrumentChange}
              name="instrumentSelect"
            >
              {instrumentList?.map((instrument) => (
                <MenuItem value={instrument.id} key={instrument.id}>
                  {`${instrument.name}: ${instrument.filters}`}
                </MenuItem>
              ))}
            </Select>
          </div>
          <div>
            <Form
              schema={photoFormSchema}
              validator={validator}
              onSubmit={submit}
              customValidate={validate}
            />
          </div>
        </div>
      ) : (
        <div>
          <p>Loading instruments and groups</p>
        </div>
      )}
    </div>
  );
};

NewPhotometryForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default NewPhotometryForm;
