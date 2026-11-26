import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import { useGetConfigQuery } from "../../ducks/config";
import { useGetPaperCornerQuery } from "../../ducks/paperCorner";
import PaperList from "./PaperList";

const SourcePapers = ({ objID }: { objID: string }) => {
  const { data: config } = useGetConfigQuery();
  const { currentData: data } = useGetPaperCornerQuery(objID, {
    skip: config?.["paperCornerEnabled"] !== true,
    refetchOnMountOrArgChange: true,
  });
  if (!data?.enabled) return null;

  return (
    <Paper sx={{ mt: 1, p: 1 }}>
      <Typography variant="h6" component="h2" sx={{ fontWeight: "normal" }}>
        Papers
      </Typography>
      {data.papers.length > 0 ? (
        <PaperList papers={data.papers} linkSources={false} />
      ) : (
        <Box
          role="status"
          sx={{ color: "text.secondary", typography: "body2" }}
        >
          {data.pending
            ? "Waiting for the first ADS refresh."
            : "No matching papers."}
        </Box>
      )}
    </Paper>
  );
};

export default SourcePapers;
