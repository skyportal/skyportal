import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import makeStyles from "@mui/styles/makeStyles";

import * as followupRequestActions from "../../ducks/followup_requests";
import * as gcnEventsActions from "../../ducks/gcnEvents";

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
    (state) => state.instruments,
  );
  const { followupRequestList } = useSelector(
    (state) => state.followup_requests,
  );

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
      setSelectedGcnEventId(data?.events[0]?.id);
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

  const sortedInstrumentList = [...instrumentList];
  sortedInstrumentList.sort((i1, i2) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const gcnEventsLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  gcnEvents?.events.forEach((gcnEvent) => {
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
        "Start date must be before end date, please fix.",
      );
    }
    if (!requestsGroupedByInstId[formData.instrumentId]) {
      errors.instrumentId.addError(
        "This instrument does not have any requests, please fix.",
      );
    }
    return errors;
  }

  const FollowupRequestPrioritizationFormSchema = {
    type: "object",
    properties: {
      priorityType: {
        type: "string",
        oneOf: [
          { enum: ["localization"], title: "Localization" },
          { enum: ["magnitude"], title: "Magnitude" },
        ],
        default: "magnitude",
        title: "Prioritization",
      },
      instrumentId: {
        type: "integer",
        oneOf: sortedInstrumentList.map((instrument) => ({
          enum: [instrument.id],
          title: `${instrument.name} / ${
            telLookUp[instrument.telescope_id].name
          }`,
        })),
        title: "Instrument",
        default: instrumentList[0]?.id,
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
    dependencies: {
      priorityType: {
        oneOf: [
          {
            properties: {
              priorityType: {
                enum: ["magnitude"],
              },
              magnitudeOrdering: {
                type: "string",
                oneOf: [
                  { enum: ["ascending"], title: "Ascending (brightest first)" },
                  {
                    enum: ["descending"],
                    title: "Descending (faintest first)",
                  },
                ],
                default: "ascending",
                title: "Magnitude ordering",
              },
            },
          },
        ],
      },
    },
  };

  return (
    <div>
      <div data-testid="gcnsource-selection-form">
        <Form
          schema={FollowupRequestPrioritizationFormSchema}
          validator={validator}
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
          {gcnEvents?.events.map((gcnEvent) => (
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
          className={classes.select}
        >
          {gcnEventsLookUp[selectedGcnEventId]?.localizations?.map(
            (localization) => (
              <MenuItem
                value={localization.id}
                key={localization.id}
                className={classes.selectItem}
              >
                {`${localization.localization_name}`}
              </MenuItem>
            ),
          )}
        </Select>
      </div>
    </div>
  );
};

export default FollowupRequestPrioritizationForm;
