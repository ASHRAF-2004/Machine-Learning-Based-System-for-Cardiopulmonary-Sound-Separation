/** Display-only iris tint. Original approved assets and pose geometry stay intact. */
export function OwlEyeMaterial() {
  return (
    <svg className="sf-owl-material" aria-hidden="true" width="0" height="0">
      <defs>
        <filter
          id="sf-pine-irises"
          x="0"
          y="0"
          width="100%"
          height="100%"
          colorInterpolationFilters="sRGB"
        >
          <feColorMatrix
            in="SourceGraphic"
            type="matrix"
            values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -10 4 6 0 -1"
            result="blueChroma"
          />
          <feColorMatrix
            in="SourceGraphic"
            type="matrix"
            values="0.060 0.202 0.020 0 0  0.155 0.522 0.053 0 0  0.127 0.426 0.043 0 0  0 0 0 1 0"
            result="pineColour"
          />
          <feComposite
            in="pineColour"
            in2="blueChroma"
            operator="in"
            result="pineIrises"
          />
          <feComposite
            in="SourceGraphic"
            in2="blueChroma"
            operator="out"
            result="unchanged"
          />
          <feComposite
            in="unchanged"
            in2="pineIrises"
            operator="arithmetic"
            k1="0"
            k2="1"
            k3="1"
            k4="0"
          />
        </filter>
      </defs>
    </svg>
  );
}
