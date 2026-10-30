import Divider from "@mui/material/Divider";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

interface GcnCircularsProps {
  gcnEvent: {
    circulars?: Record<string, string>;
    [key: string]: any;
  };
}

const GcnCirculars = ({ gcnEvent }: GcnCircularsProps) => {
  const circulars = Object.entries(gcnEvent.circulars ?? {});
  if (circulars.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No circulars available for this event yet
      </Typography>
    );
  }
  return (
    <Stack divider={<Divider />} spacing={1}>
      {circulars.map(([id, title]) => (
        <Link
          key={id}
          href={`https://heasarc.gsfc.nasa.gov/wsgi-scripts/tach/gcn_v2/tach.wsgi/?circular=${id}`}
          target="_blank"
          rel="noopener noreferrer"
          underline="hover"
          variant="body2"
        >
          {title}
        </Link>
      ))}
    </Stack>
  );
};

export default GcnCirculars;
