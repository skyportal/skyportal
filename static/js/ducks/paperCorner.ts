import { skyportalApi } from "../api/skyportalApi";

export interface PaperMatch {
  bibcode: string;
  title: string;
  first_author: string | null;
  date: string | null;
  arxiv_id: string | null;
  sources: { id: string; designations: string[] }[];
}

interface PaperCornerData {
  enabled: boolean;
  pending: boolean;
  papers: PaperMatch[];
}

const paperCornerApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getPaperCorner: build.query<PaperCornerData, string | void>({
      query: (objID) =>
        objID === undefined
          ? "api/internal/paper_corner"
          : `api/internal/paper_corner?objID=${encodeURIComponent(objID)}`,
    }),
  }),
});

export const { useGetPaperCornerQuery } = paperCornerApi;
