import Paper from "@mui/material/Paper";

import MoreLikeThis from "./MoreLikeThis";
import NeighborVetting from "./NeighborVetting";

const SimilarityPage = () => (
  <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
    <Paper style={{ padding: "1rem" }}>
      <NeighborVetting />
    </Paper>
    <Paper style={{ padding: "1rem" }}>
      <MoreLikeThis />
    </Paper>
  </div>
);

export default SimilarityPage;
