import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Typography from "@mui/material/Typography";

import { showNotification } from "baselayer/components/Notifications";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import GroupShareSelect from "../group/GroupShareSelect";
import { checkSource, saveSource } from "../../ducks/source";
import { dms_to_dec, hours_to_ra } from "../../units";

dayjs.extend(utc);

const NewSource = ({ classes, onClose }) => {
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
    const dataToSend = {
      ...formData,
    };
    if (dataToSend?.ra?.includes(":")) {
      dataToSend.ra = hours_to_ra(dataToSend?.ra);
    } else {
      dataToSend.ra = parseFloat(dataToSend?.ra);
    }
    if (dataToSend?.dec?.includes(":")) {
      dataToSend.dec = dms_to_dec(dataToSend?.dec);
    } else {
      dataToSend.dec = parseFloat(dataToSend?.dec);
    }
    if (
      dataToSend?.id === "" ||
      dataToSend?.id === null ||
      dataToSend?.id === undefined ||
      !dataToSend?.id
    ) {
      dispatch(showNotification("Please enter a source ID.", "error"));
    } else {
      const data = await dispatch(checkSource(dataToSend?.id, dataToSend));
      if (data.status === "success") {
        if (data.data?.source_exists === true) {
          dispatch(showNotification(data.data.message, "error"));
          return;
        }

        if (selectedGroupIds.length > 0) {
          dataToSend.group_ids = selectedGroupIds;
        }
        const result = await dispatch(saveSource(dataToSend));
        if (result.status === "success") {
          onClose();
          dispatch(showNotification("Source saved"));
          navigate(`/source/${dataToSend.id}`);
        }
      }
    }
  };

  function validate(formData, errors) {
    if (selectedGroupIds?.length === 0 && formData?.id !== "") {
      errors.__errors.push("Select at least one group.");
    }
    if ((formData?.ra !== "" || formData?.dec !== "") && formData?.id === "") {
      errors.id.addError("Please enter a source ID.");
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
    <div className={classes.widgetPaperDiv}>
      <div>
        <Typography variant="h6" display="inline">
          Add a Source
        </Typography>
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
            customValidate={validate}
          />
        </div>
      </div>
    </div>
  );
};

NewSource.propTypes = {
  classes: PropTypes.shape({
    widgetPaperDiv: PropTypes.string.isRequired,
  }).isRequired,
  onClose: PropTypes.func,
};

NewSource.defaultProps = {
  onClose: () => ({}),
};

export default NewSource;
