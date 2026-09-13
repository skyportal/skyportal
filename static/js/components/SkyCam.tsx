import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import CardMedia from "@mui/material/CardMedia";

import { Telescope } from "../types/domain";

interface SkyCamProps {
  telescope: Telescope;
}

const SkyCam = ({ telescope }: SkyCamProps) => {
  const handleImageError = (e: any) => {
    e.target.onerror = null;
    e.target.src = "/static/images/static.jpg";
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">Skycam</Typography>
      </CardContent>
      {telescope.skycam_link ? (
        <CardMedia
          component="img"
          image={telescope.skycam_link || undefined}
          title={`${telescope.nickname} SkyCam`}
          sx={{ minHeight: "18.75rem" }}
          onError={handleImageError}
        />
      ) : (
        <Typography
          variant="subtitle1"
          color="textSecondary"
          sx={{
            width: "100%",
            display: "flex",
            justifyContent: "center",
            p: 2,
          }}
        >
          No skycam link configured
        </Typography>
      )}
    </Card>
  );
};

export default SkyCam;
