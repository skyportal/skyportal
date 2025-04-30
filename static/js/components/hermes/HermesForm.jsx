import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
import Form from "@rjsf/mui";
import BugReportIcon from "@mui/icons-material/BugReport";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Spinner from "../Spinner";
import { userLabel } from "../tns/TNSRobotsPage";
import FormValidationError from "../FormValidationError";

import * as sourceActions from "../../ducks/source";
import * as tnsrobotsActions from "../../ducks/tnsrobots";
import * as streamsActions from "../../ducks/streams";

const useStyles = makeStyles(() => ({
  tnsrobotSelect: {
    width: "100%",
  },
  tnsrobotSelectItem: {
    whiteSpace: "break-spaces",
  },
  container: {
    width: "99%",
    marginBottom: "1rem",
  },
}));

const HermesForm = ({ obj_id, submitCallback }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const { users: allUsers } = useSelector((state) => state.users);
  const currentUser = useSelector((state) => state.profile);
  const streams = useSelector((state) => state.streams);

  const tnsAllowedInstruments = useSelector(
    (state) => state.config.tnsAllowedInstruments,
  );

  const { tnsrobotList } = useSelector((state) => state.tnsrobots);
  const [selectedTNSRobotId, setSelectedTNSRobotId] = useState(null);
  const [defaultReporterString, setDefaultReporterString] = useState(null);
  const [defaultInstrumentIds, setDefaultInstrumentIds] = useState([]);
  const [defaultStreamIds, setDefaultStreamIds] = useState([]);

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const [dataFetched, setDataFetched] = useState(false);

  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  let allowedInstruments;
  if (
    selectedTNSRobotId &&
    tnsrobotList.find((tnsrobot) => tnsrobot.id === selectedTNSRobotId)
      ?.instruments?.length > 0
  ) {
    const tnsRobotInstruments = tnsrobotList.find(
      (tnsrobot) => tnsrobot.id === selectedTNSRobotId,
    )?.instruments;
    // only keep the intersection of the instruments and the tns robot's instruments
    allowedInstruments = instrumentList.filter((instrument) =>
      tnsRobotInstruments?.find(
        (tnsRobotInstrument) => tnsRobotInstrument.id === instrument.id,
      ),
    );
  } else {
    allowedInstruments = instrumentList;
  }

  instrumentList.filter((instrument) =>
    (tnsAllowedInstruments || []).includes(instrument.name?.toLowerCase()),
  );

  useEffect(() => {
    const getTNSRobots = async () => {
      const result = await dispatch(tnsrobotsActions.fetchTNSRobots());
      const { data } = result;
      setSelectedTNSRobotId(data[0]?.id);
    };
    if (tnsrobotList === null) {
      getTNSRobots();
    } else if (tnsrobotList?.length > 0 && !selectedTNSRobotId) {
      setSelectedTNSRobotId(tnsrobotList[0]?.id);
    }
  }, [dispatch, setSelectedTNSRobotId, tnsrobotList]);

  useEffect(() => {
    const fetchData = () => {
      dispatch(streamsActions.fetchStreams());
    };
    if (!dataFetched && (!streams || streams?.length === 0)) {
      fetchData();
      setDataFetched(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, dataFetched]);

  useEffect(() => {
    if (
      tnsrobotList?.length > 0 &&
      selectedTNSRobotId &&
      currentUser &&
      allUsers?.length > 0
    ) {
      const usersLookup = {};
      if (allUsers?.length > 0) {
        allUsers.forEach((user) => {
          usersLookup[user.id] = user;
        });
      }
      let coauthors =
        tnsrobotList.find((tnsrobot) => tnsrobot.id === selectedTNSRobotId)
          ?.coauthors || [];
      // filter out the current user from the coauthors list
      coauthors = coauthors.filter(
        (coauthor) => coauthor.user_id !== currentUser.id,
      );
      const authorString = userLabel(currentUser);
      const coauthorsString = coauthors
        .map((coauthor) => userLabel(usersLookup[coauthor.user_id]))
        .join(", ");
      // append the acknowledgments (string) to the coauthors string if it exists
      const acknowledgments =
        tnsrobotList.find((tnsrobot) => tnsrobot.id === selectedTNSRobotId)
          ?.acknowledgments || "on the behalf of ...";
      let finalString = `${authorString}${
        coauthorsString?.length > 0 ? "," : ""
      } ${coauthorsString} ${acknowledgments}`;
      // remove all the extra spaces (only simple spaces are allowed)
      finalString = finalString.replace(/\s+/g, " ");

      setDefaultReporterString(finalString);
    }
  }, [tnsrobotList, selectedTNSRobotId, currentUser, allUsers]);

  useEffect(() => {
    if (tnsrobotList?.length > 0 && selectedTNSRobotId) {
      if (instrumentList?.length > 0) {
        const tnsRobotInstruments = tnsrobotList.find(
          (tnsrobot) => tnsrobot.id === selectedTNSRobotId,
        )?.instruments;
        const instrumentIds = tnsRobotInstruments?.map(
          (instrument) => instrument.id,
        );
        setDefaultInstrumentIds(instrumentIds);
      }
      if (streams?.length > 0) {
        const tnsRobotStreams = tnsrobotList.find(
          (tnsrobot) => tnsrobot.id === selectedTNSRobotId,
        )?.streams;
        let streamIds = tnsRobotStreams?.map((stream) => stream.id);
        // order the streamIds from lowest to highest
        streamIds = streamIds.sort((a, b) => a - b);
        setDefaultStreamIds(streamIds);
      }
    }
  }, [tnsrobotList, selectedTNSRobotId, instrumentList, streams]);
  // need to check both of these conditions as selectedTNSRobotId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if tnsrobotList is not
  // empty.

  if (tnsrobotList?.length === 0) {
    return <h3>No TNS robots available...</h3>;
  } else if (streams?.length === 0) {
    return <Spinner />;
  }

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    formData.tns_robot_id = selectedTNSRobotId;
    formData.photometry_options = {
      first_and_last_detections: formData.first_and_last_detections,
    };
    delete formData.first_and_last_detections;

    dispatch(sourceActions.addSourceHermes(obj_id, formData)).then((result) => {
      setSubmissionRequestInProcess(false);
      if (result.status === "success") {
        dispatch(showNotification(`Sent to Hermes`));
        if (submitCallback) {
          submitCallback();
        }
      }
    });
  };

  const tnsrobotLookUp = {};
  tnsrobotList?.forEach((tnsrobot) => {
    tnsrobotLookUp[tnsrobot.id] = tnsrobot;
  });

  const handleSelectedTNSRobotChange = (e) => {
    setSelectedTNSRobotId(e.target.value);
  };

  const formSchema = {
    type: "object",
    properties: {
      title: {
        type: "string",
        title: "Title",
        default: obj_id,
      },
      submitter: {
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
      first_and_last_detections: {
        type: "boolean",
        title: "Mandatory first and last detection",
        default:
          tnsrobotLookUp[selectedTNSRobotId]?.photometry_options
            ?.first_and_last_detections !== undefined
            ? tnsrobotLookUp[selectedTNSRobotId]?.photometry_options
                ?.first_and_last_detections
            : true,
        description:
          "If enabled, the bot will not send a report to TNS if there is no first and last detection (at least 2 detections).",
      },
    },
    required: ["title", "submitter", "instrument_ids"],
  };

  return (
    <div className={classes.container}>
      <InputLabel id="tnsrobotSelectLabel">TNS Robot</InputLabel>
      <Select
        inputProps={{ MenuProps: { disableScrollLock: true } }}
        labelId="tnsrobotSelectLabel"
        value={selectedTNSRobotId}
        onChange={handleSelectedTNSRobotChange}
        name="tnsrobotSelect"
        className={classes.tnsrobotSelect}
      >
        {tnsrobotList?.map((tnsrobot) => (
          <MenuItem
            value={tnsrobot.id}
            key={tnsrobot.id}
            className={classes.tnsrobotSelectItem}
          >
            <div style={{ display: "flex", alignItems: "center" }}>
              {tnsrobot.testing === true && (
                <Tooltip
                  title={
                    <h2>
                      This bot is in testing mode and will not submit to Hermes.
                      It will only validate the data using the API. Can be
                      removed from the TNS robots page.
                    </h2>
                  }
                  placement="right"
                >
                  <BugReportIcon style={{ color: "orange" }} />
                </Tooltip>
              )}
              <Typography variant="body1" style={{ marginLeft: "0.5rem" }}>
                {tnsrobot.bot_name}
              </Typography>
            </div>
          </MenuItem>
        ))}
      </Select>
      {selectedTNSRobotId &&
        tnsrobotList &&
        (allowedInstruments.length === 0 ? (
          <FormValidationError message="This TNS robot has no allowed instruments, edit the TNS robot before submitting" />
        ) : (
          <div>
            {defaultReporterString ? (
              <Form
                schema={formSchema}
                validator={validator}
                onSubmit={handleSubmit}
                disabled={submissionRequestInProcess}
                liveValidate
              />
            ) : (
              <h3>Loading...</h3>
            )}
          </div>
        ))}
    </div>
  );
};

HermesForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  submitCallback: PropTypes.func,
};

HermesForm.defaultProps = {
  submitCallback: null,
};

export default HermesForm;
