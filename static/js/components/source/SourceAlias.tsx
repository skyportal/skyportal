import { useState } from "react";
import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";

import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import { useUpdateSourceMutation } from "../../ducks/source";
import FieldLabel from "./FieldLabel";
import EditDialog from "./EditDialog";

interface SourceAliasProps {
  source: {
    id: string;
    alias?: string[];
  };
}

const SourceAlias = ({ source }: SourceAliasProps) => {
  const dispatch = useAppDispatch();
  const [updateSource] = useUpdateSourceMutation();
  const [open, setOpen] = useState(false);
  const [alias, setAlias] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const aliases = source.alias || [];
  const newAlias = alias.trim();
  const duplicate = aliases.includes(newAlias);

  const save = async (aliasList: string[], message: string) => {
    setIsSubmitting(true);
    const result = await updateSource({
      id: source.id,
      payload: { alias: aliasList },
    });
    setIsSubmitting(false);
    if ("error" in result) return false;
    dispatch(showNotification(message));
    return true;
  };

  const add = async () => {
    if (
      await save([...aliases, newAlias], "Source alias successfully updated.")
    ) {
      setOpen(false);
    }
  };

  return (
    <>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.75,
        }}
      >
        <FieldLabel>Aliases</FieldLabel>
        {aliases.length === 0 && (
          <Box component="span" sx={{ fontStyle: "italic", opacity: 0.6 }}>
            none
          </Box>
        )}
        {aliases.map((a, idx) => (
          <Chip
            key={`${a}-${idx}`}
            label={a}
            size="small"
            variant="outlined"
            sx={{ maxWidth: "100%" }}
            onDelete={() =>
              save(
                aliases.filter((other) => other !== a),
                "Source alias removed successfully.",
              )
            }
          />
        ))}
        <Tooltip title="Add alias">
          <IconButton
            data-testid="updateAliasIconButton"
            size="small"
            onClick={() => {
              setAlias("");
              setOpen(true);
            }}
            sx={{
              opacity: 0.5,
              transition: "opacity 0.2s",
              "&:hover": { opacity: 1 },
            }}
          >
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
      <EditDialog
        open={open}
        onClose={() => setOpen(false)}
        title="Add alias"
        actions={
          <Button
            primary
            onClick={add}
            disabled={isSubmitting || !newAlias || duplicate}
            data-testid="addAliasSubmitButton"
          >
            Add
          </Button>
        }
      >
        <TextField
          data-testid="addAliasTextfield"
          size="small"
          label="Alias"
          value={alias}
          onChange={(e) => setAlias(e.target.value)}
          error={duplicate}
          helperText={duplicate ? "Already an alias of this source" : ""}
          autoFocus
          fullWidth
        />
      </EditDialog>
    </>
  );
};

export default SourceAlias;
