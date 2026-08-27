import { useEffect, useRef } from "react";
import {
  LngLatBounds,
  Map as MlMap,
  NavigationControl,
  type MapLayerMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { SITES_GEOJSON_URL } from "../../lib/api";

// ADR-5: MapLibre GL + OpenFreeMap (no API key; style URL verified live).
// OpenFreeMap/OSM credits are injected automatically by MapLibre from the
// style; we add the data attribution ourselves.
const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";
const DATA_ATTRIBUTION = "© OpenExit contributors (ODbL)";

export interface MapViewProps {
  onSiteClick?: (sitePath: string) => void;
}

export default function MapView({ onSiteClick }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const clickRef = useRef(onSiteClick);
  clickRef.current = onSiteClick;

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MlMap({
      container: containerRef.current,
      style: STYLE_URL,
      center: [6.5, 45.9], // synthetic demo region; fitBounds takes over once data loads
      zoom: 8,
      attributionControl: { customAttribution: DATA_ATTRIBUTION },
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      map.addSource("sites", { type: "geojson", data: SITES_GEOJSON_URL });
      map.addLayer({
        id: "sites-circles",
        type: "circle",
        source: "sites",
        paint: {
          "circle-radius": 9,
          "circle-color": "#e84e10",
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2.5,
        },
      });
      map.addLayer({
        id: "sites-labels",
        type: "symbol",
        source: "sites",
        layout: {
          "text-field": ["get", "name"],
          "text-size": 12,
          "text-offset": [0, 1.3],
          "text-anchor": "top",
        },
        paint: {
          "text-color": "#1a1c1e",
          "text-halo-color": "#ffffff",
          "text-halo-width": 1.5,
        },
      });
      map.on("click", "sites-circles", (e: MapLayerMouseEvent) => {
        const path = e.features?.[0]?.properties?.path as string | undefined;
        if (path) clickRef.current?.(path);
      });
      map.on("mouseenter", "sites-circles", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "sites-circles", () => {
        map.getCanvas().style.cursor = "";
      });
      // frame the data once it arrives
      fetch(SITES_GEOJSON_URL)
        .then((r) => (r.ok ? r.json() : null))
        .then((geojson) => {
          if (!geojson?.features?.length) return;
          const bounds = new LngLatBounds();
          for (const f of geojson.features) {
            bounds.extend(f.geometry.coordinates as [number, number]);
          }
          map.fitBounds(bounds, { padding: 80, maxZoom: 12, duration: 0 });
        })
        .catch(() => undefined);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return <div ref={containerRef} className="h-full w-full" />;
}
