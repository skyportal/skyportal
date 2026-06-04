// A small reimplementation of d3-geo-zoom (https://github.com/vasturiano/d3-geo-zoom,
// MIT, Vasco Asturiano), which drives zoom/pan/rotate on a D3 geo projection.
//
// We vendor it instead of depending on the package because its published ESM
// build (v1.5+) does `import versor from "versor/src/index"` — an extensionless
// subpath that strict ESM bundlers (rspack >= 1.6) refuse to resolve — which
// repeatedly broke the dependabot bump. The original leaned on `kapsule` for its
// fluent prop API; that is trivial to inline, so this copy depends only on the
// `versor` math helpers and the `select`/`pointers`/`zoom` utilities re-exported
// by `d3`, both already direct SkyPortal dependencies.
//
// `d3` and `versor` are ambient `any` in this codebase, so the geometry below is
// loosely typed; the exported fluent API, which is all callers touch, is typed.
import { select as d3Select, pointers as d3Pointers, zoom as d3Zoom } from "d3";
import versor from "versor";

export interface GeoZoomMoveEvent {
  scale: number;
  rotation: number[];
}

export interface GeoZoom {
  /** Mount the zoom behavior on a DOM node. Chainable. */
  (element: Element | null): GeoZoom;
  projection(projection: unknown): GeoZoom;
  scaleExtent(extent: [number, number]): GeoZoom;
  northUp(northUp: boolean): GeoZoom;
  onMove(callback: (event: GeoZoomMoveEvent) => void): GeoZoom;
}

export default function d3GeoZoom(): GeoZoom {
  let projection: any = null;
  let scaleExtent: [number, number] = [0.1, 1e3];
  let northUp = false;
  let onMove: (event: GeoZoomMoveEvent) => void = () => {};

  // Base scale of the projection at zoom k=1, captured when the projection is set.
  let unityScale = 1;
  let zoomBehavior: any = null;

  const instance = ((element: Element | null): GeoZoom => {
    if (element) {
      let v0: number[];
      let r0: number[];
      let q0: number[];

      const getPointerCoords = (zoomEv: unknown): [number, number] => {
        const avg = (vals: number[]): number =>
          vals.reduce((agg, v) => agg + v, 0) / vals.length;

        const ptrs = d3Pointers(zoomEv, element);
        if (ptrs && ptrs.length > 1) {
          // centroid of all points when multi-touch
          return [0, 1].map((idx) =>
            avg(ptrs.map((t: number[]) => t[idx])),
          ) as [number, number];
        }
        return ptrs.length ? ptrs[0] : [NaN, NaN];
      };

      const zoomStarted = (ev: any): void => {
        if (!projection) return;
        v0 = versor.cartesian(projection.invert(getPointerCoords(ev)));
        r0 = projection.rotate();
        q0 = versor(r0);
      };

      const zoomed = (ev: any): void => {
        if (!projection) return;

        const scale = ev.transform.k * unityScale;
        projection.scale(scale);

        const v1 = versor.cartesian(
          projection.rotate(r0).invert(getPointerCoords(ev)),
        );
        const q1 = versor.multiply(q0, versor.delta(v0, v1));
        const rotation = versor.rotation(q1);

        if (northUp) {
          rotation[2] = 0; // don't rotate on the Z axis
        }

        projection.rotate(rotation);
        onMove({ scale, rotation });
      };

      zoomBehavior = d3Zoom()
        .scaleExtent(scaleExtent)
        .on("start", zoomStarted)
        .on("zoom", zoomed);
      d3Select(element).call(zoomBehavior);
    }
    return instance;
  }) as unknown as GeoZoom;

  instance.projection = (p: unknown): GeoZoom => {
    projection = p;
    unityScale = p ? (p as any).scale() : 1;
    return instance;
  };
  instance.scaleExtent = (extent: [number, number]): GeoZoom => {
    scaleExtent = extent;
    if (zoomBehavior) zoomBehavior.scaleExtent(extent);
    return instance;
  };
  instance.northUp = (value: boolean): GeoZoom => {
    northUp = value;
    return instance;
  };
  instance.onMove = (callback: (event: GeoZoomMoveEvent) => void): GeoZoom => {
    onMove = callback;
    return instance;
  };

  return instance;
}
