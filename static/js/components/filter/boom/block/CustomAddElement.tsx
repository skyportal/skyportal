import { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import {
  Box,
  Button,
  Popper,
  Paper,
  ClickAwayListener,
  Divider,
  Typography,
  TextField,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

interface CustomAddElementProps {
  block: any;
  uiState: {
    activeBlockForAdd?: any;
    setActiveBlockForAdd: (...a: any[]) => void;
  };
  customBlocks: any[];
  defaultCondition: (...a: any[]) => any;
  defaultBlock: (...a: any[]) => any;
  setFilters: (...a: any[]) => void;
  filters: any[];
  setSpecialConditionDialog: (...a: any[]) => void;
  setListConditionDialog: (...a: any[]) => void;
  setSwitchDialog: (...a: any[]) => void;
  setCollapsedBlocks: (...a: any[]) => void;
  disableSwitchOption?: boolean;
}

const CustomAddElement = ({
  block,
  uiState: { activeBlockForAdd, setActiveBlockForAdd },
  customBlocks,
  defaultCondition,
  defaultBlock,
  setFilters,
  filters,
  setSpecialConditionDialog,
  setListConditionDialog,
  setSwitchDialog,
  setCollapsedBlocks,
  disableSwitchOption = false,
}: CustomAddElementProps) => {
  const [customBlockSearch, setCustomBlockSearch] = useState("");
  const [hoveredVariable, setHoveredVariable] = useState(false);
  const [variableButtonRef, setVariableButtonRef] = useState<any>(null);
  const [addButtonRef, setAddButtonRef] = useState<any>(null);

  const addItemToBlock = (blockId: string, category: string) => {
    const updateFilters = (filtersArray: any[]) => {
      return filtersArray.map((rootBlock: any) => {
        const updateBlock = (currentBlock: any): any => {
          if (currentBlock.id === blockId) {
            let newItem;
            if (category === "condition") {
              newItem = defaultCondition();
            } else if (category === "switch") {
              // Create a switch condition with the $switch operator
              newItem = {
                ...defaultCondition(),
                operator: "$switch",
                value: {
                  cases: [
                    {
                      block: {
                        ...defaultBlock(),
                        operator: "$and",
                      },
                      then: "",
                    },
                  ],
                  default: "",
                },
              };
            } else {
              newItem = defaultBlock();
            }
            return {
              ...currentBlock,
              children: [...currentBlock.children, newItem],
            };
          }

          if (currentBlock.children) {
            return {
              ...currentBlock,
              children: currentBlock.children.map((child: any) =>
                child.category === "block" ? updateBlock(child) : child,
              ),
            };
          }

          return currentBlock;
        };

        return updateBlock(rootBlock);
      });
    };

    setFilters(updateFilters(filters));
    setActiveBlockForAdd(null);
  };

  const handleOpenSpecialCondition = (blockId: string) => {
    setSpecialConditionDialog({
      open: true,
      blockId,
      equation: "yourVariableName = yourEquation",
    });
    setActiveBlockForAdd(null);
    setHoveredVariable(false);
  };

  const handleOpenListCondition = (
    blockId: string,
    conditionId: string | null = null,
  ) => {
    setListConditionDialog({ open: true, blockId, conditionId });
    setActiveBlockForAdd(null);
    setHoveredVariable(false);
  };

  const handleOpenSwitchDialog = (blockId: string) => {
    setSwitchDialog({ open: true, blockId });
    setActiveBlockForAdd(null);
    setHoveredVariable(false);
  };

  const addCustomBlockToBlock = (blockId: string, customBlockName: string) => {
    const customBlock = customBlocks.find(
      (cb: any) => cb.name === customBlockName,
    );
    if (!customBlock) return;

    const nestedBlockIds: string[] = [];

    // Helper function to check if a condition is empty/default
    const isEmptyCondition = (condition: any) => {
      return (
        condition.category === "condition" &&
        (condition.field === null ||
          condition.field === undefined ||
          condition.field === "") &&
        (condition.operator === null ||
          condition.operator === undefined ||
          condition.operator === "")
      );
    };

    const cloneBlock = (
      block_to_clone: any,
      parentName: string,
      isTopLevel = true,
    ): any => {
      const newId = uuidv4();
      const clonedBlock = {
        ...block_to_clone,
        id: newId,
        customBlockName: isTopLevel
          ? parentName.replace(/^Custom\./, "")
          : block_to_clone.customBlockName,
        children: block_to_clone.children
          ? block_to_clone.children.map((child: any) =>
              child.category === "block"
                ? cloneBlock(child, parentName, false)
                : {
                    ...child,
                    id: uuidv4(),
                    // Deep clone any object properties that might contain nested data
                    ...(child.value && typeof child.value === "object"
                      ? { value: JSON.parse(JSON.stringify(child.value)) }
                      : {}),
                    ...(child.listCondition
                      ? {
                          listCondition: JSON.parse(
                            JSON.stringify(child.listCondition),
                          ),
                        }
                      : {}),
                  },
            )
          : [],
      };

      if (clonedBlock.category === "block" && !isTopLevel) {
        nestedBlockIds.push(clonedBlock.id);
      }

      return clonedBlock;
    };

    const updateFilters = (filtersArray: any[]) => {
      return filtersArray.map((rootBlock: any) => {
        const updateBlock = (currentBlock: any): any => {
          if (currentBlock.id === blockId) {
            // Found the target block, add the custom block to its children
            const clonedBlock = cloneBlock(
              customBlock.block,
              customBlock.name,
              true,
            );

            // Check if this block only has one child and it's an empty condition
            // If so, remove it before adding the custom block
            let updatedChildren = [...currentBlock.children];
            if (
              updatedChildren.length === 1 &&
              isEmptyCondition(updatedChildren[0])
            ) {
              updatedChildren = [];
            }

            return {
              ...currentBlock,
              children: [...updatedChildren, clonedBlock],
            };
          }

          // Recursively update children blocks
          if (currentBlock.children) {
            return {
              ...currentBlock,
              children: currentBlock.children.map((child: any) =>
                child.category === "block" ? updateBlock(child) : child,
              ),
            };
          }

          return currentBlock;
        };

        return updateBlock(rootBlock);
      });
    };

    setFilters(updateFilters(filters));

    if (nestedBlockIds.length > 0 && setCollapsedBlocks) {
      setCollapsedBlocks((prev: any) => {
        const newCollapsed = { ...prev };
        nestedBlockIds.forEach((id: string) => {
          newCollapsed[id] = true;
        });
        return newCollapsed;
      });
    }
    setActiveBlockForAdd(null);
  };

  return (
    <Box>
      <Button
        ref={setAddButtonRef}
        variant="contained"
        size="medium"
        startIcon={<AddIcon />}
        onClick={() =>
          setActiveBlockForAdd(activeBlockForAdd === block.id ? null : block.id)
        }
        sx={{
          minHeight: 40, // Match the typical height of a small Select component
          px: 2, // Add some horizontal padding to match Select width better
        }}
      >
        Add
      </Button>

      <Popper
        open={activeBlockForAdd === block?.id}
        anchorEl={addButtonRef}
        placement="bottom-start"
        sx={{ zIndex: 1500 }}
        modifiers={[
          {
            name: "offset",
            options: {
              offset: [0, 8],
            },
          },
        ]}
      >
        <ClickAwayListener onClickAway={() => setActiveBlockForAdd(null)}>
          <Paper
            sx={{
              minWidth: 220,
              maxWidth: 300,
              maxHeight: 340,
              overflowY: "auto",
              p: 1,
              boxShadow: "0 4px 24px 0 rgba(80,120,255,0.13)",
              // Hide scrollbars while keeping scroll functionality
              "&::-webkit-scrollbar": {
                display: "none",
              },
              msOverflowStyle: "none", // IE and Edge
              scrollbarWidth: "none", // Firefox
            }}
          >
            <Button
              fullWidth
              variant="text"
              sx={{
                mb: 0.5,
                justifyContent: "flex-start",
                fontWeight: 600,
                borderRadius: 1,
                "&:hover": {
                  bgcolor: "info.light",
                },
              }}
              onClick={() => {
                addItemToBlock(block.id, "condition");
                setActiveBlockForAdd(null);
              }}
            >
              + Condition
            </Button>

            {/* Variable Button with submenu */}
            <Box
              sx={{
                position: "relative",
                mb: 0.5,
              }}
              onMouseEnter={() => setHoveredVariable(true)}
              onMouseLeave={() => setHoveredVariable(false)}
            >
              <Button
                ref={setVariableButtonRef}
                fullWidth
                variant="text"
                sx={{
                  justifyContent: "flex-start",
                  fontWeight: 600,
                  borderRadius: 1,
                  color: "warning.dark",
                  "&:hover": {
                    bgcolor: "warning.light",
                  },
                }}
              >
                + Variable
              </Button>

              <Popper
                open={hoveredVariable}
                anchorEl={variableButtonRef}
                placement="right-start"
                sx={{ zIndex: 2000 }}
                modifiers={[
                  {
                    name: "offset",
                    options: {
                      offset: [0, -4],
                    },
                  },
                ]}
              >
                <Paper
                  sx={{
                    minWidth: 180,
                    p: 0.5,
                    boxShadow: "0 4px 24px 0 rgba(180,83,9,0.13)",
                  }}
                  onMouseEnter={() => setHoveredVariable(true)}
                  onMouseLeave={() => setHoveredVariable(false)}
                >
                  <Button
                    fullWidth
                    variant="text"
                    sx={{
                      justifyContent: "flex-start",
                      fontWeight: 600,
                      borderRadius: 1,
                      color: "warning.dark",
                      fontSize: "0.875rem",
                      "&:hover": {
                        bgcolor: "warning.light",
                      },
                    }}
                    onClick={() => handleOpenSpecialCondition(block.id)}
                  >
                    + Arithmetic
                  </Button>
                  <Button
                    fullWidth
                    variant="text"
                    sx={{
                      justifyContent: "flex-start",
                      fontWeight: 600,
                      borderRadius: 1,
                      color: "success.dark",
                      fontSize: "0.875rem",
                      "&:hover": {
                        bgcolor: "success.light",
                      },
                    }}
                    onClick={() => handleOpenListCondition(block.id)}
                  >
                    + List
                  </Button>
                  {!disableSwitchOption && (
                    <Button
                      fullWidth
                      variant="text"
                      sx={{
                        justifyContent: "flex-start",
                        fontWeight: 600,
                        borderRadius: 1,
                        color: "primary.dark",
                        fontSize: "0.875rem",
                        "&:hover": {
                          bgcolor: "primary.light",
                        },
                      }}
                      onClick={() => handleOpenSwitchDialog(block.id)}
                    >
                      + Switch
                    </Button>
                  )}
                </Paper>
              </Popper>
            </Box>

            <Button
              fullWidth
              variant="text"
              sx={{
                mb: 1,
                justifyContent: "flex-start",
                fontWeight: 600,
                borderRadius: 1,
                "&:hover": {
                  bgcolor: "info.light",
                },
              }}
              onClick={() => addItemToBlock(block.id, "block")}
            >
              + Block
            </Button>

            {customBlocks.length > 0 && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.secondary",
                    px: 1,
                    pb: 0.5,
                    display: "block",
                  }}
                >
                  Custom Blocks
                </Typography>

                <TextField
                  size="small"
                  placeholder="Search custom blocks..."
                  fullWidth
                  sx={{ mb: 1 }}
                  value={customBlockSearch}
                  onChange={(e: any) => setCustomBlockSearch(e.target.value)}
                />

                <Box
                  sx={{
                    maxHeight: 180,
                    overflowY: "auto",
                    // Hide scrollbars while keeping scroll functionality
                    "&::-webkit-scrollbar": {
                      display: "none",
                    },
                    msOverflowStyle: "none", // IE and Edge
                    scrollbarWidth: "none", // Firefox
                  }}
                >
                  {customBlocks
                    .filter(
                      (cb: any) =>
                        !customBlockSearch ||
                        cb.name
                          .replace(/^Custom\./, "")
                          .toLowerCase()
                          .includes(customBlockSearch.toLowerCase()),
                    )
                    .map((cb: any) => (
                      <Button
                        key={cb.name}
                        fullWidth
                        variant="text"
                        sx={{
                          justifyContent: "flex-start",
                          fontWeight: 600,
                          borderRadius: 1,
                          color: "secondary.dark",
                          mb: 0.5,
                          "&:hover": {
                            bgcolor: "secondary.light",
                          },
                        }}
                        onClick={() => addCustomBlockToBlock(block.id, cb.name)}
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
    </Box>
  );
};

export default CustomAddElement;
