import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";

interface DeletableChipsProps {
  items: string[];
  onDelete: (item: string) => void;
}

const DeletableChips = ({ items, onDelete }: DeletableChipsProps) => (
  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
    {items?.map((item) => (
      <Chip
        key={item}
        label={item}
        color="primary"
        variant="outlined"
        onDelete={() => onDelete(item)}
      />
    ))}
  </Box>
);

export default DeletableChips;
