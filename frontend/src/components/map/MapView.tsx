import { useEffect, useRef } from "react";
import {
  LngLatBounds,
  Map as MlMap,
  Marker,
  NavigationControl,
  type MapLayerMouseEvent,
  type MapMouseEvent,
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
  /** pick mode: clicking the map drops/moves a pin and reports it */
  onPick?: (lat: number, lon: number) => void;
  marker?: { lat: number; lon: number } | null;
  center?: { lat: number; lon: number; zoom?: number };
}

export default function MapView({ onSiteClick, onPick, marker, center }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const clickRef = useRef(onSiteClick);
  clickRef.current = onSiteClick;
  const pickRef = useRef(onPick);
  pickRef.current = onPick;

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MlMap({
      container: containerRef.current,
      style: STYLE_URL,
      center: center ? [center.lon, center.lat] : [6.5, 45.9],
      zoom: center?.zoom ?? 8,
      attributionControl: { customAttribution: DATA_ATTRIBUTION },
    });
    map.on("click", (e: MapMouseEvent) => {
      pickRef.current?.(
        Number(e.lngLat.lat.toFixed(6)),
        Number(e.lngLat.lng.toFixed(6)),
      );
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
      if (onPick) return; // pick mode keeps the user's framing
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (marker) {
      if (!markerRef.current) {
        markerRef.current = new Marker({ color: "#e84e10" })
          .setLngLat([marker.lon, marker.lat])
          .addTo(map);
      } else {
        markerRef.current.setLngLat([marker.lon, marker.lat]);
      }
    } else if (markerRef.current) {
      markerRef.current.remove();
      markerRef.current = null;
    }
  }, [marker]);

  return <div ref={containerRef} className="h-full w-full" />;
}
