import { makeStyles } from "tss-react/mui";
import { useAppSelector } from "../types/hooks";

const useStyles = makeStyles()(() => ({
  rotateLogo: {
    verticalAlign: "middle",
    height: "100%",
    animationName: "$rotateUp",
    animationDuration: "4s",
  },
  noRotateLogo: {
    verticalAlign: "middle",
    height: "100%",
  },
  "@keyframes rotateUp": {
    "0%": {
      transform: "rotate(60deg)",
    },
    "50%": {
      transform: "rotate(-10deg)",
    },
    "100%": {
      transform: "rotate(0deg)",
    },
  },
}));

interface LogoProps {
  src?: string;
  altText?: string;
}

const Logo = ({
  src = "/static/images/skyportal_logo_dark.png",
  altText = "SkyPortal logo",
}: LogoProps) => {
  const rotateLogo = useAppSelector((state) => state.logo.rotateLogo);
  const { classes: styles } = useStyles();
  return (
    <div className={(styles as any).logoContainer}>
      <img
        alt={altText}
        className={rotateLogo ? styles.rotateLogo : styles.noRotateLogo}
        src={src}
      />
    </div>
  );
};

export default Logo;
