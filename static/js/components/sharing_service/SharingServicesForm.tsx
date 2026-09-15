import { useGetProfileQuery } from "../../ducks/profile";
import { useEffect, useState } from "react";
import validator from "@rjsf/validator-ajv8";
import { withTheme } from "@rjsf/core";

import BugReportIcon from "@mui/icons-material/BugReport";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import Typography from "@mui/material/Typography";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import FormControl from "@mui/material/FormControl";
import FormHelperText from "@mui/material/FormHelperText";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import FormValidationError from "../FormValidationError";

import { useAppDispatch } from "../../types/hooks";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import {
  useAddSharingServiceSubmissionMutation,
  useGetSharingServicesQuery,
} from "../../ducks/sharingServices";
import { useGetStreamsQuery } from "../../ducks/streams";
import { useGetConfigQuery } from "../../ducks/config";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { CustomCheckboxWidgetMuiTheme } from "../CustomCheckboxWidget";
import { userLabel } from "../../utils/format";
import { useGetUsersQuery } from "../../ducks/users";

const Form = withTheme(CustomCheckboxWidgetMuiTheme as any);

interface SharingServicesDialogProps {
  obj_id: string;
  dialogOpen: boolean;
  setDialogOpen: (...a: any[]) => void;
}

const SharingServicesDialog = ({
  obj_id,
  dialogOpen,
  setDialogOpen,
}: SharingServicesDialogProps) => {
  const dispatch = useAppDispatch();
  const [addSharingServiceSubmission] =
    useAddSharingServiceSubmissionMutation();
  // Skipped until the dialog opens: the response is the whole user table.
  const allUsers =
    useGetUsersQuery(undefined, { skip: !dialogOpen }).data?.users ?? [];
  const { data: currentUser } = useGetProfileQuery();
  const { data: streams = [] } = useGetStreamsQuery();
  const allowedInstrumentsForSharing = useGetConfigQuery().data?.[
    "allowedInstrumentsForSharing"
  ] as string[] | undefined;
  const isNoAffiliation = !currentUser?.affiliations?.length;

  const { data: sharingServicesList = [], isLoading: loading } =
    useGetSharingServicesQuery() as { data: any[]; isLoading: boolean };
  const [selectedSharingServiceId, setSelectedSharingServiceId] =
    useState<any>(null);
  const [sendToTNS, setSendToTNS] = useState(false);
  const [sendToHermes, setSendToHermes] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: telescopeList = [] } = useGetTelescopesQuery();

  const selectedSharingService = sharingServicesList?.find(
    (b: any) => b.id === selectedSharingServiceId,
  );
  const allowedInstruments = selectedSharingService?.instruments
    ? instrumentList.filter(
        (instrument: any) =>
          selectedSharingService.instruments.some(
            (i: any) => i.id === instrument.id,
          ) &&
          (allowedInstrumentsForSharing || []).includes(
            instrument.name?.toLowerCase(),
          ),
      )
    : [];
  const allowedInstrumentIds = allowedInstruments.map(
    (instrument: any) => instrument.id,
  );

  const defaultStreams = streams
    .filter((stream: any) =>
      (selectedSharingService?.streams || []).some(
        (s: any) => s.id === stream.id,
      ),
    )
    .sort((a: any, b: any) => a.id - b.id);
  const defaultStreamIds = defaultStreams.map((stream: any) => stream.id);

  const defaultArchivalComment = `No non-detections prior to first detection${
    defaultStreams.length
      ? ` in ${defaultStreams
          .map((stream: any) => stream.name)
          .join(", ")} alert stream${defaultStreams.length > 1 ? "s" : ""}`
      : ""
  }`;

  const coauthorsString = (selectedSharingService?.coauthors || [])
    .filter((coauthor: any) => coauthor.user_id !== currentUser?.id)
    .map((coauthor: any) =>
      userLabel(
        allUsers.find((user: any) => user.id === coauthor.user_id),
        false,
        true,
      ),
    )
    .join(", ");

  const defaultSharersString =
    currentUser && allUsers.length > 0
      ? `${userLabel(currentUser, false, true)}${
          coauthorsString ? `, ${coauthorsString}` : ""
        } ${
          selectedSharingService?.acknowledgments || "on the behalf of ..."
        }`.replace(/\s+/g, " ")
      : null;

  useEffect(() => {
    if (!selectedSharingServiceId && sharingServicesList.length) {
      setSelectedSharingServiceId(sharingServicesList[0]?.id);
    }
  }, [sharingServicesList, selectedSharingServiceId]);

  useEffect(() => {
    setSendToTNS(
      Boolean(selectedSharingService?.enable_sharing_with_tns) &&
        !isNoAffiliation,
    );
    setSendToHermes(
      Boolean(selectedSharingService?.enable_sharing_with_hermes),
    );
  }, [selectedSharingServiceId, selectedSharingService, isNoAffiliation]);

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setSubmitting(true);
    const { first_and_last_detections, remarks, ...rest } = formData;
    const result = await addSharingServiceSubmission({
      ...rest,
      ...(remarks && { remarks }),
      obj_id,
      sharing_service_id: selectedSharingServiceId,
      photometry_options: { first_and_last_detections },
      publish_to_tns: sendToTNS,
      publish_to_hermes: sendToHermes,
    });
    if (!("error" in result)) {
      dispatch(showNotification("Successfully queued for submission."));
    }
    setSubmitting(false);
    setDialogOpen(false);
  };

  const formSchema: any = {
    type: "object",
    properties: {
      publishers: {
        type: "string",
        title: "Publishers",
        default: defaultSharersString,
      },
      instrument_ids: {
        type: "array",
        items: {
          type: "integer",
          enum: allowedInstrumentIds,
        },
        uniqueItems: true,
        default: allowedInstrumentIds,
        title: "Instrument(s)",
      },
      stream_ids: {
        type: "array",
        items: {
          type: "integer",
          enum: streams.map((stream: any) => stream.id),
        },
        uniqueItems: true,
        default: defaultStreamIds,
        title: "Streams (optional)",
      },
      remarks: {
        type: "string",
        title: "Remark (optional)",
        default: "",
        description: "Any additional remarks to include. Optional",
      },
      first_and_last_detections: {
        type: "boolean",
        title: "Mandatory first and last detection",
        default:
          selectedSharingService?.photometry_options
            ?.first_and_last_detections ?? true,
        description:
          "If enabled, the sharing service will not publish the data if there is no first and last detection (at least 2 detections).",
      },
      ...(sendToTNS && {
        archival: {
          type: "boolean",
          title: "TNS Archival",
          description:
            "TNS require non-detections by default. However, reports can be sent as 'archival', excluding non-detections and requiring a comment. You can use this option after a normal report failed because non-detections were missing.",
          default: false,
        },
      }),
    },
    dependencies: {
      archival: {
        oneOf: [
          {
            properties: {
              archival: {
                enum: [false],
              },
            },
          },
          {
            properties: {
              archival: {
                enum: [true],
              },
              archival_comment: {
                type: "string",
                title: "Archival Comment",
                default: defaultArchivalComment,
              },
            },
            required: ["archival_comment"],
          },
        ],
      },
    },
    required: ["publishers", "instrument_ids"],
  };

  const uiSchema: any = {
    instrument_ids: {
      "ui:enumNames": allowedInstruments.map(
        (instrument: any) =>
          `${
            telescopeList.find(
              (telescope: any) => telescope.id === instrument.telescope_id,
            )?.["name"]
          } / ${instrument.name}`,
      ),
    },
    stream_ids: {
      "ui:enumNames": streams.map((stream: any) => stream.name),
    },
  };

  const validate = (formData: any, errors: any) => {
    if (!sendToTNS && !sendToHermes) {
      errors.__errors.push(
        "Please select at least one destination (TNS or Hermes)",
      );
    }
    const publishers = formData.publishers ?? "";
    if (!publishers.trim()) {
      errors.publishers.addError(
        "Please specify the group you are publishing on behalf of",
      );
    }
    if (publishers === "on behalf of...") {
      errors.publishers.addError(
        "Please edit the publishers field before submitting",
      );
    }
    if (
      publishers.includes("on behalf of") &&
      !/on behalf of\s*[a-zA-Z]+/i.test(publishers)
    ) {
      errors.publishers.addError(
        "Please specify the group you are publishing on behalf of",
      );
    }
    if (formData.archival === true && !formData.archival_comment) {
      errors.archival.addError(
        "Archival comment must be defined if archival is true",
      );
    }
    return errors;
  };

  const sharingServiceForm = () => {
    if (!sharingServicesList?.length || !selectedSharingServiceId) return null;
    if (!defaultSharersString) {
      return (
        <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (!allowedInstruments.length) {
      return (
        <FormValidationError message="This sharing service has no allowed instruments, edit it before submitting" />
      );
    }

    return (
      <Form
        key={selectedSharingServiceId}
        schema={formSchema}
        uiSchema={uiSchema}
        validator={validator as any}
        onSubmit={handleSubmit as any}
        disabled={submitting}
        customValidate={validate}
      />
    );
  };

  return (
    <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          Send to
          <Tooltip
            title={
              isNoAffiliation && (
                <h3>
                  Warning: You have no affiliation(s), you should set your
                  affiliation(s) in your profile before submitting to TNS
                </h3>
              )
            }
          >
            <div>
              <Chip
                label="TNS"
                clickable
                onClick={() => setSendToTNS(!sendToTNS)}
                color={sendToTNS ? "primary" : "default"}
                variant={sendToTNS ? "filled" : "outlined"}
                disabled={
                  isNoAffiliation ||
                  !selectedSharingService?.enable_sharing_with_tns
                }
              />
            </div>
          </Tooltip>
          <Tooltip
            title={
              <h3>
                HERMES is a Message Exchange Service for Multi-Messenger
                Astronomy. Click{" "}
                <a
                  href="https://hermes.lco.global/about"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  here
                </a>{" "}
                for more information.
              </h3>
            }
          >
            <Chip
              label="Hermes"
              clickable
              onClick={() => setSendToHermes(!sendToHermes)}
              color={sendToHermes ? "primary" : "default"}
              variant={sendToHermes ? "filled" : "outlined"}
              disabled={!selectedSharingService?.enable_sharing_with_hermes}
            />
          </Tooltip>
        </Box>
      </DialogTitle>
      <DialogContent>
        <FormControl
          sx={{ mt: 1 }}
          fullWidth
          required
          error={!sharingServicesList?.length && !loading}
        >
          <InputLabel id="sharingServiceSelectLabel">
            Sharing Service
          </InputLabel>
          <Select
            inputProps={{ MenuProps: { disableScrollLock: true } }}
            labelId="sharingServiceSelectLabel"
            label="Sharing Service"
            value={selectedSharingServiceId || ""}
            onChange={(e) => setSelectedSharingServiceId(e.target.value)}
          >
            {sharingServicesList?.map((sharingService: any) => (
              <MenuItem value={sharingService.id} key={sharingService.id}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  {sharingService.testing === true && (
                    <Tooltip
                      title={
                        <h3>
                          This Sharing Service is currently in testing mode. It
                          will not publish any data to TNS but will store the
                          payload in the database instead (useful for debugging
                          purposes). For Hermes, it will publish to the test
                          topic. You can remove it from the sharing services
                          page.
                        </h3>
                      }
                      placement="right"
                    >
                      <BugReportIcon sx={{ color: "orange" }} />
                    </Tooltip>
                  )}
                  <Typography variant="body1">{sharingService.name}</Typography>
                </Box>
              </MenuItem>
            ))}
          </Select>
          {!sharingServicesList?.length && !loading && (
            <FormHelperText>No sharing service available.</FormHelperText>
          )}
        </FormControl>
        {sharingServiceForm()}
      </DialogContent>
    </Dialog>
  );
};

export default SharingServicesDialog;
