import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";

const TAB_WIDTHS = ["2.5rem", "2.5rem", "3.5rem"];

const CONTROL_ROWS = [2, 3, 2, 2, 1, 2];

const ControlRow = () => (
  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
    <Skeleton variant="text" width="7rem" height={24} />
    <Skeleton variant="rounded" width={32} height={16} />
  </Box>
);

const PhotometryPlotSkeleton = ({ height }: { height: string }) => (
  <Box sx={{ width: "100%" }}>
    <Box sx={{ display: "flex", gap: 3, paddingX: 2, paddingY: 1.5 }}>
      {TAB_WIDTHS.map((width, index) => (
        <Skeleton
          key={`tab-${index}`}
          variant="text"
          width={width}
          height={24}
        />
      ))}
    </Box>
    <Skeleton variant="rounded" width="100%" height={height} />
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        columnGap: 4,
        paddingX: 2,
        paddingTop: 1,
      }}
    >
      {CONTROL_ROWS.map((rows, index) => (
        <Box key={`control-${index}`}>
          {[...Array(rows)].map((_, row) => (
            <ControlRow key={`control-${index}-${row}`} />
          ))}
        </Box>
      ))}
    </Box>
  </Box>
);

export default PhotometryPlotSkeleton;
