import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

interface CircularProgressWithLabelProps {
  current?: number;
  total?: number;
  percentage?: boolean;
}

const CircularProgressWithLabel = ({
  current = 0,
  total = 100,
  percentage = true,
}: CircularProgressWithLabelProps) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      width: "100%",
      height: "100%",
      alignItems: "center",
      justifyContent: "center",
    }}
  >
    <CircularProgress
      variant="determinate"
      value={Math.round((current * 100) / total)}
      style={{ width: "100%", height: "100%" }}
    />
    <Box
      sx={{
        top: "25%",
        left: 0,
        bottom: 0,
        right: 0,
        position: "absolute",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {percentage ? (
        <Typography
          variant="caption"
          component="div"
          color="text.secondary"
        >{`${Math.round((current * 100) / total)}%`}</Typography>
      ) : (
        <Typography
          variant="caption"
          component="div"
          color="text.secondary"
        >{`${current}/${total}`}</Typography>
      )}
    </Box>
  </div>
);

interface TableProgressTextProps {
  nbItems?: number;
  status?: string;
}

const TableProgressText = ({
  nbItems = 0,
  status = "pending",
}: TableProgressTextProps) => {
  if (nbItems === 0) {
    return null;
  }
  return (
    <div>
      <Typography variant="caption" component="div" color="text.secondary">
        {`${nbItems} ${status}`}
      </Typography>
    </div>
  );
};

export default CircularProgressWithLabel;

export { TableProgressText };
