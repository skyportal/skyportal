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

const NewSource = ({ onClose }) => {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const groups = useSelector((state) => state.groups.userAccessible);
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);

  const handleSubmit = async ({ formData }) => {
    const dataToSend = {
      ...formData,
      ra: formData?.ra?.includes(":")
        ? hours_to_ra(formData.ra)
        : parseFloat(formData.ra),
      dec: formData?.dec?.includes(":")
        ? dms_to_dec(formData.dec)
        : parseFloat(formData.dec),
    };
    if (!dataToSend?.id) {
      dispatch(showNotification("Please enter a source ID.", "error"));
    } else {
      const data = await dispatch(checkSource(dataToSend?.id, dataToSend));
      if (data.status === "success") {
        if (data.data?.source_exists === true) {
          dispatch(showNotification(data.data.message, "error"));
          return;
        }
        if (selectedGroupIds.length) {
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
    if (!selectedGroupIds?.length && formData?.id) {
      errors.__errors.push("Select at least one group.");
    }
    if ((formData?.ra !== "" || formData?.dec !== "") && !formData?.id) {
      errors.id.addError("Please enter a source ID.");
    }
    if (formData?.id?.includes(" ")) {
      errors.id.addError("IDs are not allowed to have spaces, please fix.");
    }
    const ra = formData?.ra?.includes(":")
      ? hours_to_ra(formData.ra)
      : parseFloat(formData.ra);
    if (ra < 0 || ra >= 360) {
      errors.ra.addError("0 <= RA < 360, please fix.");
    }
    const dec = formData?.dec?.includes(":")
      ? dms_to_dec(formData.dec)
      : parseFloat(formData.dec);
    if (dec < -90 || dec > 90) {
      errors.dec.addError("-90 <= Declination <= 90, please fix.");
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
    <div style={{ position: "relative" }}>
      <Typography variant="h6" display="inline">
        Add a Source
      </Typography>
      <Form
        schema={sourceFormSchema}
        validator={validator}
        onSubmit={handleSubmit}
        customValidate={validate}
      />
      <div style={{ position: "absolute", bottom: "0", right: "0" }}>
        <GroupShareSelect
          groupList={groups}
          setGroupIDs={setSelectedGroupIds}
          groupIDs={selectedGroupIds}
        />
      </div>
    </div>
  );
};

NewSource.propTypes = {
  onClose: PropTypes.func,
};

NewSource.defaultProps = {
  onClose: () => ({}),
};

export default NewSource;
