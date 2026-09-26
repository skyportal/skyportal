import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Typography from "@mui/material/Typography";

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
  <Box
    sx={{
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
      sx={{ width: "100%", height: "100%" }}
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
      <Typography
        variant="caption"
        component="div"
        sx={{ color: "text.secondary" }}
      >
        {percentage
          ? `${Math.round((current * 100) / total)}%`
          : `${current}/${total}`}
      </Typography>
    </Box>
  </Box>
);

interface DownloadProgressDialogProps {
  current: number;
  total: number;
  label: string;
}

const DownloadProgressDialog = ({
  current,
  total,
  label,
}: DownloadProgressDialogProps) => (
  <Dialog open={total > 0} maxWidth="md">
    <DialogContent
      sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}
    >
      <Typography variant="h6">
        Downloading {total} {label}
      </Typography>
      <Box sx={{ height: "5rem", width: "5rem" }}>
        <CircularProgressWithLabel
          current={current}
          total={total}
          percentage={false}
        />
      </Box>
    </DialogContent>
  </Dialog>
);

interface TableProgressTextProps {
  nbItems?: number;
  status?: string;
}

const TableProgressText = ({
  nbItems = 0,
  status = "pending",
}: TableProgressTextProps) =>
  nbItems === 0 ? null : (
    <Typography
      variant="caption"
      component="div"
      sx={{ color: "text.secondary" }}
    >
      {`${nbItems} ${status}`}
    </Typography>
  );

export { DownloadProgressDialog, TableProgressText };
