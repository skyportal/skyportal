import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Skeleton from "@mui/material/Skeleton";
import { SxProps, Theme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import { useCommentPanel } from "../../contexts/CommentPanelContext";
import { useGetProfileQuery } from "../../ducks/profile";
import FavoritesButton from "../listing/FavoritesButton";
import { SlowLoadNotice } from "../Spinner";

interface SourceSkeletonProps {
  objId: string;
}

interface SectionProps {
  name: string;
  order: number;
  titleWidth: string;
  /** Left out for a section that loads collapsed, so only its title shows. */
  bodyHeight?: string;
  buttons?: number;
}

const LEFT_SECTIONS: SectionProps[] = [
  { name: "surveys", order: 2, titleWidth: "5rem", bodyHeight: "2.5rem" },
  {
    name: "photometry",
    order: 4,
    titleWidth: "8rem",
    bodyHeight: "65vh",
    buttons: 4,
  },
  {
    name: "spectroscopy",
    order: 5,
    titleWidth: "9rem",
    bodyHeight: "55vh",
    buttons: 2,
  },
  { name: "followup", order: 10, titleWidth: "7rem", bodyHeight: "10rem" },
  { name: "forcedPhotometry", order: 11, titleWidth: "11rem" },
  { name: "observingRun", order: 12, titleWidth: "14rem", bodyHeight: "8rem" },
];

const ButtonRow = ({ count, sx }: { count: number; sx?: SxProps<Theme> }) => (
  <Box
    sx={[
      { display: "flex", flexWrap: "wrap", gap: 1 },
      ...(Array.isArray(sx) ? sx : [sx]),
    ]}
  >
    {[...Array(count)].map((_, index) => (
      <Skeleton
        key={`button-${index}`}
        variant="rounded"
        width={110}
        height={30}
      />
    ))}
  </Box>
);

const Section = ({ titleWidth, bodyHeight, buttons = 0 }: SectionProps) => (
  <Paper sx={{ padding: 1 }}>
    <Skeleton variant="text" width={titleWidth} height={32} />
    {bodyHeight && (
      <Skeleton variant="rounded" width="100%" height={bodyHeight} />
    )}
    {buttons > 0 && <ButtonRow count={buttons} sx={{ marginTop: 1 }} />}
  </Paper>
);

const SourceSkeleton = ({ objId }: SourceSkeletonProps) => {
  const downLg = useMediaQuery((theme: Theme) => theme.breakpoints.down("lg"));
  const { data: profile } = useGetProfileQuery();
  const { inline: inlineComments } = useCommentPanel();
  const canWrite = !profile || (profile.permissions?.length ?? 0) > 0;

  const rightSections: SectionProps[] = [
    {
      name: "annotations",
      order: 6,
      titleWidth: "10rem",
      bodyHeight: "52vh",
      buttons: canWrite ? 3 : 0,
    },
    ...(canWrite && inlineComments
      ? [
          {
            name: "comments",
            order: 3,
            titleWidth: "7rem",
            bodyHeight: "60vh",
          },
        ]
      : []),
    { name: "centroidPlot", order: 8, titleWidth: "8rem", bodyHeight: "50vh" },
    { name: "hrDiagram", order: 9, titleWidth: "7rem", bodyHeight: "19rem" },
    {
      name: "classifications",
      order: 13,
      titleWidth: "9rem",
      bodyHeight: "6rem",
    },
    { name: "analysis", order: 14, titleWidth: "10rem", bodyHeight: "8rem" },
    {
      name: "notification",
      order: 15,
      titleWidth: "11rem",
      bodyHeight: "8rem",
    },
  ];

  // Stacked on a narrow screen, the loaded page interleaves the two columns.
  const mainSections = downLg
    ? [...LEFT_SECTIONS, ...rightSections].sort((a, b) => a.order - b.order)
    : LEFT_SECTIONS;

  return (
    <Grid container spacing={1.5}>
      <Grid container size={{ xs: 12, lg: 7 }} spacing={1.5}>
        <Grid size={12}>
          <Paper sx={{ padding: 1 }}>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                columnGap: 0.5,
                marginBottom: 0.5,
              }}
            >
              <Box
                sx={{ display: "flex", alignItems: "center", columnGap: 0.5 }}
              >
                {canWrite && <FavoritesButton sourceID={objId} />}
                {/* Not an <h6>: the tests wait on //h6[text()=objId] to know the page loaded. */}
                <Box
                  sx={{
                    lineHeight: "1em",
                    fontSize: "200%",
                    fontWeight: 900,
                    color: (theme) =>
                      theme.palette.mode === "dark"
                        ? theme.palette.secondary.main
                        : theme.palette.primary.main,
                  }}
                >
                  {objId}
                </Box>
              </Box>
              <Skeleton variant="circular" width={26} height={26} />
            </Box>

            <Skeleton variant="text" width="30%" height={24} />
            <Skeleton variant="text" width="70%" height={24} />
            <Skeleton variant="text" width="55%" height={24} />
            <Skeleton variant="text" width="65%" height={24} />

            <ButtonRow count={7} sx={{ marginY: 1.5 }} />

            <Skeleton
              variant="rounded"
              width="100%"
              height="4rem"
              sx={{ marginBottom: 1 }}
            />
            <Skeleton
              variant="text"
              width="40%"
              height={24}
              sx={{ marginBottom: 1 }}
            />

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 13rem))",
                gap: 1,
              }}
            >
              {[...Array(6)].map((_, index) => (
                <Box key={`thumbnail-${index}`}>
                  <Skeleton variant="text" width="60%" height={20} />
                  <Skeleton
                    variant="rounded"
                    sx={{ width: "100%", height: "auto", aspectRatio: "1 / 1" }}
                  />
                </Box>
              ))}
            </Box>
          </Paper>
          <SlowLoadNotice overlay />
        </Grid>
        {mainSections.map((section) => (
          <Grid size={12} key={section.name}>
            <Section {...section} />
          </Grid>
        ))}
      </Grid>

      {!downLg && (
        <Grid
          container
          size={5}
          spacing={1.5}
          sx={{ alignContent: "flex-start" }}
        >
          {rightSections.map((section) => (
            <Grid size={12} key={section.name}>
              <Section {...section} />
            </Grid>
          ))}
        </Grid>
      )}
    </Grid>
  );
};

export default SourceSkeleton;
