/** Iris-only material: 12% less chroma, same luminance/mask and approved assets. */
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
            values="0.068734 0.231404 0.023031 0 0  0.152334 0.513004 0.052071 0 0  0.127694 0.428524 0.043271 0 0  0 0 0 1 0"
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
