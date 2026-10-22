import { useState } from "react";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { usePrioritizeFollowupRequestsMutation } from "../../ducks/followup_requests";
import { useGetGcnEventsQuery } from "../../ducks/gcnEvents";
import Button from "../Button";

interface FollowupPrioritizationDialogProps {
  open: boolean;
  onClose: () => void;
  followupRequests: any[];
}

const FollowupPrioritizationDialog = ({
  open,
  onClose,
  followupRequests,
}: FollowupPrioritizationDialogProps) => {
  const { data: gcnEvents }: any = useGetGcnEventsQuery();
  const [prioritizeFollowupRequests, { isLoading }] =
    usePrioritizeFollowupRequestsMutation();
  const [formData, setFormData] = useState<any>({});
  const [gcnEventId, setGcnEventId] = useState<any>("");
  const [localizationId, setLocalizationId] = useState<any>("");

  const instruments = [
    ...new Map(
      followupRequests.map(({ allocation }) => [
        allocation.instrument.id,
        allocation.instrument,
      ]),
    ).values(),
  ];
  const localizations =
    gcnEvents?.events?.find(({ id }: any) => id === gcnEventId)
      ?.localizations ?? [];

  const handleSubmit = async ({ formData: data }: { formData?: any }) => {
    await prioritizeFollowupRequests({
      ...data,
      localizationId: localizationId || null,
      requestIds: followupRequests
        .filter(
          ({ allocation }) => allocation.instrument.id === data.instrumentId,
        )
        .map(({ id }) => id),
    });
    onClose();
  };

  const schema: any = {
    type: "object",
    properties: {
      priorityType: {
        type: "string",
        oneOf: [
          { enum: ["magnitude"], title: "Magnitude" },
          { enum: ["localization"], title: "Localization" },
        ],
        default: "magnitude",
        title: "Prioritization",
      },
      instrumentId: {
        type: "integer",
        oneOf: instruments.map((instrument) => ({
          enum: [instrument.id],
          title: instrument.name,
        })),
        title: "Instrument",
        default: instruments[0]?.id,
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
          { properties: { priorityType: { enum: ["localization"] } } },
        ],
      },
    },
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Prioritize Follow-up Requests</DialogTitle>
      <DialogContent>
        {instruments.length ? (
          <>
            <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
              Applies to the requests currently listed for the selected
              instrument.
            </Typography>
            <Form
              schema={schema}
              formData={formData}
              onChange={({ formData: data }) => setFormData(data)}
              validator={validator}
              onSubmit={handleSubmit}
              disabled={isLoading}
            >
              {formData.priorityType === "localization" && (
                <Box sx={{ display: "flex", gap: 2, mb: 2 }}>
                  <TextField
                    select
                    label="GCN Event"
                    value={gcnEventId}
                    onChange={(e) => {
                      setGcnEventId(e.target.value);
                      setLocalizationId("");
                    }}
                    sx={{ flex: 1 }}
                  >
                    {gcnEvents?.events?.map((gcnEvent: any) => (
                      <MenuItem value={gcnEvent.id} key={gcnEvent.id}>
                        {gcnEvent.dateobs}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    select
                    label="Localization"
                    value={localizationId}
                    onChange={(e) => setLocalizationId(e.target.value)}
                    disabled={!localizations.length}
                    sx={{ flex: 1 }}
                  >
                    {localizations.map((localization: any) => (
                      <MenuItem value={localization.id} key={localization.id}>
                        {localization.localization_name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Box>
              )}
              <Button primary type="submit" disabled={isLoading}>
                Prioritize
              </Button>
            </Form>
          </>
        ) : (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No follow-up requests to prioritize.
          </Typography>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default FollowupPrioritizationDialog;
