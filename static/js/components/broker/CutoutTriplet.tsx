import { useEffect, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";

import ThumbnailList from "../thumbnail/ThumbnailList";

import { bytes2image } from "../../utils/imageProcessing";

interface CutoutTripletProps {
  brokerId: number;
  candid: string | number;
  survey: string;
  ra: number;
  dec: number;
}

/**
 * Fetch an alert's science/template/difference cutouts from the broker API and
 * render them (client-side FITS -> image, borrowed from fritz) via the core
 * ThumbnailList.
 */
const CutoutTriplet = ({
  brokerId,
  candid,
  survey,
  ra,
  dec,
}: CutoutTripletProps) => {
  const [dataUris, setDataUris] = useState<{
    new?: string | null;
    ref?: string | null;
    sub?: string | null;
  } | null>(null);

  useEffect(() => {
    let alive = true;
    fetch(`/api/brokers/${brokerId}/alerts/${candid}/cutouts`, {
      credentials: "include",
    })
      .then((r) => r.json())
      .then((json) => {
        if (!alive) return;
        if (json.status !== "success" || !json.data) {
          setDataUris({});
          return;
        }
        const d = json.data;
        setDataUris({
          new: bytes2image(d.cutoutScience, survey, "science", "bone") ?? null,
          ref:
            bytes2image(d.cutoutTemplate, survey, "template", "bone") ?? null,
          sub:
            bytes2image(d.cutoutDifference, survey, "difference", "bone") ??
            null,
        });
      })
      .catch(() => alive && setDataUris({}));
    return () => {
      alive = false;
    };
  }, [brokerId, candid, survey]);

  if (dataUris === null) {
    return <CircularProgress size={32} />;
  }

  return (
    <ThumbnailList
      thumbnails={[
        { type: "new", id: 0, public_url: dataUris.new },
        { type: "ref", id: 1, public_url: dataUris.ref },
        { type: "sub", id: 2, public_url: dataUris.sub },
      ]}
      ra={ra}
      dec={dec}
      displayTypes={["new", "ref", "sub"]}
    />
  );
};

export default CutoutTriplet;
