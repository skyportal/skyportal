import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import DragHandleIcon from "@mui/icons-material/DragHandle";
import PropTypes from "prop-types";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "./GroupShareSelect";
import { saveSource, checkSource } from "../ducks/source";
import { hours_to_ra, dms_to_dec } from "../units";

dayjs.extend(utc);

const NewSource = ({ classes }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [selectedFormData, setSelectedFormData] = useState({
    id: "",
    ra: "",
    dec: "",
  });

  const handleSubmit = async ({ formData }) => {
    let data = null;
    if (formData?.ra?.includes(":")) {
      formData.ra = hours_to_ra(formData?.ra);
    } else {
      formData.ra = parseFloat(formData?.ra);
    }
    if (formData?.dec?.includes(":")) {
      formData.dec = dms_to_dec(formData?.dec);
    } else {
      formData.dec = parseFloat(formData?.dec);
    }
    if (
      formData?.id === "" ||
      formData?.id === null ||
      formData?.id === undefined ||
      !formData?.id
    ) {
      dispatch(showNotification("Please enter a source ID.", "error"));
    } else {
      data = await dispatch(checkSource(formData?.id, formData));
      if (data.data !== "A source of that name does not exist.") {
        dispatch(showNotification(data.data, "error"));
      } else {
        if (selectedGroupIds.length > 0) {
          formData.group_ids = selectedGroupIds;
        }
        const result = await dispatch(saveSource(formData));
        if (result.status === "success") {
          dispatch(showNotification("Source saved"));
          navigate(`/source/${formData.id}`);
        }
      }
    }
  };

  function validate(formData, errors) {
    if ((formData?.ra !== "" || formData?.dec !== "") && formData?.id === "") {
      errors.id.addError("Please enter a source ID.");
    }
    if (selectedGroupIds?.length === 0 && formData?.id !== "") {
      errors.id.addError("Select at least one group.");
    }
    if ((formData?.id || "").indexOf(" ") >= 0) {
      errors.id.addError("IDs are not allowed to have spaces, please fix.");
    }
    if ((formData?.ra || "").includes(":")) {
      formData.ra = hours_to_ra(formData.ra);
    } else {
      formData.ra = parseFloat(formData.ra);
    }
    if (formData?.ra < 0 || formData?.ra >= 360) {
      errors.ra.addError("0 <= RA < 360, please fix.");
    }
    if ((formData?.dec || "").includes(":")) {
      formData.dec = dms_to_dec(formData.dec);
    } else {
      formData.dec = parseFloat(formData.dec);
    }
    if (formData?.dec < -90 || formData?.dec > 90) {
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
        type: "string",
        title: "Right Ascension [decimal deg. or HH:MM:SS]",
      },
      dec: {
        type: "string",
        title: "Declination [decimal deg. or DD:MM:SS]",
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
              groupList={groups}
              setGroupIDs={setSelectedGroupIds}
              groupIDs={selectedGroupIds}
            />
            <Form
              schema={sourceFormSchema}
              formData={selectedFormData}
              onChange={({ formData }) => setSelectedFormData(formData)}
              validator={validator}
              onSubmit={handleSubmit}
              // eslint-disable-next-line react/jsx-no-bind
              customValidate={validate}
              liveValidate
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
