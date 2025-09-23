import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import validator from "@rjsf/validator-ajv8";
import { withTheme } from "@rjsf/core";

import makeStyles from "@mui/styles/makeStyles";
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

import { showNotification } from "baselayer/components/Notifications";
import Spinner from "../Spinner";
import FormValidationError from "../FormValidationError";

import * as sharingServicesActions from "../../ducks/sharingServices";
import * as streamsActions from "../../ducks/streams";
import { CustomCheckboxWidgetMuiTheme } from "../CustomCheckboxWidget";
import { userLabel } from "../../utils/format";

const Form = withTheme(CustomCheckboxWidgetMuiTheme);

const useStyles = makeStyles(() => ({
  sharingServiceSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    margin: "1rem 0",
  },
}));

const SharingServicesDialog = ({ obj_id, dialogOpen, setDialogOpen }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);
  const currentUser = useSelector((state) => state.profile);
  const streams = useSelector((state) => state.streams);
  const allowedInstrumentsForSharing = useSelector(
    (state) => state.config.allowedInstrumentsForSharing,
  );
  const isNoAffiliation = !currentUser?.affiliations?.length;

  const { sharingServicesList, loading } = useSelector(
    (state) => state.sharingServices,
  );
  const [selectedSharingServiceId, setselectedSharingServiceId] =
    useState(null);
  const [defaultSharersString, setdefaultSharersString] = useState(null);
  const [defaultArchivalComment, setDefaultArchivalComment] = useState(null);
  const [defaultInstrumentIds, setDefaultInstrumentIds] = useState([]);
  const [defaultStreamIds, setDefaultStreamIds] = useState([]);
  const [sendToTNS, setSendToTNS] = useState(false);
  const [sendToHermes, setSendToHermes] = useState(false);
  // request in process
  const [SharingRequestInProcess, setSharingRequestInProcess] = useState(false);
  const [dataFetched, setDataFetched] = useState(false);

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const selectedSharingService = sharingServicesList?.find(
    (b) => b.id === selectedSharingServiceId,
  );
  const allowedInstruments = selectedSharingService?.instruments
    ? instrumentList.filter((instrument) =>
        selectedSharingService.instruments.some((i) => i.id === instrument.id),
      )
    : [];

  instrumentList.filter((instrument) =>
    (allowedInstrumentsForSharing || []).includes(
      instrument.name?.toLowerCase(),
    ),
  );

  useEffect(() => {
    const getSharingServices = async () => {
      const result = await dispatch(
        sharingServicesActions.fetchSharingServices(),
      );
      const { data } = result;
      setselectedSharingServiceId(data[0]?.id);
    };
    if (!sharingServicesList) {
      getSharingServices();
    } else if (sharingServicesList?.length > 0 && !selectedSharingServiceId) {
      setselectedSharingServiceId(sharingServicesList[0]?.id);
    }
  }, [dispatch, sharingServicesList, selectedSharingServiceId]);

  useEffect(() => {
    const fetchData = () => {
      dispatch(streamsActions.fetchStreams());
    };
    if (!dataFetched && !streams?.length) {
      fetchData();
      setDataFetched(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataFetched, dispatch]);

  useEffect(() => {
    if (
      sharingServicesList?.length > 0 &&
      selectedSharingServiceId &&
      currentUser &&
      allUsers?.length > 0
    ) {
      const coauthors = (selectedSharingService?.coauthors || []).filter(
        (coauthor) => coauthor.user_id !== currentUser.id,
      );
      const authorString = userLabel(currentUser, false, true);
      const coauthorsString = coauthors
        .map((coauthor) =>
          userLabel(
            allUsers.find((user) => user.id === coauthor.user_id),
            false,
            true,
          ),
        )
        .join(", ");
      const acknowledgments =
        selectedSharingService?.acknowledgments || "on the behalf of ...";

      const finalString = `${authorString}${
        coauthorsString ? `, ${coauthorsString}` : ""
      } ${acknowledgments}`.replace(/\s+/g, " ");

      setdefaultSharersString(finalString);
    }
  }, [sharingServicesList, selectedSharingServiceId, currentUser, allUsers]);

  useEffect(() => {
    if (
      !sharingServicesList?.length ||
      !selectedSharingServiceId ||
      !selectedSharingService
    )
      return;
    let archivalComment = "No non-detections prior to first detection";

    // Set publish to
    if (sendToTNS !== selectedSharingService.enable_sharing_with_tns) {
      setSendToTNS(
        selectedSharingService.enable_sharing_with_tns && !isNoAffiliation,
      );
    }
    if (sendToHermes !== selectedSharingService.enable_sharing_with_hermes) {
      setSendToHermes(selectedSharingService.enable_sharing_with_hermes);
    }

    // Set instruments
    if (instrumentList?.length && selectedSharingService.instruments?.length) {
      const instrumentIds = selectedSharingService.instruments.map((i) => i.id);
      setDefaultInstrumentIds(instrumentIds);
    }

    // Set streams
    if (streams?.length && selectedSharingService.streams?.length) {
      const streamIds = selectedSharingService.streams
        .map((s) => s.id)
        .sort((a, b) => a - b);

      setDefaultStreamIds(streamIds);

      const streamNames = streamIds
        .map((id) => streams.find((s) => s.id === id)?.name)
        .filter(Boolean);

      if (streamNames.length) {
        archivalComment = `${archivalComment} in ${streamNames.join(
          ", ",
        )} alert stream${streamNames.length > 1 ? "s" : ""}`;
      }
    }

    setDefaultArchivalComment(archivalComment);
  }, [sharingServicesList, selectedSharingServiceId, instrumentList, streams]);

  const handleSubmit = async ({ formData }) => {
    setSharingRequestInProcess(true);

    const payload = {
      ...formData,
      obj_id: obj_id,
      sharing_service_id: selectedSharingServiceId,
      photometry_options: {
        first_and_last_detections: formData.first_and_last_detections,
      },
      publish_to_tns: sendToTNS,
      publish_to_hermes: sendToHermes,
    };

    delete payload.first_and_last_detections;
    if (payload?.remarks?.length === 0) {
      delete payload.remarks;
    }

    const result = await dispatch(
      sharingServicesActions.addSharingServiceSubmission(payload),
    );
    setSharingRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Successfully queued for submission."));
    }
    setDialogOpen(false);
  };

  if (!sharingServicesList?.length) {
    return (
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        {loading ? (
          <DialogContent
            style={{ width: "60px", height: "60px", padding: "0" }}
          >
            <Spinner />
          </DialogContent>
        ) : (
          <DialogTitle>
            <Typography variant="body1" color="text.secondary">
              No sharing services available...
            </Typography>
          </DialogTitle>
        )}
      </Dialog>
    );
  }

  const formSchema = {
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
          anyOf: allowedInstruments.map((instrument) => ({
            enum: [instrument.id],
            type: "integer",
            title: `${
              telescopeList.find(
                (telescope) => telescope.id === instrument.telescope_id,
              )?.name
            } / ${instrument.name}`,
          })),
        },
        uniqueItems: true,
        default: defaultInstrumentIds,
        title: "Instrument(s)",
      },
      stream_ids: {
        type: "array",
        items: {
          type: "integer",
          anyOf: streams.map((stream) => ({
            enum: [stream.id],
            type: "integer",
            title: stream.name,
          })),
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

  const validate = (formData, errors) => {
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
    if (publishers === `on behalf of...`) {
      errors.publishers.addError(
        "Please edit the publishers field before submitting",
      );
    }
    if (publishers.includes("on behalf of")) {
      if (!/on behalf of\s*[a-zA-Z]+/i.test(publishers)) {
        errors.publishers.addError(
          "Please specify the group you are publishing on behalf of",
        );
      }
    }
    if (formData.archival === true && !formData.archival_comment) {
      errors.archival.addError(
        "Archival comment must be defined if archival is true",
      );
    }
    return errors;
  };

  return (
    <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
      <DialogTitle>
        <Box display="flex" gap={1}>
          Send to
          <Tooltip
            title={
              isNoAffiliation ? (
                <h3>
                  Warning: You have no affiliation(s), you should set your
                  affiliation(s) in your profile before submitting to TNS
                </h3>
              ) : (
                ""
              )
            }
          >
            <div>
              <Chip
                label="Tns"
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
                  className={classes.tooltipLink}
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
        <div className={classes.container}>
          <FormControl fullWidth required>
            <InputLabel id="sharingServiceSelectLabel">
              Sharing Service
            </InputLabel>
            <Select
              inputProps={{ MenuProps: { disableScrollLock: true } }}
              labelId="sharingServiceSelectLabel"
              label="Sharing Service"
              value={selectedSharingServiceId || ""}
              onChange={(e) => setselectedSharingServiceId(e.target.value)}
            >
              {sharingServicesList?.map((sharingService) => (
                <MenuItem
                  value={sharingService.id}
                  key={sharingService.id}
                  className={classes.sharingServiceSelectItem}
                >
                  <div style={{ display: "flex", alignItems: "center" }}>
                    {sharingService.testing === true && (
                      <Tooltip
                        title={
                          <h3>
                            This Sharing Service is currently in testing mode.
                            It will not publish any data to TNS but will store
                            the payload in the database instead (useful for
                            debugging purposes). For Hermes, it will publish to
                            the test topic. You can remove it from the sharing
                            services page.
                          </h3>
                        }
                        placement="right"
                      >
                        <BugReportIcon style={{ color: "orange" }} />
                      </Tooltip>
                    )}
                    <Typography
                      variant="body1"
                      style={{ marginLeft: "0.5rem" }}
                    >
                      {sharingService.name}
                    </Typography>
                  </div>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {selectedSharingServiceId &&
            sharingServicesList &&
            (allowedInstruments.length === 0 ? (
              <FormValidationError message="This sharing service has no allowed instruments, edit it before submitting" />
            ) : (
              <div data-testid="external-publishing-form">
                {defaultSharersString ? (
                  <Form
                    schema={formSchema}
                    validator={validator}
                    onSubmit={handleSubmit}
                    disabled={SharingRequestInProcess}
                    customValidate={validate}
                  />
                ) : (
                  <h3>Loading...</h3>
                )}
              </div>
            ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};

SharingServicesDialog.propTypes = {
  obj_id: PropTypes.string.isRequired,
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
};

export default SharingServicesDialog;
