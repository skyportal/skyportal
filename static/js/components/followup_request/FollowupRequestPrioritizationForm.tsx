import { useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useGetFollowupRequestsQuery,
  usePrioritizeFollowupRequestsMutation,
} from "../../ducks/followup_requests";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";
import {
  useGetInstrumentFormsQuery,
  useGetInstrumentsQuery,
} from "../../ducks/instruments";

interface FollowupRequestPrioritizationFormProps {
  fetchParams?: Record<string, any>;
}

const FollowupRequestPrioritizationForm = ({
  fetchParams,
}: FollowupRequestPrioritizationFormProps) => {
  const { data: gcnEvents }: any = useGetGcnEventsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  const [prioritizeFollowupRequests] = usePrioritizeFollowupRequestsMutation();
  const followupRequestList =
    useGetFollowupRequestsQuery(fetchParams).data?.followup_requests;
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [selectedGcnEventId, setSelectedGcnEventId] = useState<any>(null);
  const [selectedLocalizationId, setSelectedLocalizationId] = useState("");

  const gcnEventId = selectedGcnEventId ?? gcnEvents?.events?.[0]?.id;

  if (!Array.isArray(followupRequestList)) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Waiting for followup requests to load...
      </Typography>
    );
  }
  if (
    !instrumentList.length ||
    !telescopeList.length ||
    !Object.keys(instrumentFormParams).length
  ) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No instruments or telescopes found...
      </Typography>
    );
  }
  if (!followupRequestList.length) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No robotic followup requests fetched...
      </Typography>
    );
  }
  if (!gcnEventId)
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No GCN Events...
      </Typography>
    );

  const requestIdsOf = (instrumentId: number) =>
    followupRequestList
      .filter(
        (request: any) => request.allocation.instrument.id === instrumentId,
      )
      .map((request: any) => request.id);

  const handleSubmit = async ({ formData }: { formData?: any }) => {
    setIsSubmitting(true);
    await prioritizeFollowupRequests({
      ...formData,
      gcnEventId,
      localizationId: selectedLocalizationId || null,
      requestIds: requestIdsOf(formData.instrumentId),
    });
    setIsSubmitting(false);
  };

  const schema: any = {
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
        oneOf: [...instrumentList]
          .sort((a, b) => a.name.localeCompare(b.name))
          .map((instrument) => ({
            enum: [instrument.id],
            title: `${instrument.name} / ${
              telescopeList.find(
                ({ id }: any) => id === instrument.telescope_id,
              )?.name
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
              priorityType: { enum: ["magnitude"] },
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
    <>
      <Form
        schema={schema}
        validator={validator}
        onSubmit={handleSubmit}
        disabled={isSubmitting}
        liveValidate
      />
      {isSubmitting && <CircularProgress />}
      <InputLabel id="gcnEventSelectLabel">GCN Event</InputLabel>
      <Box sx={{ display: "flex", gap: 1 }}>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="gcnEventSelectLabel"
          value={gcnEventId}
          onChange={(e) => setSelectedGcnEventId(e.target.value)}
          name="followupRequestGcnEventSelect"
          sx={{ width: "25%" }}
        >
          {gcnEvents.events.map((gcnEvent: any) => (
            <MenuItem value={gcnEvent.id} key={gcnEvent.id}>
              {gcnEvent.dateobs}
            </MenuItem>
          ))}
        </Select>
        <Select
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          labelId="localizationSelectLabel"
          value={selectedLocalizationId}
          onChange={(e) => setSelectedLocalizationId(e.target.value)}
          name="observationPlanRequestLocalizationSelect"
          sx={{ width: "25%" }}
        >
          {gcnEvents.events
            .find(({ id }: any) => id === gcnEventId)
            ?.localizations?.map((localization: any) => (
              <MenuItem value={localization.id} key={localization.id}>
                {localization.localization_name}
              </MenuItem>
            ))}
        </Select>
      </Box>
    </>
  );
};

export default FollowupRequestPrioritizationForm;
