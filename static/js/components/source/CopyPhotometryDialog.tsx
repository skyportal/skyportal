import { Controller, useForm } from "react-hook-form";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as sourceActions from "../../ducks/source";
import FormValidationError from "../FormValidationError";
import Button from "../Button";
import type { Source } from "../../types";

interface CopyPhotometryDialogProps {
  source: Source;
  duplicate: any;
  dialogOpen: boolean;
  closeDialog: () => void;
}

const CopyPhotometryDialog = ({
  source,
  duplicate,
  dialogOpen,
  closeDialog,
}: CopyPhotometryDialogProps) => {
  const dispatch = useAppDispatch();

  const groups = useAppSelector((state) => state.groups.userAccessible);

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  const currentGroupIds = source.groups?.map((g) => g.id);

  const savedGroups = groups?.filter((g: any) =>
    currentGroupIds?.includes(g.id),
  );

  const validateGroups = () => {
    const formState = getValues();
    return (
      formState["groupIds"]?.length &&
      formState["groupIds"].filter((value: any) => Boolean(value)).length >= 1
    );
  };

  const onSubmit = async (data: any) => {
    data.origin_id = duplicate.obj_id;
    data.group_ids = savedGroups
      ?.filter((_: any, idx: number) => data.groupIds[idx])
      .map((g: any) => g.id);
    const result: any = await dispatch(
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

  return (
    <>
      <Dialog open={dialogOpen} onClose={() => closeDialog()}>
        <DialogTitle>Copy photometry to selected groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {(errors["inviteGroupIds"] || errors["unsaveGroupIds"]) && (
              <FormValidationError message="Select at least one group." />
            )}
            {savedGroups.map((savedGroup: any, idx: number) => (
              <FormControlLabel
                key={savedGroup.id}
                control={
                  <Controller
                    render={({ field: { onChange, value } }) => (
                      <Checkbox
                        onChange={(event) => onChange(event.target.checked)}
                        checked={value}
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

export default CopyPhotometryDialog;
