import { useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import Spinner from "../Spinner";
import { useAppDispatch } from "../../types/hooks";
import { useUpdateSpectrumMutation } from "../../ducks/spectra";
import { useGetUsersQuery } from "../../ducks/users";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { compareUsersByLastName, userLabel } from "../../utils/format";
import {
  spectrumCreditsErrors,
  spectrumCreditsFormData,
  spectrumCreditsOrder,
  spectrumCreditsPayload,
  spectrumCreditsSchema,
  spectrumCreditsUiSchema,
} from "./spectrumCredits";

interface EditSpectrumCreditsFormProps {
  spectrum: any;
  onClose: () => void;
}

const EditSpectrumCreditsForm = ({
  spectrum,
  onClose,
}: EditSpectrumCreditsFormProps) => {
  const dispatch = useAppDispatch();
  const [updateSpectrum, { isLoading }] = useUpdateSpectrumMutation();
  const { data: usersData } = useGetUsersQuery();
  const { data: instruments } = useGetInstrumentsQuery();
  const [formData, setFormData] = useState<any>(null);

  const userEnumOptions = useMemo(() => {
    const sortedUsers = [...(usersData?.users ?? [])].sort(
      compareUsersByLastName,
    );
    return {
      enum: sortedUsers.map((user: any) => user.id),
      enumNames: sortedUsers.map((user: any) => userLabel(user, true)),
    };
  }, [usersData]);

  if (!usersData?.users?.length || !instruments) {
    return <Spinner />;
  }

  const roboticObserver =
    instruments.find((i: any) => i.id === spectrum.instrument_id)
      ?.default_observer || "Robotic";
  const currentData =
    formData ?? spectrumCreditsFormData(spectrum, roboticObserver);
  const credits = spectrumCreditsSchema(
    userEnumOptions.enum,
    currentData,
    roboticObserver,
  );

  const onSubmit = async ({ formData: submitted }: { formData: any }) => {
    try {
      await updateSpectrum({
        id: spectrum.id,
        ...spectrumCreditsPayload(
          submitted,
          roboticObserver,
          spectrum.owner_id,
        ),
      }).unwrap();
      dispatch(showNotification("Spectrum credits updated."));
      onClose();
    } catch {
      // error notification handled by the baseQuery
    }
  };

  return (
    <Form
      schema={{ type: "object", ...credits } as any}
      uiSchema={{
        ...spectrumCreditsUiSchema(currentData, userEnumOptions.enumNames),
        "ui:order": spectrumCreditsOrder,
      }}
      validator={validator}
      formData={currentData}
      onChange={
        (({ formData: changed }: { formData: any }) =>
          setFormData(changed)) as any
      }
      onSubmit={onSubmit as any}
      transformErrors={(errors) => spectrumCreditsErrors(errors, currentData)}
      showErrorList={false}
      disabled={isLoading}
    >
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 1, mt: 2 }}>
        <Button secondary onClick={onClose}>
          Cancel
        </Button>
        <Button primary type="submit" disabled={isLoading}>
          Save
        </Button>
      </Box>
    </Form>
  );
};

const stopPropagation = (event: React.SyntheticEvent) =>
  event.stopPropagation();

const EditSpectrumCredits = ({ spectrum }: { spectrum: any }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={(event: React.MouseEvent) => {
          event.stopPropagation();
          setOpen(true);
        }}
        data-testid={`edit-spectrum-credits-${spectrum.id}`}
      >
        Edit credits
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        onClick={stopPropagation}
        onKeyDown={stopPropagation}
        fullWidth
      >
        <DialogTitle sx={{ pb: 0 }}>Edit credits</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {spectrum.instrument_name}, observed{" "}
            {spectrum.observed_at?.slice(0, 10)}
          </Typography>
          {open && (
            <EditSpectrumCreditsForm
              spectrum={spectrum}
              onClose={() => setOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default EditSpectrumCredits;
