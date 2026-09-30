import { useEffect, useRef } from "react";
import { createOwlSurface } from "../components/owlSurface";
import { OwlEyeMaterial } from "./OwlEyeMaterial";

/** Reuses the approved connected-neck renderer without the live auth provider. */
export function PreviewOwl() {
  const ref = useRef<HTMLDivElement>(null),
    canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const element = ref.current!,
      layer = canvas.current!;
    const motion = matchMedia("(prefers-reduced-motion: reduce)"),
      fine = matchMedia("(pointer: fine)");
    if (motion.matches || !fine.matches) return;
    const abort = new AbortController();
    let disposed = false,
      frame = 0,
      previous = 0;
    let yaw = 0,
      pitch = 0,
      targetYaw = 0,
      targetPitch = 0;
    let surface: Awaited<ReturnType<typeof createOwlSurface>> | null = null;
    const tick = (time: number) => {
      frame = 0;
      if (!surface || disposed || document.hidden || motion.matches) return;
      const dt = previous ? Math.min(0.05, (time - previous) / 1000) : 1 / 60;
      previous = time;
      const smoothing = -Math.expm1(-dt * 13);
      yaw += (targetYaw - yaw) * smoothing;
      pitch += (targetPitch - pitch) * smoothing;
      surface.draw(yaw, pitch);
      element.dataset.renderer = "approved-connected-neck";
      element.dataset.yaw = yaw.toFixed(3);
      element.dataset.pitch = pitch.toFixed(3);
      element.classList.add("is-ready");
      if (Math.abs(yaw - targetYaw) + Math.abs(pitch - targetPitch) > 0.001)
        frame = requestAnimationFrame(tick);
    };
    const wake = () => {
      if (!frame && surface && !motion.matches)
        frame = requestAnimationFrame(tick);
    };
    const pointer = (event: PointerEvent) => {
      const bounds = element.getBoundingClientRect();
      let x =
          (event.clientX - bounds.left - bounds.width * 0.428) /
          Math.max(innerWidth * 0.55, 280),
        y =
          (bounds.top + bounds.height * 0.192 - event.clientY) /
          Math.max(innerHeight * 0.6, 180);
      const length = Math.hypot(x, y);
      if (length > 1) {
        x /= length;
        y /= length;
      }
      targetYaw = x * 30;
      targetPitch = y * 18;
      element.dataset.targetYaw = targetYaw.toFixed(3);
      element.dataset.targetPitch = targetPitch.toFixed(3);
      wake();
    };
    const leave = () => {
      targetYaw = 0;
      targetPitch = 0;
      wake();
    };
    const changed = () => {
      if (motion.matches) {
        cancelAnimationFrame(frame);
        frame = 0;
        element.classList.remove("is-ready");
      } else wake();
    };
    void createOwlSurface(layer, abort.signal)
      .then((value) => {
        if (disposed) {
          value.dispose();
          return;
        }
        surface = value;
        wake();
      })
      .catch(() => {
        element.dataset.renderer = "approved-poster-fallback";
      });
    window.addEventListener("pointermove", pointer, { passive: true });
    document.addEventListener("pointerleave", leave);
    motion.addEventListener("change", changed);
    return () => {
      disposed = true;
      abort.abort();
      cancelAnimationFrame(frame);
      surface?.dispose();
      window.removeEventListener("pointermove", pointer);
      document.removeEventListener("pointerleave", leave);
      motion.removeEventListener("change", changed);
    };
  }, []);
  return (
    <div
      className="sf-owl"
      ref={ref}
      aria-hidden="true"
      data-eye-colour="pine-green"
      data-pointer-scope="page"
    >
      <OwlEyeMaterial />
      <img
        src="/assets/owl-poster-420.webp"
        alt=""
        width={1163}
        height={1353}
      />
      <canvas ref={canvas} width={336} height={391} />
    </div>
  );
}
