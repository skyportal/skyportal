import { useState } from "react";
import {
  Box,
  Button,
  ClickAwayListener,
  Divider,
  IconButton,
  Paper,
  Popper,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import MoreVertIcon from "@mui/icons-material/MoreVert";

import { useFilterBuilder } from "../../../../hooks/useContexts";
import {
  cloneCustomBlock,
  mapBlock,
  replaceOrAppend,
} from "../block/blockTree";

interface ConditionTypeMenuProps {
  condition: any;
  block: any;
  filters: any[];
  setFilters: (...a: any[]) => void;
  disableSwitchOption?: boolean;
}

const itemSx = (color: string, hover: string) => ({
  justifyContent: "flex-start",
  fontWeight: 600,
  borderRadius: 1,
  color,
  "&:hover": { bgcolor: hover },
});

const ConditionTypeMenu = ({
  condition,
  block,
  filters,
  setFilters,
  disableSwitchOption = false,
}: ConditionTypeMenuProps) => {
  const {
    customBlocks,
    customVariables,
    createDefaultBlock,
    setCollapsedBlocks,
    setSpecialConditionDialog,
    setListConditionDialog,
    setSwitchDialog,
  } = useFilterBuilder();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const [search, setSearch] = useState("");

  const label = condition.isListVariable
    ? "List"
    : (customVariables ?? []).some((v: any) => v.name === condition.field)
      ? "Variable"
      : "Condition";

  const close = () => {
    setAnchor(null);
    setSearch("");
  };

  const replaceWith = (item: any) => {
    setFilters(
      mapBlock(filters, block.id, (current) => ({
        ...current,
        children: replaceOrAppend(current.children, item, condition.id),
      })),
    );
    close();
  };

  const openDialog = (setDialog: (...a: any[]) => void, extra = {}) => {
    setDialog({
      open: true,
      blockId: block.id,
      replaceConditionId: condition.id,
      ...extra,
    });
    close();
  };

  const insertCustomBlock = (customBlock: any) => {
    const { block: cloned, nestedBlockIds } = cloneCustomBlock(customBlock);
    replaceWith(cloned);
    setCollapsedBlocks((prev: any) => ({
      ...prev,
      ...Object.fromEntries(nestedBlockIds.map((id) => [id, true])),
    }));
  };

  const matchingCustomBlocks = (customBlocks ?? []).filter(
    (cb: any) =>
      !search ||
      cb.name
        .replace(/^Custom\./, "")
        .toLowerCase()
        .includes(search.toLowerCase()),
  );

  return (
    <>
      <Tooltip title={`${label}: click to change its type`}>
        <IconButton
          size="small"
          onClick={(e) => (anchor ? close() : setAnchor(e.currentTarget))}
          aria-label="Change the type of this condition"
          sx={{ p: 0.25 }}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Popper
        open={!!anchor}
        anchorEl={anchor}
        placement="bottom-start"
        sx={{ zIndex: 1500 }}
      >
        <ClickAwayListener onClickAway={close}>
          <Paper sx={{ minWidth: 220, maxWidth: 300, p: 1 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ px: 1, display: "block" }}
            >
              Turn this condition into
            </Typography>
            <Button
              fullWidth
              sx={itemSx("warning.dark", "warning.light")}
              onClick={() =>
                openDialog(setSpecialConditionDialog, {
                  equation: "yourVariableName = yourEquation",
                })
              }
            >
              Arithmetic variable
            </Button>
            <Button
              fullWidth
              sx={itemSx("success.dark", "success.light")}
              onClick={() =>
                openDialog(setListConditionDialog, { conditionId: null })
              }
            >
              List variable
            </Button>
            {!disableSwitchOption && (
              <Button
                fullWidth
                sx={itemSx("primary.dark", "primary.light")}
                onClick={() => openDialog(setSwitchDialog)}
              >
                Switch
              </Button>
            )}
            <Button
              fullWidth
              sx={itemSx("info.dark", "info.light")}
              onClick={() =>
                replaceWith({ ...createDefaultBlock(), children: [condition] })
              }
            >
              Block
            </Button>
            {(customBlocks ?? []).length > 0 && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ px: 1, pb: 0.5, display: "block" }}
                >
                  Custom blocks
                </Typography>
                <TextField
                  size="small"
                  placeholder="Search custom blocks..."
                  fullWidth
                  sx={{ mb: 1 }}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <Box sx={{ maxHeight: 180, overflowY: "auto" }}>
                  {matchingCustomBlocks.map((cb: any) => (
                    <Button
                      key={cb.name}
                      fullWidth
                      sx={itemSx("secondary.dark", "secondary.light")}
                      onClick={() => insertCustomBlock(cb)}
                    >
                      {cb.name.replace(/^Custom\./, "")}
                    </Button>
                  ))}
                </Box>
              </>
            )}
          </Paper>
        </ClickAwayListener>
      </Popper>
    </>
  );
};

export default ConditionTypeMenu;
