import { useEffect, useRef, useState } from "react";
import { Button, Modal, Notice } from "./primitives";

export async function readAvatar(file: File): Promise<ImageBitmap> {
  if (file.size > 2 * 1024 * 1024)
    throw new Error("Choose an image smaller than 2MiB.");
  const bytes = new Uint8Array(await file.slice(0, 16).arrayBuffer());
  const png =
    bytes[0] === 137 && bytes[1] === 80 && bytes[2] === 78 && bytes[3] === 71;
  const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  const webp =
    String.fromCharCode(...bytes.slice(0, 4)) === "RIFF" &&
    String.fromCharCode(...bytes.slice(8, 12)) === "WEBP";
  if (
    !(png || jpeg || webp) ||
    !["image/png", "image/jpeg", "image/webp"].includes(file.type)
  )
    throw new Error("Choose a PNG, JPEG or WebP image.");
  const image = await createImageBitmap(file);
  if (
    Math.min(image.width, image.height) < 64 ||
    Math.max(image.width, image.height) > 4096
  ) {
    image.close();
    throw new Error("Choose an image between64 and4096 pixels on each side.");
  }
  return image;
}
export function AvatarCrop({
  image,
  onClose,
  onSave,
}: {
  image: ImageBitmap;
  onClose: () => void;
  onSave: (url: string) => void;
}) {
  const [zoom, setZoom] = useState(1),
    [error, setError] = useState("");
  const canvas = useRef<HTMLCanvasElement>(null),
    active = useRef(true);
  useEffect(
    () => () => {
      active.current = false;
      image.close();
    },
    [image],
  );
  useEffect(() => {
    const ctx = canvas.current!.getContext("2d")!,
      size = Math.min(image.width, image.height) / zoom;
    ctx.clearRect(0, 0, 512, 512);
    ctx.drawImage(
      image,
      (image.width - size) / 2,
      (image.height - size) / 2,
      size,
      size,
      0,
      0,
      512,
      512,
    );
  }, [image, zoom]);
  return (
    <Modal title="Choose your crop" onClose={onClose}>
      <p>
        Keep your face or chosen image centred. This photo stays in the local
        preview.
      </p>
      <canvas
        className="sf-avatar-crop"
        ref={canvas}
        width={512}
        height={512}
        role="img"
        aria-label="Square avatar crop preview"
      />
      <label className="sf-field">
        <span>Zoom</span>
        <input
          type="range"
          min={1}
          max={3}
          step={0.05}
          value={zoom}
          onChange={(e) => setZoom(Number(e.target.value))}
        />
      </label>
      <div className="sf-dialog-actions">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          onClick={() =>
            canvas.current!.toBlob(
              (blob) => {
                if (!active.current) return;
                if (!blob) {
                  setError("The crop could not be saved. Try another image.");
                  return;
                }
                onSave(URL.createObjectURL(blob));
                onClose();
              },
              "image/webp",
              0.88,
            )
          }
        >
          Use photo
        </Button>
      </div>
      {error && <Notice danger>{error}</Notice>}
    </Modal>
  );
}
