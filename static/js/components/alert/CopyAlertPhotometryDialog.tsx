import { useForm, Controller } from "react-hook-form";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";

import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch } from "../../types/hooks";

import Button from "../Button";
import FormValidationError from "../FormValidationError";

import { useSaveAlertAsSourceMutation } from "../../ducks/boom_alert";
import { useGetGroupsQuery } from "../../ducks/groups";

interface CopyAlertPhotometryDialogProps {
  alert: any;
  survey: string;
  duplicate: any;
  dialogOpen: boolean;
  closeDialog: (...a: any[]) => void;
}

const CopyAlertPhotometryDialog = ({
  alert,
  survey,
  duplicate,
  dialogOpen,
  closeDialog,
}: CopyAlertPhotometryDialogProps) => {
  const dispatch = useAppDispatch();
  const [saveAlertAsSource] = useSaveAlertAsSourceMutation();

  const { data: groupsData } = useGetGroupsQuery();
  const groups = groupsData?.userAccessible;

  const {
    handleSubmit,
    reset,
    control,
    getValues,

    formState: { errors },
  } = useForm();

  const currentGroupIds = duplicate.groups?.map((g: any) => g.id);

  const savedGroups =
    groups?.filter((g: any) => currentGroupIds.includes(g.id)) ?? [];

  const validateGroups = () => {
    const formState: any = getValues();
    return (
      formState.groupIds?.length &&
      formState.groupIds.filter((value: any) => Boolean(value)).length >= 1
    );
  };

  const onSubmit = async (data: any) => {
    const savedGroupIds = savedGroups?.map((g: any) => g.id);
    const groupIds = savedGroupIds?.filter(
      (_ID: any, idx: number) => data.groupIds[idx],
    );
    data.group_ids = groupIds;
    data.copyToSource = duplicate.id;
    try {
      await saveAlertAsSource({
        survey,
        id: alert.objectId,
        payload: data,
      }).unwrap();
      dispatch(
        showNotification("Source photometry updated successfully", "info"),
      );
      reset();
    } catch {
      // error notification handled by the base query
    }
    closeDialog();
  };

  return (
    <>
      <Dialog open={dialogOpen} onClose={closeDialog} sx={{ "z-index": 99999 }}>
        <DialogTitle>Copy photometry to selected groups:</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            {(errors["inviteGroupIds"] || errors["unsaveGroupIds"]) && (
              <FormValidationError message="Select at least one group." />
            )}
            {!!savedGroups.length && (
              <>
                {savedGroups.map((savedGroup: any, idx: number) => (
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
                name={`copyPhotometryButton_${alert.objectId}`}
              >
                Copy Photometry
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default CopyAlertPhotometryDialog;
