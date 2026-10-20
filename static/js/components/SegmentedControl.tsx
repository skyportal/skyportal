import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";

interface SegmentedControlProps<T> {
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (value: T) => void;
  size?: "small" | "medium";
}

const SegmentedControl = <T,>({
  value,
  options,
  onChange,
  size = "medium",
}: SegmentedControlProps<T>) => (
  <Box
    sx={{
      display: "inline-flex",
      gap: 0.5,
      p: size === "small" ? 0.25 : 0.5,
      borderRadius: 999,
      border: 1,
      borderColor: "divider",
      backgroundColor: "background.default",
    }}
  >
    {options.map((option) => {
      const selected = option.value === value;
      return (
        <ButtonBase
          key={String(option.value)}
          aria-pressed={selected}
          onClick={() => onChange(option.value)}
          sx={{
            height: size === "small" ? "1.375rem" : "1.75rem",
            px: size === "small" ? 1 : 1.5,
            borderRadius: 999,
            fontSize: size === "small" ? "0.7rem" : "0.8125rem",
            fontWeight: 600,
            whiteSpace: "nowrap",
            color: selected ? "primary.contrastText" : "text.secondary",
            backgroundColor: selected ? "primary.main" : "transparent",
            transition: (theme) =>
              theme.transitions.create(["background-color", "color"], {
                duration: theme.transitions.duration.short,
              }),
            "&:hover": {
              color: selected ? "primary.contrastText" : "text.primary",
            },
            "&.Mui-focusVisible": {
              outline: 2,
              outlineColor: "primary.main",
              outlineOffset: 2,
            },
          }}
        >
          {option.label}
        </ButtonBase>
      );
    })}
  </Box>
);

export default SegmentedControl;
