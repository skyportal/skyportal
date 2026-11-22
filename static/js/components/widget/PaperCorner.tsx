import DragHandleIcon from "@mui/icons-material/DragHandle";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { useGetPaperCornerQuery } from "../../ducks/paperCorner";
import PaperList from "../source/PaperList";
import WidgetLoading from "./WidgetLoading";

interface PaperCornerProps {
  classes: {
    widgetPaperDiv: string;
    widgetIcon: string;
    widgetPaperFillSpace: string;
  };
}

const PaperCorner = ({ classes }: PaperCornerProps) => {
  const { data, isLoading, isError } = useGetPaperCornerQuery(undefined, {
    refetchOnMountOrArgChange: true,
  });
  let message = "No matching papers.";
  if (isError) message = "Paper Corner is temporarily unavailable.";
  else if (!data?.enabled) message = "Paper Corner is disabled.";
  else if (data.pending) message = "Waiting for the first ADS refresh.";

  return (
    <Paper elevation={1} className={classes.widgetPaperFillSpace}>
      <div className={classes.widgetPaperDiv}>
        <div>
          <Typography variant="h6" component="h2" sx={{ display: "inline" }}>
            Paper Corner
          </Typography>
          <DragHandleIcon className={`${classes.widgetIcon} dragHandle`} />
        </div>
        <Box sx={{ overflowY: "auto" }}>
          {isLoading ? (
            <WidgetLoading />
          ) : data?.papers.length ? (
            <PaperList papers={data.papers} linkSources />
          ) : (
            <Typography variant="body2" color="text.secondary" role="status">
              {message}
            </Typography>
          )}
        </Box>
      </div>
    </Paper>
  );
};

export default PaperCorner;
