import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";
import { Link as RouterLink } from "react-router-dom";

import type { PaperMatch } from "../../ducks/paperCorner";

const PaperList = ({
  papers,
  linkSources,
}: {
  papers: PaperMatch[];
  linkSources: boolean;
}) => (
  <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
    {papers.map((paper) => {
      const metadata = [paper.first_author, paper.date]
        .filter(Boolean)
        .join(" · ");
      return (
        <Box
          component="li"
          key={paper.bibcode}
          sx={{
            py: 0.75,
            "& + &": { borderTop: 1, borderColor: "divider" },
            overflowWrap: "anywhere",
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {paper.title}
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", columnGap: 1 }}>
            {metadata && (
              <Typography variant="caption" color="text.secondary">
                {metadata}
              </Typography>
            )}
            <Link
              variant="caption"
              href={`https://ui.adsabs.harvard.edu/abs/${encodeURIComponent(paper.bibcode)}/abstract`}
              target="_blank"
              rel="noopener noreferrer"
            >
              ADS
            </Link>
            {paper.arxiv_id && (
              <Link
                variant="caption"
                href={`https://arxiv.org/abs/${paper.arxiv_id.split("/").map(encodeURIComponent).join("/")}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                arXiv
              </Link>
            )}
          </Box>
          {paper.sources.map(({ id, designations }) => (
            <Typography
              key={id}
              variant="caption"
              color="text.secondary"
              component="div"
            >
              {linkSources && (
                <>
                  <Link
                    component={RouterLink}
                    to={`/source/${encodeURIComponent(id)}`}
                  >
                    {id}
                  </Link>
                  {" · "}
                </>
              )}
              Matched on {designations.join(", ")}
            </Typography>
          ))}
        </Box>
      );
    })}
  </Box>
);

export default PaperList;
