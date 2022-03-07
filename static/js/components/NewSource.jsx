import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/material-ui";
import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import PropTypes from "prop-types";
import { makeStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "./GroupShareSelect";
import { saveSource } from "../ducks/source";
import { fetchSources } from "../ducks/sources";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  header: {},
  eventListContainer: {
    height: "calc(100% - 5rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  eventList: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  eventNameContainer: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  eventNameLink: {
    color: theme.palette.primary.main,
  },
  eventTags: {
    marginLeft: "1rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
}));

const NewSource = ({ classes }) => {
  const styles = useStyles();

  const dispatch = useDispatch();
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const handleSubmit = async ({ formData }) => {
    const result = await dispatch(saveSource(formData));
    if (result.status === "success") {
      dispatch(showNotification("Source saved"));
      dispatch(fetchSources());
    }
  };

  function validate(formData, errors) {
    if (formData.ra < 0 || formData.ra >= 360) {
      errors.ra.addError("0 <= RA < 360, please fix.");
    }
    if (formData.dec < -90 || formData.dec > 90) {
      errors.ra.addError("-90 <= Declination <= 90, please fix.");
    }
    return errors;
  }

  const sourceFormSchema = {
    type: "object",
    properties: {
      id: {
        type: "string",
        title: "object ID",
      },
      ra: {
        type: "number",
        title: "Right Ascension [deg]",
      },
      dec: {
        type: "number",
        title: "Declination [deg]",
      },
    },
    required: ["id", "ra", "dec"],
  };

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div className={styles.header}>
          <Typography variant="h6" display="inline">
            Add a Source
          </Typography>
        </div>
        <GroupShareSelect
          groupList={allGroups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
        <Form
          schema={sourceFormSchema}
          onSubmit={handleSubmit}
          // eslint-disable-next-line react/jsx-no-bind
          validate={validate}
          liveValidate
        />
      </div>
    </Paper>
  );
};

NewSource.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
    widgetIcon: PropTypes.string.isRequired,
    widgetPaperFillSpace: PropTypes.string.isRequired,
  }).isRequired,
};

export default NewSource;
