import { Link as RouterLink } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Link from "@mui/material/Link";
import Typography from "@mui/material/Typography";

import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetInstrumentsQuery } from "../../ducks/instruments";
import { useGetTelescopesQuery } from "../../ducks/telescopes";

const observingRunLabel = (
  run: any,
  instruments: any[],
  telescopes: any[],
  groups: any[],
) => {
  const instrument = instruments?.find((i) => i.id === run?.instrument_id);
  const telescope = telescopes?.find((t) => t.id === instrument?.telescope_id);
  const group = groups?.find((g) => g.id === run?.group_id);
  if (!run?.calendar_date || !instrument?.name || !telescope?.name) return null;
  return {
    name: `${run.calendar_date} ${instrument.name}/${telescope.nickname}`,
    details: [
      run.pi && `PI: ${run.pi}`,
      group?.name && `Group: ${group.name}`,
    ].filter(Boolean),
  };
};

export const observingRunTitle = (
  run: any,
  instruments: any[],
  telescopes: any[],
  groups: any[],
) => {
  const label = observingRunLabel(run, instruments, telescopes, groups);
  if (!label) return <CircularProgress />;
  return label.details.length
    ? `${label.name} (${label.details.join(" / ")})`
    : label.name;
};

interface ObservingRunTitleProps {
  run: any;
  variant?: "body2" | "h5";
  link?: boolean;
  sx?: any;
}

const ObservingRunTitle = ({
  run,
  variant = "body2",
  link = false,
  sx,
}: ObservingRunTitleProps) => {
  const { data: instruments = [] } = useGetInstrumentsQuery();
  const { data: telescopes = [] } = useGetTelescopesQuery();
  const groups = useGetGroupsQuery().data?.all ?? [];
  const label = observingRunLabel(run, instruments, telescopes, groups);
  if (!label) return <CircularProgress size={20} />;

  return (
    <Box sx={sx}>
      <Typography variant={variant}>
        {link ? (
          <Link component={RouterLink} to={`/run/${run.id}`} underline="hover">
            {label.name}
          </Link>
        ) : (
          label.name
        )}
      </Typography>
      {label.details.length > 0 && (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {label.details.join(" · ")}
        </Typography>
      )}
    </Box>
  );
};

export default ObservingRunTitle;
