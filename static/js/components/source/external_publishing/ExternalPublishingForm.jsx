import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import validator from "@rjsf/validator-ajv8";
import { Theme as MuiTheme } from "@rjsf/mui";
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
import Checkbox from "@mui/material/Checkbox";

import { showNotification } from "baselayer/components/Notifications";
import Spinner from "../../Spinner";
import { userLabel } from "../../tns/TNSRobotsPage";
import FormValidationError from "../../FormValidationError";

import * as sourceActions from "../../../ducks/source";
import * as externalPublishingActions from "../../../ducks/externalPublishing";
import * as streamsActions from "../../../ducks/streams";
import InfoIcon from "@mui/icons-material/Info";

const CustomCheckboxWidget = ({ id, name, value, onChange, label, schema }) => {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <Checkbox
        type="checkbox"
        id={id}
        name={name}
        checked={value}
        onChange={(event) => onChange(event.target.checked)}
      />
      <label htmlFor={id}>{label}</label>
      {schema?.description && (
        <Tooltip
          title={<h3>{schema.description}</h3>}
          size="medium"
          style={{ fontSize: "3rem" }}
        >
          <InfoIcon size="small" style={{ color: "grey", fontSize: "1rem" }} />
        </Tooltip>
      )}
    </div>
  );
};

CustomCheckboxWidget.propTypes = {
  id: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string.isRequired,
  schema: PropTypes.objectOf({
    description: PropTypes.string,
  }).isRequired,
};

const CustomMuiTheme = {
  ...MuiTheme,
  widgets: {
    ...MuiTheme.widgets,
    CheckboxWidget: CustomCheckboxWidget,
  },
};

const Form = withTheme(CustomMuiTheme);

