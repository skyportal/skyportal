import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Spinner from "./Spinner";
import { userLabel } from "./TNSRobotsPage";

import * as sourceActions from "../ducks/source";
import * as tnsrobotsActions from "../ducks/tnsrobots";
import * as streamsActions from "../ducks/streams";

const useStyles = makeStyles(() => ({
  chips: {
    display: "flex",
    flexWrap: "wrap",
  },
  chip: {
    margin: 2,
  },
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

const TNSATForm = ({ obj_id, submitCallback }) => {
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

  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);

  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);
  const [dataFetched, setDataFetched] = useState(false);

  const groupIDToName = {};
  groups?.forEach((g) => {
    groupIDToName[g.id] = g.name;
  });

  const allowedInstruments = instrumentList.filter((instrument) =>
    (tnsAllowedInstruments || []).includes(instrument.name?.toLowerCase()),
  );

  useEffect(() => {
    const getTNSRobots = async () => {
      // Wait for the TNS robots to update before setting
      // the new default form fields, so that the TNS robots list can
      // update

      const result = await dispatch(tnsrobotsActions.fetchTNSRobots());

      const { data } = result;
      setSelectedTNSRobotId(data[0]?.id);
    };
    if (tnsrobotList?.length === 0 && !tnsrobotList) {
      getTNSRobots();
    } else if (tnsrobotList?.length > 0 && !selectedTNSRobotId) {
      setSelectedTNSRobotId(tnsrobotList[0]?.id);
    }

    // Don't want to reset everytime the component rerenders and
    // the defaultStartDate is updated, so ignore ESLint here
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  }, [dataFetched, dispatch]);

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

  // need to check both of these conditions as selectedTNSRobotId is
  // initialized to be null and useEffect is not called on the first
  // render to update it, so it can be null even if tnsrobotList is not
  // empty.
  if (tnsrobotList.length === 0) {
    return <h3>No TNS robots available...</h3>;
  }

  if (!streams?.length) {
    return <Spinner />;
  }

  const handleSubmit = async ({ formData }) => {
    setSubmissionRequestInProcess(true);
    formData.tnsrobotID = selectedTNSRobotId;
    const result = await dispatch(sourceActions.addSourceTNS(obj_id, formData));
    setSubmissionRequestInProcess(false);
    if (result.status === "success") {
      dispatch(showNotification("added to TNS submission queue"));
    } else {
      dispatch(
        showNotification("Failed to add object to TNS submission queue"),
      );
    }
    if (submitCallback) {
      submitCallback();
    }
  };

  const tnsrobotLookUp = {};
  // eslint-disable-next-line no-unused-expressions
  tnsrobotList?.forEach((tnsrobot) => {
    tnsrobotLookUp[tnsrobot.id] = tnsrobot;
  });

  const handleSelectedTNSRobotChange = (e) => {
    setSelectedTNSRobotId(e.target.value);
  };

  const formSchema = {
    type: "object",
    properties: {
      reporters: {
        type: "string",
        title: "Reporters",
        default: defaultReporterString,
      },
      archival: {
        type: "boolean",
        title: "Archival (no upperlimits)",
        default: false,
      },
      instrument_id: {
        type: "integer",
        oneOf: allowedInstruments.map((instrument) => ({
          enum: [instrument.id],
          title: `${
            telescopeList.find(
              (telescope) => telescope.id === instrument.telescope_id,
            )?.name
          } / ${instrument.name}`,
        })),
        title: "Instrument",
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
        default: [],
        title: "Streams (optional)",
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
              },
            },
            required: ["archivalComment"],
          },
        ],
      },
    },
  };

  const validate = (formData, errors) => {
    if (
      formData.reporters ===
      `${currentUser.first_name} ${currentUser.last_name} on behalf of...`
    ) {
      errors.reporters.addError(
        "Please edit the reporters field before submitting",
      );
    }
    if (formData.reporters.includes("on behalf of")) {
      const secondHalf = formData.reporters.split("on behalf of")[1];
      if (!secondHalf.match(/[a-z]/i)) {
        errors.reporters.addError(
          "Please specify the group you are reporting on behalf of",
        );
      }
    }
    if (formData.reporters === "" || formData.reporters === undefined) {
      errors.reporters.addError(
        "Please specify the group you are reporting on behalf of",
      );
    }

    if (formData.archival === true) {
      if (
        Object.keys(formData).includes("archivalComment") &&
        formData.archivalComment === undefined
      ) {
        errors.archival.addError(
          "Archival comment must be defined if archive is true",
        );
      }
    }
    return errors;
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
            {`${tnsrobot.bot_name}`}
          </MenuItem>
        ))}
      </Select>
      <div data-testid="tnsrobot-form">
        {defaultReporterString ? (
          <Form
            schema={formSchema}
            validator={validator}
            onSubmit={handleSubmit}
            disabled={submissionRequestInProcess}
            customValidate={validate}
            liveValidate
          />
        ) : (
          <h3>Loading...</h3>
        )}
      </div>
    </div>
  );
};

TNSATForm.propTypes = {
  obj_id: PropTypes.string.isRequired,
  submitCallback: PropTypes.func,
};

TNSATForm.defaultProps = {
  submitCallback: null,
};

export default TNSATForm;
