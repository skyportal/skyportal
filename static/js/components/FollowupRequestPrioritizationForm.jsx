import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import Select from "@material-ui/core/Select";
import InputLabel from "@material-ui/core/InputLabel";
import MenuItem from "@material-ui/core/MenuItem";
import CircularProgress from "@material-ui/core/CircularProgress";
import { makeStyles } from "@material-ui/core/styles";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as followupRequestActions from "../ducks/followup_requests";
import * as instrumentActions from "../ducks/instruments";
import * as gcnEventsActions from "../ducks/gcnEvents";

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

const FollowupRequestPrioritizationForm = () => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const gcnEvents = useSelector((state) => state.gcnEvents);

  const { telescopeList } = useSelector((state) => state.telescopes);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { followupRequestList } = useSelector(
    (state) => state.followup_requests
  );

  const defaultStartDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  const defaultEndDate = dayjs()
    .add(1, "day")
    .utc()
    .format("YYYY-MM-DDTHH:mm:ssZ");

  const [isSubmittingPrioritization, setIsSubmittingPrioritization] =
    useState(false);
  const [selectedInstrumentId, setSelectedInstrumentId] = useState(null);
  const [selectedGcnEventId, setSelectedGcnEventId] = useState(null);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);

  useEffect(() => {
    const getInstruments = async () => {
      // Wait for the instruments to update before setting
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

  useEffect(() => {
    const getGcnEvents = async () => {
      // Wait for the GCN Events to update before setting
      // the new default form fields, so that the allocations list can
      // update

      const result = await dispatch(gcnEventsActions.fetchGcnEvents());
      const { data } = result;
      setSelectedGcnEventId(data[0]?.id);
    };
    getGcnEvents();

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, setSelectedGcnEventId]);

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    followupRequestList.length === 0 ||
    !selectedInstrumentId ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>No robotic followup requests for this source...</p>;
  }

  if (!selectedGcnEventId) {
    return <p>No GCN Events...</p>;
  }

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.forEach((gcnEvent) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  const telLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  telescopeList?.forEach((tel) => {
    telLookUp[tel.id] = tel;
  });

  const requestsGroupedByInstId = followupRequestList.reduce((r, a) => {
    r[a.allocation.instrument.id] = [
      ...(r[a.allocation.instrument.id] || []),
      a,
    ];
    return r;
  }, {});

  Object.values(requestsGroupedByInstId).forEach((value) => {
    value.sort();
  });

  const handleSelectedInstrumentChange = (e) => {
    setSelectedInstrumentId(e.target.value);
  };

  const handleSelectedGcnEventChange = (e) => {
    setSelectedGcnEventId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmitPrioritization = async ({ formData }) => {
    setIsSubmittingPrioritization(true);
    formData.gcnEventId = selectedGcnEventId;
    formData.localizationId = selectedLocalizationId;
    formData.instrumentId = selectedInstrumentId;
    formData.requestIds = [];
    requestsGroupedByInstId[selectedInstrumentId].forEach((request) => {
      formData.requestIds.push(request.id);
    });
    console.log("formData", formData);
    await dispatch(followupRequestActions.prioritizeFollowupRequests(formData));
    setIsSubmittingPrioritization(false);
  };

  function validatePrioritization(formData, errors) {
    if (formData.observationStartDate > formData.observationEndDate) {
      errors.observationStartDate.addError(
        "Start date must be before end date, please fix."
      );
    }
    return errors;
  }

  const FollowupRequestPrioritizationFormSchema = {
    type: "object",
    properties: {
      observationStartDate: {
        type: "string",
        format: "date-time",
        title: "Observation Start Date (Local Time)",
        default: defaultStartDate,
      },
      observationEndDate: {
        type: "string",
        format: "date-time",
        title: "Observation End Date (Local Time)",
        default: defaultEndDate,
      },
      minimumPriority: {
        type: "number",
        default: 1.0,
        title: "Minimum Priority",
      },
      maximumPriority: {
        type: "number",
        default: 5.0,
        title: "Maximum Priority",
      },
    },
  };

  return (
    <div>
      <div>
        <InputLabel id="gcnEventSelectLabel">GCN Event</InputLabel>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="gcnEventSelectLabel"
          value={selectedGcnEventId}
          onChange={handleSelectedGcnEventChange}
          name="followupRequestGcnEventSelect"
          className={classes.select}
        >
          {gcnEvents?.map((gcnEvent) => (
            <MenuItem
              value={gcnEvent.id}
              key={gcnEvent.id}
              className={classes.selectItem}
            >
              {`${gcnEvent.dateobs}`}
            </MenuItem>
          ))}
        </Select>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="localizationSelectLabel"
          value={selectedLocalizationId || ""}
          onChange={handleSelectedLocalizationChange}
          name="observationPlanRequestLocalizationSelect"
          className={classes.localizationSelect}
        >
          {gcnEventsLookUp[selectedGcnEventId].localizations?.map(
            (localization) => (
              <MenuItem
                value={localization.id}
                key={localization.id}
                className={classes.localizationSelectItem}
              >
                {`${localization.localization_name}`}
              </MenuItem>
            )
          )}
        </Select>
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
      </div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={FollowupRequestPrioritizationFormSchema}
          onSubmit={handleSubmitPrioritization}
          // eslint-disable-next-line react/jsx-no-bind
          validate={validatePrioritization}
          disabled={isSubmittingPrioritization}
          liveValidate
        />
        {isSubmittingPrioritization && (
          <div>
            <CircularProgress />
          </div>
        )}
      </div>
    </div>
  );
};

export default FollowupRequestPrioritizationForm;
