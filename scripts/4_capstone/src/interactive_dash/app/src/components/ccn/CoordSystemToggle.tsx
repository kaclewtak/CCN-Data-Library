/**
 * CCN ADDITION — Coordinate System Toggle
 * ========================================
 * Renders two always-visible icon buttons (Cartesian / Geographic) that
 * replace the single dropdown built into graphic-walker's toolbar.
 *
 * The built-in dropdown is CSS-hidden (see index.tsx) so both coordinate
 * modes are discoverable at a glance.
 */

import React from "react";
import { observer } from "mobx-react-lite";
import type { VizSpecStore } from "@kanaries/graphic-walker/store/visualSpecStore";
import { GlobeAltIcon } from "@heroicons/react/24/outline";
import {
    ToggleGroup,
    ToggleGroupItem,
} from "@/components/ui/toggle-group";

/* ---- Cartesian / crosshair icon (matches graphic-walker's built-in) ---- */
const CartesianIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <svg
        stroke="currentColor"
        fill="none"
        strokeWidth="1.5"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        aria-hidden="true"
        width="16"
        height="16"
        {...props}
    >
        <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M2 12h20M12 2v20"
        />
        <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 7h2M12 16h2M7 12v-2M16 12v-2"
        />
    </svg>
);

/* ---- Geographic / globe icon (via @heroicons/react) ---- */
const GeoIcon: React.FC<React.SVGProps<SVGSVGElement>> = (props) => (
    <GlobeAltIcon width="16" height="16" {...props} />
);

export interface CoordSystemToggleProps {
    storeRef: React.RefObject<VizSpecStore | null>;
}

const CoordSystemToggle: React.FC<CoordSystemToggleProps> = observer(
    ({ storeRef }) => {
        const coordSystem =
            storeRef.current?.currentVis?.config?.coordSystem ?? "generic";

        return (
            <div
                className="flex items-center gap-1"
                title="Coordinate System"
                data-ccn-component="coord-toggle"
            >
                <ToggleGroup
                    type="single"
                    value={coordSystem}
                    onValueChange={(value) => {
                        if (value) {
                            storeRef.current?.setCoordSystem(
                                value as "generic" | "geographic",
                            );
                        }
                    }}
                >
                    <ToggleGroupItem value="generic" aria-label="Cartesian">
                        <CartesianIcon className="h-4 w-4" />
                    </ToggleGroupItem>
                    <ToggleGroupItem value="geographic" aria-label="Geographic">
                        <GeoIcon className="h-4 w-4" />
                    </ToggleGroupItem>
                </ToggleGroup>
            </div>
        );
    },
);

export default CoordSystemToggle;
