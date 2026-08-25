import { useState, useRef } from "react";
import {
  Box,
  Chip,
  TextField,
  IconButton,
  Tooltip,
  Badge,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";

interface ChipArrayInputProps {
  value?: any;
  onChange: (...a: any[]) => void;
  label?: string;
}

const ChipArrayInput = ({
  value = [],
  onChange,
  label = "Values",
}: ChipArrayInputProps) => {
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<any>(null);
  const fileInputRef = useRef<any>(null);

  const chips: string[] = (() => {
    if (Array.isArray(value)) {
      return value.map(String);
    }
    if (value === null || value === undefined || value === "") {
      return [];
    }
    return [String(value)];
  })();

  const handleInputChange = (e: any) => {
    setInputValue(e.target.value);
  };

  const handleKeyDown = (e: any) => {
    const trimmedValue = inputValue.trim();

    if ((e.key === " " || e.key === "Enter") && trimmedValue) {
      e.preventDefault();

      if (!chips.includes(trimmedValue)) {
        const newChips = [...chips, trimmedValue];
        onChange(newChips);
      }

      setInputValue("");
    }

    if (e.key === "Backspace" && !inputValue && chips.length > 0) {
      e.preventDefault();
      const newChips = chips.slice(0, -1);
      onChange(newChips.length > 0 ? newChips : []);
    }
  };

  const handleDeleteChip = (chipToDelete: any) => {
    const newChips = chips.filter((chip: any) => chip !== chipToDelete);
    onChange(newChips.length > 0 ? newChips : []);
  };

  const handleBlur = () => {
    const trimmedValue = inputValue.trim();
    if (trimmedValue && !chips.includes(trimmedValue)) {
      const newChips = [...chips, trimmedValue];
      onChange(newChips);
      setInputValue("");
    }
  };

  // Handle CSV file import
  const handleFileUpload = (event: any) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e: any) => {
      const text = e.target?.result;
      if (typeof text === "string") {
        // Parse CSV: split by newlines and commas, trim whitespace
        const values = text
          .split(/[\n,]/) // Split by newlines or commas
          .map((val: any) => val.trim()) // Trim whitespace
          .filter((val: any) => val !== "") // Remove empty strings
          .filter((val: any) => !chips.includes(val)); // Remove duplicates

        if (values.length > 0) {
          const newChips = [...chips, ...values];
          onChange(newChips);
        }
      }
    };
    reader.readAsText(file);

    // Reset file input so the same file can be uploaded again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <Box
      sx={{ display: "flex", alignItems: "flex-start", gap: 1, width: "100%" }}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.txt"
        style={{ display: "none" }}
        onChange={handleFileUpload}
      />

      {/* Chip input container */}
      <Badge
        badgeContent={chips.length}
        color="primary"
        max={1000}
        sx={{ flexGrow: 1, width: 0 }}
      >
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 0.5,
            alignContent: "flex-start",
            border: "1px solid rgba(0, 0, 0, 0.23)",
            borderRadius: 1,
            padding: 0.5,
            minHeight: 40,
            maxHeight: 120, // Cap the height at ~3 rows of chips
            overflowY: "auto", // Scroll vertically inside the box
            overflowX: "hidden", // Never overflow horizontally
            width: "100%",
            boxSizing: "border-box", // Ensure border is included in height calculation
            "&:focus-within": {
              borderColor: "primary.main",
              borderWidth: 2,
            },
          }}
          onClick={() => {
            if (inputRef.current) {
              inputRef.current.focus();
            }
          }}
        >
          {chips.map((chip: any, index: number) => (
            <Chip
              key={`${chip}-${index}`}
              label={chip}
              onDelete={() => handleDeleteChip(chip)}
              size="small"
              color="primary"
              variant="outlined"
            />
          ))}
          <TextField
            inputRef={inputRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onBlur={handleBlur}
            placeholder={chips.length === 0 ? label : ""}
            variant="standard"
            sx={{
              flexGrow: 1,
              minWidth: 120,
              "& .MuiInput-root": {
                "&:before, &:after": {
                  display: "none",
                },
              },
            }}
            slotProps={{
              input: {
                disableUnderline: true,
              },
            }}
          />
        </Box>
      </Badge>

      {/* CSV Upload Button */}
      <Tooltip title="Import from CSV">
        <IconButton
          onClick={handleUploadClick}
          size="small"
          color="primary"
          sx={{
            border: "1px solid",
            borderColor: "primary.main",
            "&:hover": {
              backgroundColor: "primary.light",
            },
          }}
        >
          <UploadFileIcon />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

export default ChipArrayInput;
