import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { showNotification } from "baselayer/components/Notifications";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/material-ui/v5";

import { submitPhotometry } from "../ducks/photometry";

const validateDate = (date) => {
  // use a regex to check if the date is written as YYYY-MM-DDThh:mm:ss
  const regex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/;
  return regex.test(date);
};

const validateExposure = (exposure) => {
  // use a regex to check if the exposure is written as Numbers x Numbers s
  const regex = /^\d+x\d+s$/;
  return regex.test(exposure);
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
      exposure: {
        type: "string",
        title: "Exposure [i.e. 60x60s ou 1x300s]",
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
    required: ["dateobs", "instrument_id"],
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
    },
  };

  const validate = (formData, errors) => {
    if (formData.dateobs && !validateDate(formData.dateobs)) {
      errors.dateobs.addError("Date must be in the format YYYY-MM-DDThh:mm:ss");
    }
    if (formData.exposure && !validateExposure(formData.exposure)) {
      errors.exposure.addError(
        "Exposure must be in the format 60x60s ou 1x300s"
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
    // if there are no mag and not limiting mag, add an error
    if (!formData.mag && !formData.limiting_mag) {
      errors.mag.addError("Please enter a magnitude or a limiting magnitude");
    }
    // if there is a mag or limiting mag, but no magerr, add an error
    if ((formData.mag || formData.limiting_mag) && !formData.magerr) {
      errors.magerr.addError("Please enter a magnitude error");
    }
    // if the mag, magerr or limiting_mag are all not numbers, add an error
    if (formData.mag && Number.isNaN(formData.mag)) {
      errors.mag.addError("Magnitude must be a number");
    }
    if (formData.magerr && Number.isNaN(formData.magerr)) {
      errors.magerr.addError("Magnitude error must be a number");
    }
    if (formData.limiting_mag && Number.isNaN(formData.limiting_mag)) {
      errors.magerr.addError("Limiting magnitude must be a number");
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
      exposure,
      instrument_id,
      filter,
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
    if (exposure) {
      payload.altdata = { exposure };
    }
    if (group_ids) {
      payload.group_ids = group_ids;
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
          onSubmit={submit}
          validate={validate}
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