const useStyles = makeStyles(() => ({
  externalPublishingBotSelect: {
    width: "100%",
  },
  externalPublishingBotSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const ExternalPublishingDialog = ({ obj_id, dialogOpen, setDialogOpen }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const { users: allUsers } = useSelector((state) => state.users);
  const currentUser = useSelector((state) => state.profile);
  const streams = useSelector((state) => state.streams);
  const allowedInstrumentForPublishing = useSelector(
    (state) => state.config.allowedInstrumentForPublishing,
  );
  const isNoAffiliation = !currentUser?.affiliations?.length;

  const { botList } = useSelector((state) => state.externalPublishingBots);
  const [selectedBotId, setSelectedBotId] = useState(null);
  const [defaultReporterString, setDefaultReporterString] = useState(null);
  const [defaultArchivalComment, setDefaultArchivalComment] = useState(null);
  const [defaultInstrumentIds, setDefaultInstrumentIds] = useState([]);
  const [defaultStreamIds, setDefaultStreamIds] = useState([]);
  const [sendToTNS, setSendToTNS] = useState(!isNoAffiliation);
  const [sendToHermes, setSendToHermes] = useState(false);
  // request in process
  const [publishRequestInProcess, setPublishRequestInProcess] = useState(false);
  const [dataFetched, setDataFetched] = useState(false);

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const selectedBot = botList?.find((b) => b.id === selectedBotId);
  const allowedInstruments = selectedBot?.instruments
    ? instrumentList.filter((instrument) =>
        selectedBot.instruments.some((i) => i.id === instrument.id),
      )
    : [];

  instrumentList.filter((instrument) =>
    (allowedInstrumentForPublishing || []).includes(
      instrument.name?.toLowerCase(),
    ),
  );

  useEffect(() => {
    const getPublishingBots = async () => {
      const result = await dispatch(
        externalPublishingActions.fetchExternalPublishingBots(),
      );
      const { data } = result;
      setSelectedBotId(data[0]?.id);
    };
    if (botList === null) {
      getPublishingBots();
    } else if (botList?.length > 0 && !selectedBotId) {
      setSelectedBotId(botList[0]?.id);
    }
  }, [dispatch, botList, selectedBotId]);

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
      botList?.length > 0 &&
      selectedBotId &&
      currentUser &&
      allUsers?.length > 0
    ) {
      const coauthors = (selectedBot?.coauthors || []).filter(
        (coauthor) => coauthor.user_id !== currentUser.id,
      );
      const authorString = userLabel(currentUser);
      const coauthorsString = coauthors
        .map((coauthor) =>
          userLabel(allUsers.find((user) => user.id === coauthor.user_id)),
        )
        .join(", ");
      const acknowledgments =
        selectedBot?.acknowledgments || "on the behalf of ...";

      const finalString = `${authorString}${
        coauthorsString ? `, ${coauthorsString}` : ""
      } ${acknowledgments}`.replace(/\s+/g, " ");

      setDefaultReporterString(finalString);
    }
  }, [botList, selectedBotId, currentUser, allUsers]);

  useEffect(() => {
    if (!botList?.length || !selectedBotId || !selectedBot) return;
    let archivalComment = "No non-detections prior to first detection";

    // Set instruments
    if (instrumentList?.length && selectedBot.instruments?.length) {
      const instrumentIds = selectedBot.instruments.map((i) => i.id);
      setDefaultInstrumentIds(instrumentIds);
    }

    // Set streams
    if (streams?.length && selectedBot.streams?.length) {
      const streamIds = selectedBot.streams
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
  }, [botList, selectedBotId, instrumentList, streams]);

  if (botList?.length === 0) {
    return <h3>No publishing bots available...</h3>;
  }

  if (!streams?.length) {
    return <Spinner />;
  }

  const handleSubmit = async ({ formData }) => {
    setPublishRequestInProcess(true);

    const payload = {
      ...formData,
      external_publishing_bot_id: selectedBotId,
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
      sourceActions.publishSourceExternally(obj_id, payload),
    );
    setPublishRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("Successfully added to the publish queue"));
    }
    setDialogOpen(false);
  };

  const formSchema = {
    type: "object",
    properties: {
      reporters: {
        type: "string",
        title: "Reporters",
        default: defaultReporterString,
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
        description:
          "Any additional remarks to include in the report. Optional",
      },
      first_and_last_detections: {
        type: "boolean",
        title: "Mandatory first and last detection",
        default:
          selectedBot?.photometry_options?.first_and_last_detections ?? true,
        description:
          "If enabled, the bot will not publish the data if there is no first and last detection (at least 2 detections).",
      },
      archival: {
        type: "boolean",
        title: "Archival report",
        description:
          "TNS reports require non-detections by default. However, reports can be sent as 'archival', excluding non-detections and requiring a comment. You can use this option after a normal report failed because non-detections were missing.",
        default: false,
      },
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
              archivalComment: {
                type: "string",
                title: "Archival Comment",
                default: defaultArchivalComment,
              },
            },
            required: ["archivalComment"],
          },
        ],
      },
    },
    required: ["reporters", "instrument_ids"],
  };

  const validate = (formData, errors) => {
    if (!sendToTNS && !sendToHermes) {
      errors.__errors.push(
        "Please select at least one destination (TNS or Hermes)",
      );
    }
    const reporters = formData.reporters ?? "";
    if (!reporters.trim()) {
      errors.reporters.addError(
        "Please specify the group you are reporting on behalf of",
      );
    }
    if (reporters === `on behalf of...`) {
      errors.reporters.addError(
        "Please edit the reporters field before submitting",
      );
    }
    if (reporters.includes("on behalf of")) {
      if (!/on behalf of\s*[a-zA-Z]+/i.test(reporters)) {
        errors.reporters.addError(
          "Please specify the group you are reporting on behalf of",
        );
      }
    }
    if (formData.archival === true && !formData.archivalComment) {
      errors.archival.addError(
        "Archival comment must be defined if archival is true",
      );
    }
    return errors;
  };

  return (
    <Dialog
      open={dialogOpen}
      onClose={() => setDialogOpen(false)}
      style={{ position: "fixed" }}
    >
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
                disabled={isNoAffiliation}
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
            />
          </Tooltip>
        </Box>
      </DialogTitle>
      <DialogContent>
        <div className={classes.container}>
          <InputLabel id="externalPublishingBotSelectLabel">
            External publishing bot
          </InputLabel>
          <Select
            inputProps={{ MenuProps: { disableScrollLock: true } }}
            labelId="externalPublishingBotSelectLabel"
            value={selectedBotId}
            onChange={(e) => setSelectedBotId(e.target.value)}
            name="externalPublishingBotSelect"
            className={classes.externalPublishingBotSelect}
          >
            {botList?.map((publishingBot) => (
              <MenuItem
                value={publishingBot.id}
                key={publishingBot.id}
                className={classes.externalPublishingBotSelectItem}
              >
                <div style={{ display: "flex", alignItems: "center" }}>
                  {publishingBot.testing === true && (
                    <Tooltip
                      title={
                        <h2>
                          This bot is currently in testing mode. It will not
                          publish any data but will store the payload in the
                          database instead (useful for debugging purposes). You
                          can remove it from the External Publishing Bots page.
                        </h2>
                      }
                      placement="right"
                    >
                      <BugReportIcon style={{ color: "orange" }} />
                    </Tooltip>
                  )}
                  <Typography variant="body1" style={{ marginLeft: "0.5rem" }}>
                    {publishingBot.bot_name}
                  </Typography>
                </div>
              </MenuItem>
            ))}
          </Select>
          {selectedBotId &&
            botList &&
            (allowedInstruments.length === 0 ? (
              <FormValidationError message="This publishing bot has no allowed instruments, edit this bot before submitting" />
            ) : (
              <div data-testid="external-publishing-form">
                {defaultReporterString ? (
                  <Form
                    schema={formSchema}
                    validator={validator}
                    onSubmit={handleSubmit}
                    disabled={publishRequestInProcess}
                    customValidate={validate}
                    liveValidate
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

ExternalPublishingDialog.propTypes = {
  obj_id: PropTypes.string.isRequired,
  dialogOpen: PropTypes.bool.isRequired,
  setDialogOpen: PropTypes.func.isRequired,
};

export default ExternalPublishingDialog;
