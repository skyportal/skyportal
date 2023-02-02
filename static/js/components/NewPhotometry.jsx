import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { showNotification } from "baselayer/components/Notifications";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { submitPhotometry } from "../ducks/photometry";

const validateDate = (date) => {
  // use a regex to check if the date is written as YYYY-MM-DDThh:mm:ss
  const regex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
  return regex.test(date);
};

const UTCToMJD = (utc) => {
  // convert utc to MJD
  const utcDate = new Date(utc);
  const mjd = utcDate / 86400000 + 40587;
  return mjd;
};

const NewPhotometryForm = ({ obj_id }) => {
  const dispatch = useDispatch();
  const { instrumentList } = useSelector((state) => state.instruments);
  const groups = useSelector((state) => state.groups.userAccessible);
  // only show instruments that have an imaging mode
  const sortedInstrumentList = [...instrumentList].filter((instrument) =>
    instrument.type.includes("imag")
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

  const listmag = ["Vega", "AB"];

  const photoFormSchema = {
    type: "object",
    properties: {
      group_ids: {
        type: "array",
        items: {
          type: "number",
          enum: groups.map((group) => group.id),
          enumNames: groups.map((group) => group.name),
        },
        uniqueItems: true,
        title: "Share with Groups",
        default: [groups[0]?.id],
      },
      dateobs: {
        type: "string",
        title: "Observation date [i.e. YYYY-MM-DDThh:mm:ss]",
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
      // add a checkbox called 'coordinates' that is false by default
      // if it is checked, show the ra and dec fields
      coordinates: {
        type: "boolean",
        title: "Enter coordinates",
        default: false,
      },
      instrument_id: {
        type: "integer",
        oneOf: sortedInstrumentList.map((instrument) => ({
          enum: [instrument.id],
          // title is the instrument name: the list of filters comma separated
          title: `(${instrument.name}: ${instrument.filters})`,
        })),
        title: "Instrument",
      },
    },
    required: ["dateobs", "instrument_id", "magsys"],
    dependencies: {
      instrument_id: {
        oneOf: sortedInstrumentList.map((instrument) => ({
          properties: {
            instrument_id: {
              enum: [instrument.id],
            },
            filter: {
              type: "string",
              enum: instrument.filters,
              title: "Filter",
            },
          },
          required: ["filter"],
        })),
      },
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

  const validate = (formData, errors) => {
    if (formData.dateobs && !validateDate(formData.dateobs)) {
      errors.dateobs.addError("Date must be in the format YYYY-MM-DDThh:mm:ss");
    }
    if (formData.nb_exposure && formData.nb_exposure < 0) {
      errors.nb_exposure.addError("Number of exposures cannot be negative");
    }
    if (formData.exposure_time && formData.exposure_time < 0) {
      errors.exposure_time.addError("Exposure time cannot be negative");
    }
    if (formData.exposure_time && !formData.nb_exposure) {
      errors.nb_exposure.addError(
        "Please enter a number of exposures when entering an exposure time"
      );
    }
    if (formData.nb_exposure && !formData.exposure_time) {
      errors.exposure_time.addError(
        "Please enter an exposure time when entering a number of exposures"
      );
    }
    if (
      sortedInstrumentList.some(
        (instrument) =>
          instrument.id === formData.instrument_id &&
          instrument.filters.length === 0
      )
    ) {
      errors.instrument_id.addError("This instrument has no filters");
    }
    if (formData.instrument_id && !formData.filter) {
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
        "Please enter a valid RA and Dec when coordinates is checked"
      );
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
      instrument_id,
      filter,
      ra,
      dec,
    } = data.formData;
    const mjd = UTCToMJD(dateobs);
    const payload = {
      mjd,
      // 'ra': obj.ra,
      // 'dec': obj.dec,
      obj_id,
      magsys,
      instrument_id,
      filter,
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
    if (!Number.isNaN(nb_exposure) && !Number.isNaN(exposure_time)) {
      payload.altdata = { exposure: `${nb_exposure}x${exposure_time}` };
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
        <Form
          schema={photoFormSchema}
          validator={validator}
          onSubmit={submit}
          customValidate={validate}
          liveValidate
        />
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
