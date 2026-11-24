import { useEffect, useMemo, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import { useAddMPCMutation, useGetMPCObscodeQuery } from "../../ducks/source";
import { useGetTelescopesQuery } from "../../ducks/telescopes";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";

dayjs.extend(utc);

interface UpdateSourceMPCProps {
  source: {
    id: string;
    mpc_name?: string;
    first_detected?: string;
    [key: string]: any;
  };
}

const UpdateSourceMPC = ({ source }: UpdateSourceMPCProps) => {
  const dispatch = useAppDispatch();
  const [addMPC] = useAddMPCMutation();
  const [dialogOpen, setDialogOpen] = useState(false);
  const {
    register,
    control,
    handleSubmit,
    setValue,
    getFieldState,
    formState: { isSubmitting },
  } = useForm({
    defaultValues: {
      date: (
        source.first_detected ?? dayjs.utc().format("YYYY-MM-DDTHH:mm")
      ).slice(0, 16),
      search_radius: 1,
      limiting_magnitude: 24,
      obscode: "",
    },
  });
  const date = useWatch({ control, name: "date" });
  const { data: telescopes = [] } = useGetTelescopesQuery(undefined, {
    skip: !dialogOpen,
  });
  const { data: defaultObscode } = useGetMPCObscodeQuery(
    { id: source.id, date },
    { skip: !dialogOpen || !date },
  );

  useEffect(() => {
    if (defaultObscode && !getFieldState("obscode").isDirty) {
      setValue("obscode", defaultObscode.obscode);
    }
  }, [defaultObscode, getFieldState, setValue]);

  const observatories = useMemo(() => {
    const names: Record<string, string[]> = { 500: ["Geocentric"] };
    telescopes.forEach(({ mpc_obscode, nickname }) => {
      if (mpc_obscode) (names[mpc_obscode] ??= []).push(nickname);
    });
    return names;
  }, [telescopes]);

  const field = (name: "date" | "search_radius" | "limiting_magnitude") => {
    const { ref, ...rest } = register(name, {
      valueAsNumber: name !== "date",
    });
    return { ...rest, inputRef: ref, size: "small" as const, required: true };
  };

  const onSubmit = async (formData: Record<string, any>) => {
    const { data, error } = await addMPC({ id: source.id, formData });
    if (error) return;
    dispatch(
      showNotification(
        `MPC query sent from observatory ${data?.obscode}. The MPC name will appear once the MPC answers.`,
      ),
    );
    setDialogOpen(false);
  };

  return (
    <>
      <Tooltip title="Search the Minor Planet Center for a known solar system object at this position">
        <Button
          variant="outlined"
          color="primary"
          size="small"
          data-testid="updateMPCIconButton"
          onClick={() => setDialogOpen(true)}
          sx={{ py: 0, px: 0.75, minWidth: 0, height: 24 }}
        >
          <TravelExploreIcon fontSize="small" />
        </Button>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogTitle>Query the Minor Planet Center</DialogTitle>
          <DialogContent>
            <DialogContentText sx={{ mb: 2 }}>
              Look for a known solar system object near this position. Its name
              is added to the source when one is found.
            </DialogContentText>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 2,
                pt: 1,
              }}
            >
              <TextField
                {...field("date")}
                type="datetime-local"
                label="Date (UTC)"
                slotProps={{ inputLabel: { shrink: true } }}
                sx={{ gridColumn: "1 / -1" }}
              />
              <TextField
                {...field("search_radius")}
                type="number"
                label="Search radius [arcmin]"
                slotProps={{ htmlInput: { step: 0.1, min: 0 } }}
              />
              <TextField
                {...field("limiting_magnitude")}
                type="number"
                label="Limiting magnitude"
                slotProps={{ htmlInput: { step: 0.1 } }}
              />
              <Controller
                name="obscode"
                control={control}
                render={({ field: { value, onChange } }) => (
                  <Autocomplete
                    freeSolo
                    options={Object.keys(observatories)}
                    filterOptions={(codes, { inputValue }) =>
                      codes.includes(inputValue)
                        ? codes
                        : codes.filter((code) =>
                            `${code} ${observatories[code]?.join(" ")}`
                              .toUpperCase()
                              .includes(inputValue),
                          )
                    }
                    inputValue={value}
                    onInputChange={(_event, code) =>
                      onChange(code.toUpperCase())
                    }
                    renderOption={({ key, ...props }, code) => (
                      <Box component="li" key={key} {...props} sx={{ gap: 1 }}>
                        <b>{code}</b>
                        {observatories[code]?.join(", ")}
                      </Box>
                    )}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        size="small"
                        label="Observatory code"
                        helperText={
                          value === defaultObscode?.obscode
                            ? "Telescope of the closest detection"
                            : " "
                        }
                      />
                    )}
                    sx={{ gridColumn: "1 / -1" }}
                  />
                )}
              />
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              primary
              type="submit"
              disabled={isSubmitting}
              endIcon={<TravelExploreIcon />}
            >
              Query
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </>
  );
};

export default UpdateSourceMPC;
