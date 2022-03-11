import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useHistory } from "react-router-dom";
import Form from "@rjsf/material-ui";
import Paper from "@material-ui/core/Paper";
import Typography from "@material-ui/core/Typography";
import DragHandleIcon from "@material-ui/icons/DragHandle";
import PropTypes from "prop-types";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "./GroupShareSelect";
import { saveSource, checkSource } from "../ducks/source";

dayjs.extend(utc);

const NewSource = ({ classes }) => {
  const history = useHistory();
  const dispatch = useDispatch();
  const allGroups = useSelector((state) => state.groups.all);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const handleSubmit = async ({ formData }) => {
    let data = null;
    data = await dispatch(checkSource(formData.id, formData));
    if (data.data) {
      dispatch(showNotification(data.data, "error"));
    } else {
      const result = await dispatch(saveSource(formData));
      if (result.status === "success") {
        dispatch(showNotification("Source saved"));
        history.push(`/source/${formData.id}`);
      }
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
        <div>
          <Typography variant="h6" display="inline">
            Add a Source
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
          <div>
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
            />
          </div>
        </div>
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
