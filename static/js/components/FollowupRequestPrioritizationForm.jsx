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
  const [selectedGcnEventId, setSelectedGcnEventId] = useState(null);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState(null);

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

  if (!Array.isArray(followupRequestList)) {
    return <p>Waiting for followup requests to load...</p>;
  }

  if (
    instrumentList.length === 0 ||
    telescopeList.length === 0 ||
    followupRequestList.length === 0 ||
    Object.keys(instrumentFormParams).length === 0
  ) {
    return <p>No robotic followup requests found...</p>;
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
    formData.requestIds = [];
    requestsGroupedByInstId[formData.instrumentId].forEach((request) => {
      formData.requestIds.push(request.id);
    });
    await dispatch(followupRequestActions.prioritizeFollowupRequests(formData));
    setIsSubmittingPrioritization(false);
  };

  function validatePrioritization(formData, errors) {
    if (formData.observationStartDate > formData.observationEndDate) {
      errors.observationStartDate.addError(
        "Start date must be before end date, please fix."
      );
    }
    if (!requestsGroupedByInstId[formData.instrumentId]) {
      errors.instrumentId.addError(
        "This instrument does not have any requests, please fix."
      );
    }
    return errors;
  }

  const FollowupRequestPrioritizationFormSchema = {
    type: "object",
    properties: {
      instrumentId: {
        type: "integer",
        oneOf: instrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${instrument.name} / ${
            telLookUp[instrument.telescope_id].name
          }`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
      },
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
