import Skeleton from "@mui/material/Skeleton";

const TAB_WIDTHS = ["2.5rem", "2.5rem", "3.5rem"];

const CONTROL_ROWS = [2, 3, 2, 2, 1, 2];

interface PhotometryPlotSkeletonProps {
  /** The height the plot itself will take, so nothing moves once it is drawn. */
  height: string;
}

const ControlRow = () => (
  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
    <Skeleton variant="text" width="7rem" height={24} />
    <Skeleton variant="rounded" width={32} height={16} />
  </div>
);

const PhotometryPlotSkeleton = ({ height }: PhotometryPlotSkeletonProps) => (
  <div style={{ width: "100%" }}>
    <div style={{ display: "flex", gap: "1.5rem", padding: "0.75rem 1rem" }}>
      {TAB_WIDTHS.map((width, index) => (
        <Skeleton
          key={`tab-${index}`}
          variant="text"
          width={width}
          height={24}
        />
      ))}
    </div>
    <Skeleton variant="rounded" width="100%" height={height} />
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        columnGap: "2rem",
        padding: "0.5rem 1rem 0 1rem",
      }}
    >
      {CONTROL_ROWS.map((rows, index) => (
        <div key={`control-${index}`}>
          {[...Array(rows)].map((_, row) => (
            <ControlRow key={`control-${index}-${row}`} />
          ))}
        </div>
      ))}
    </div>
  </div>
);

export default PhotometryPlotSkeleton;
