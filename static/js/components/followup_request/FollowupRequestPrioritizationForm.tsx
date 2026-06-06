import { useEffect, useState } from "react";

import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import CircularProgress from "@mui/material/CircularProgress";
import { makeStyles } from "tss-react/mui";
import { useAppSelector } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetFollowupRequestsQuery,
  usePrioritizeFollowupRequestsMutation,
} from "../../ducks/followup_requests";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";

const useStyles = makeStyles()(() => ({
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

interface FollowupRequestPrioritizationFormProps {
  fetchParams?: Record<string, any> | undefined;
}

const FollowupRequestPrioritizationForm = ({
  fetchParams,
}: FollowupRequestPrioritizationFormProps) => {
  const { classes } = useStyles();
  const { data: gcnEvents } = useGetGcnEventsQuery() as { data: any };

  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { instrumentList, instrumentFormParams } = useAppSelector(
    (state) => state["instruments"],
  ) as any;
  const [prioritizeFollowupRequests] = usePrioritizeFollowupRequestsMutation();
  const { data: followupRequestsData } =
    useGetFollowupRequestsQuery(fetchParams);
  const followupRequestList = followupRequestsData?.followup_requests;

  const [isSubmittingPrioritization, setIsSubmittingPrioritization] =
    useState(false);
  const [selectedGcnEventId, setSelectedGcnEventId] = useState<any>(null);
  const [selectedLocalizationId, setSelectedLocalizationId] =
    useState<any>(null);

  useEffect(() => {
    // Wait for the GCN Events to load before setting the new default form
    // fields, so that the allocations list can update.
    if (gcnEvents?.events?.[0]?.id) {
      setSelectedGcnEventId(gcnEvents.events[0].id);
    }
    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
  }, [gcnEvents, setSelectedGcnEventId]);

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
  sortedInstrumentList.sort((i1: any, i2: any) => {
    if (i1.name > i2.name) {
      return 1;
    }
    if (i2.name > i1.name) {
      return -1;
    }
    return 0;
  });

  const gcnEventsLookUp: Record<string, any> = {};

  gcnEvents?.events.forEach((gcnEvent: any) => {
    gcnEventsLookUp[gcnEvent.id] = gcnEvent;
  });

  const telLookUp: Record<string, any> = {};

  telescopeList?.forEach((tel: any) => {
    telLookUp[tel.id] = tel;
  });

  const requestsGroupedByInstId = followupRequestList.reduce(
    (r: Record<string, any[]>, a: any) => {
      r[a.allocation.instrument.id] = [
        ...(r[a.allocation.instrument.id] || []),
        a,
      ];
      return r;
    },
    {},
  );

  Object.values(requestsGroupedByInstId).forEach((value: any) => {
    value.sort();
  });

  const handleSelectedGcnEventChange = (e: any) => {
    setSelectedGcnEventId(e.target.value);
  };

  const handleSelectedLocalizationChange = (e: any) => {
    setSelectedLocalizationId(e.target.value);
  };

  const handleSubmitPrioritization = async ({
    formData,
  }: {
    formData: any;
  }) => {
    setIsSubmittingPrioritization(true);
    formData.gcnEventId = selectedGcnEventId;
    formData.localizationId = selectedLocalizationId;
    formData.requestIds = [];
    (requestsGroupedByInstId[formData.instrumentId] || []).forEach(
      (request: any) => {
        formData.requestIds.push(request.id);
      },
    );
    try {
      await prioritizeFollowupRequests(formData).unwrap();
    } catch {
      // error notification handled by the base query
    }
    setIsSubmittingPrioritization(false);
  };

  function validatePrioritization(formData: any, errors: any) {
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
        oneOf: sortedInstrumentList.map((instrument: any) => ({
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
      <div>
        <Form
          schema={FollowupRequestPrioritizationFormSchema as any}
          validator={validator}
          onSubmit={handleSubmitPrioritization as any}
          {...({ validate: validatePrioritization } as any)}
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
          {gcnEvents?.events.map((gcnEvent: any) => (
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
            (localization: any) => (
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
