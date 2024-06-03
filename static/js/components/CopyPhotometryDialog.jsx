import React from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import { Controller, useForm } from "react-hook-form";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";

import { showNotification } from "baselayer/components/Notifications";
import Button from "./Button";
import * as sourceActions from "../ducks/source";
import FormValidationError from "./FormValidationError";

const CopyPhotometryDialog = ({
  source,
  duplicate,
  dialogOpen,
  closeDialog,
}) => {
  const dispatch = useDispatch();

  const groups = useSelector((state) => state.groups.userAccessible);

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  const currentGroupIds = source.groups?.map((g) => g.id);

  const savedGroups = groups?.filter((g) => currentGroupIds.includes(g.id));

  const validateGroups = () => {
    const formState = getValues();
    return (
      formState.groupIds?.length &&
      formState.groupIds.filter((value) => Boolean(value)).length >= 1
    );
  };

  const onSubmit = async (data) => {
    data.origin_id = duplicate;
    const savedGroupIds = savedGroups?.map((g) => g.id);
    const groupIds = savedGroupIds?.filter((ID, idx) => data.groupIds[idx]);
    data.group_ids = groupIds;
    const result = await dispatch(
      sourceActions.copySourcePhotometry(source.id, data),
    );
    if (result.status === "success") {
      dispatch(
        showNotification("Source photometry updated successfully", "info"),
      );
      reset();
    }
    closeDialog();
  };

  const handleClose = () => {
    closeDialog();
  };

  return (
    <>
      <Dialog open={dialogOpen} onClose={handleClose}>
        <DialogTitle>Copy photometry to selected groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {(errors.inviteGroupIds || errors.unsaveGroupIds) && (
              <FormValidationError message="Select at least one group." />
            )}
            {!!savedGroups.length && (
              <>
                {savedGroups.map((savedGroup, idx) => (
                  <FormControlLabel
                    key={savedGroup.id}
                    control={
                      <Controller
                        render={({ field: { onChange, value } }) => (
                          <Checkbox
                            onChange={(event) => onChange(event.target.checked)}
                            checked={value}
                            data-testid={`copyGroupCheckbox_${savedGroup.id}`}
                          />
                        )}
                        name={`groupIds[${idx}]`}
                        control={control}
                        rules={{ validate: validateGroups }}
                        defaultValue={false}
                      />
                    }
                    label={savedGroup.name}
                  />
                ))}
              </>
            )}
            <div style={{ textAlign: "center" }}>
              <Button
                secondary
                type="submit"
                name={`copyPhotometryButton_${source.id}`}
              >
                Save
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};
CopyPhotometryDialog.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string,
    groups: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
    ),
  }).isRequired,
  duplicate: PropTypes.string.isRequired,
  dialogOpen: PropTypes.bool.isRequired,
  closeDialog: PropTypes.func.isRequired,
};

export default CopyPhotometryDialog;
