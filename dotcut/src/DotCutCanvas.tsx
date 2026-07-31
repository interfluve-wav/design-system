import React, { useEffect, useRef, useState } from "react";
import { DotCut, DEFAULTS } from "./engine";

export interface DotCutProps {
  className?: string;
  fontFamily?: string;
  cols?: number;
  hold?: number;
  morph?: number;
  brush?: number;
  fill?: number;
  squareness?: number;
  autoplay?: boolean;
  reducedMotion?: boolean;
  onReady?: (engine: DotCut) => void;
}

const prefersReducedMotion = (): boolean =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export default function DotCutCanvas({
  className,
  fontFamily,
  cols = DEFAULTS.cols,
  hold = DEFAULTS.hold,
  morph = DEFAULTS.morph,
  brush = DEFAULTS.brush,
  fill = DEFAULTS.fill,
  squareness = DEFAULTS.squareness,
  autoplay = true,
  reducedMotion = false,
  onReady,
}: DotCutProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<DotCut | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || engineRef.current) return;

    const engine = new DotCut(host, fontFamily);
    engineRef.current = engine;

    if (!engine.ok) return;

    engine.setParams({ cols, hold, morph, brush, fill, squareness });

    onReady?.(engine);
    setReady(true);

    const reduced = reducedMotion || prefersReducedMotion();
    if (autoplay && !reduced) {
      engine.start();
    } else {
      engine.renderStill();
    }

    return () => {
      engine.destroy();
      engineRef.current = null;
    };
  }, []);

  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const engine = engineRef.current;
    if (!engine) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const cell = engine.toCell(e.clientX - rect.left, e.clientY - rect.top);
    engine.setPointer(cell);
  };

  const onPointerLeave = () => {
    const engine = engineRef.current;
    if (!engine) return;
    engine.setPointer(null);
  };

  return (
    <div
      ref={hostRef}
      className={className}
      style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden" }}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      data-dotcut-ready={ready}
    />
  );
}
