import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { PropTypes } from "prop-types";
import Button from "@material-ui/core/Button";
import Form from "@rjsf/material-ui";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import { filterOutEmptyValues } from "../API";
import { fetchGcnEventSources } from "../ducks/sources";
import { fetchGcnEventObservations } from "../ducks/observations";
import { fetchGcnEventGalaxies } from "../ducks/galaxies";
import * as instrumentActions from "../ducks/instruments";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles(() => ({
  select: {
    width: "25%",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
  selectItem: {
    whiteSpace: "break-spaces",
  },
}));

const GcnSelectionForm = ({ gcnEvent }) => {
  const classes = useStyles();
  const dispatch = useDispatch();

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList } = useSelector((state) => state.instruments);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const defaultStartDate = dayjs(gcnEvent.dateobs).format(
    "YYYY-MM-DDTHH:mm:ssZ"
  );
  const defaultEndDate = dayjs(gcnEvent.dateobs)
    .add(7, "day")
    .format("YYYY-MM-DDTHH:mm:ssZ");
  const [formDataState, setFormDataState] = useState({
    observationStartDate: defaultStartDate,
    observationEndDate: defaultEndDate,
  });

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the allocations to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(instrumentActions.fetchInstruments());

      const { data } = result;
      setSelectedInstrumentId(data[0]?.id);
    };

    getInstruments();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedInstrumentId]);

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    !selectedInstrumentId
  ) {
    return <p>No robotic followup requests for this source...</p>;
  }

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  function createUrl(instrumentId, queryParams) {
    let url = `/api/observation/gcn/${instrumentId}`;
    if (queryParams) {
      const filteredQueryParams = filterOutEmptyValues(queryParams);
      const queryString = new URLSearchParams(filteredQueryParams).toString();
      url += `?${queryString}`;
    }
    return url;
  }

  const handleSubmit = async ({ formData }) => {
    setIsSubmitting(true);
    formData.startDate = formData.startDate.replace("+00:00", "");
    formData.endDate = formData.endDate.replace("+00:00", "");
    await dispatch(fetchGcnEventSources(gcnEvent.dateobs, formData));
    await dispatch(fetchGcnEventObservations(gcnEvent.dateobs, formData));
    await dispatch(fetchGcnEventGalaxies(gcnEvent.dateobs, formData));
    setFormDataState(formData);
    setIsSubmitting(false);
  };

  function validate(formData, errors) {
    if (formData.start_date > formData.end_date) {
      errors.start_date.addError(
        "Start date must be before end date, please fix."
      );
    }
    if (
      formData.localizationCumprob < 0 ||
      formData.localizationCumprob > 1.01
    ) {
      errors.cumulative.addError(
        "Value of cumulative should be between 0 and 1"
      );
    }
    return errors;
  }

  const url = createUrl(selectedInstrumentId, formDataState);
  const GcnSourceSelectionFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
        default: defaultEndDate,
      },
      localizationCumprob: {
        type: "number",
        title: "Cumulative Probability",
        default: 0.95,
      },
      localizationName: {
        type: "string",
        title: "Localization Date Obs.",
        oneOf: gcnEvent.localizations?.map((localization) => ({
          enum: [localization?.localization_name],
          title: `${localization.localization_name}`,
        })),
      },
    },
    required: [
      "startDate",
      "endDate",
      "localizationCumprob",
      "localizationName",
    ],
  };

  return (
    <div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={GcnSourceSelectionFormSchema}
          onSubmit={handleSubmit}
          // eslint-disable-next-line react/jsx-no-bind
          validate={validate}
          disabled={isSubmitting}
          liveValidate
        />
        {isSubmitting && (
          <div>
            <CircularProgress />
          </div>
        )}
      </div>
      <div>
        <InputLabel id="instrumentSelectLabel">Instrument</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="instrumentSelectLabel"
          value={selectedInstrumentId}
          onChange={handleSelectedInstrumentChange}
          name="followupRequestInstrumentSelect"
          className={classes.select}
        >
          {instrumentList?.map((instrument) => (
            <MenuItem
              value={instrument.id}
              key={instrument.id}
              className={classes.selectItem}
            >
              {`${telLookUp[instrument.telescope_id].name} / ${
                instrument.name
              }`}
            </MenuItem>
          ))}
        </Select>
        <Button
          href={`${url}`}
          download={`observationGcn-${selectedInstrumentId}`}
          size="small"
          color="primary"
          type="submit"
          variant="outlined"
          data-testid={`observationGcn_${selectedInstrumentId}`}
        >
          GCN
        </Button>
      </div>
    </div>
  );
};

GcnSelectionForm.propTypes = {
  gcnEvent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
};
export default GcnSelectionForm;
