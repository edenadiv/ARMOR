import { useEffect, useRef, useState, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";

import { AlertFeed } from "../components/AlertFeed";
import { MessageFlow } from "../components/MessageFlow";
import { MetricsPanel } from "../components/MetricsPanel";
import { ResourcePanel } from "../components/ResourcePanel";
import { TopologyMap } from "../components/TopologyMap";

type Divider = "left" | "right";

type WidthState = {
  left: number;
  center: number;
  right: number;
};

const MIN_LEFT = 0.18;
const MIN_CENTER = 0.24;
const MIN_RIGHT = 0.2;

export function Dashboard() {
  const [widths, setWidths] = useState<WidthState>({ left: 0.26, center: 0.44, right: 0.3 });
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{
    divider: Divider;
    startX: number;
    start: WidthState;
    widthPx: number;
  } | null>(null);
  const gridRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!dragging) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      const drag = dragRef.current;
      if (!drag) {
        return;
      }
      const deltaRatio = (event.clientX - drag.startX) / drag.widthPx;
      const { start, divider } = drag;

      if (divider === "left") {
        const totalLeftCenter = start.left + start.center;
        const nextLeft = Math.min(
          Math.max(start.left + deltaRatio, MIN_LEFT),
          totalLeftCenter - MIN_CENTER,
        );
        setWidths({
          left: nextLeft,
          center: totalLeftCenter - nextLeft,
          right: start.right,
        });
        return;
      }

      const totalCenterRight = start.center + start.right;
      const nextCenter = Math.min(
        Math.max(start.center + deltaRatio, MIN_CENTER),
        totalCenterRight - MIN_RIGHT,
      );
      setWidths({
        left: start.left,
        center: nextCenter,
        right: totalCenterRight - nextCenter,
      });
    };

    const handleMouseUp = () => {
      setDragging(false);
      dragRef.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging]);

  const beginDrag = (divider: Divider, event: ReactMouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    const gridRect = gridRef.current?.getBoundingClientRect();
    if (!gridRect || gridRect.width <= 0) {
      return;
    }
    dragRef.current = {
      divider,
      startX: event.clientX,
      start: widths,
      widthPx: gridRect.width,
    };
    setDragging(true);
  };

  return (
    <div
      ref={gridRef}
      className={`grid-dash grid-dash--resizable ${dragging ? "is-dragging" : ""}`}
      style={
        {
          "--left-col": `${(widths.left * 100).toFixed(2)}%`,
          "--center-col": `${(widths.center * 100).toFixed(2)}%`,
          "--right-col": `${(widths.right * 100).toFixed(2)}%`,
        } as CSSProperties
      }
    >
      <TopologyMap />
      <div
        className="resize-handle left"
        onMouseDown={(event) => beginDrag("left", event)}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize topology and message flow panels"
      />
      <div className="center">
        <MessageFlow />
      </div>
      <div
        className="resize-handle right"
        onMouseDown={(event) => beginDrag("right", event)}
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize message flow and live alerts panels"
      />
      <div className="right">
        <AlertFeed />
        <MetricsPanel />
        <ResourcePanel />
      </div>
    </div>
  );
}
