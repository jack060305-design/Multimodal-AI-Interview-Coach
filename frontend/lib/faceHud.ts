export type ClientDeliveryMetrics = {
  eye_contact_percentage: number;
  eye_contact_score: number;
  frames_analyzed: number;
  face_present_rate: number;
  source: "browser";
};

type FaceDetectorLike = {
  detect: (source: HTMLVideoElement) => Promise<Array<{ boundingBox: DOMRectReadOnly }>>;
};

declare global {
  interface Window {
    FaceDetector?: new (options?: { fastMode?: boolean; maxDetectedFaces?: number }) => FaceDetectorLike;
  }
}

/** Browser-side eye-contact HUD — $0 server CV, runs during recording. */
export class FaceHudTracker {
  private running = false;
  private rafId = 0;
  private scores: number[] = [];
  private faceFrames = 0;
  private totalFrames = 0;
  private detector: FaceDetectorLike | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private onLiveUpdate: ((pct: number) => void) | null = null;

  async start(video: HTMLVideoElement, onLiveUpdate?: (pct: number) => void) {
    this.onLiveUpdate = onLiveUpdate ?? null;
    if (typeof window !== "undefined" && window.FaceDetector) {
      try {
        this.detector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
      } catch {
        this.detector = null;
      }
    }
    this.canvas = document.createElement("canvas");
    this.running = true;
    const loop = () => {
      if (!this.running) return;
      void this.tick(video);
      this.rafId = requestAnimationFrame(loop);
    };
    this.rafId = requestAnimationFrame(loop);
  }

  stop(): ClientDeliveryMetrics {
    this.running = false;
    cancelAnimationFrame(this.rafId);
    const pct = this.scores.length
      ? this.scores.reduce((a, b) => a + b, 0) / this.scores.length
      : 0;
    const faceRate = this.totalFrames ? (100 * this.faceFrames) / this.totalFrames : 0;
    return {
      eye_contact_percentage: Math.round(pct * 10) / 10,
      eye_contact_score: Math.round(pct),
      frames_analyzed: this.totalFrames,
      face_present_rate: Math.round(faceRate * 10) / 10,
      source: "browser",
    };
  }

  private async tick(video: HTMLVideoElement) {
    if (video.readyState < 2 || !video.videoWidth) return;
    this.totalFrames++;
    let score = 0;
    let hasFace = false;

    if (this.detector) {
      try {
        const faces = await this.detector.detect(video);
        if (faces?.length) {
          hasFace = true;
          const box = faces[0].boundingBox;
          const cx = box.x + box.width / 2;
          const cy = box.y + box.height / 2;
          const nx = cx / video.videoWidth;
          const ny = cy / video.videoHeight;
          const centerDist = Math.hypot(nx - 0.5, ny - 0.42);
          const sizeRatio = box.width / video.videoWidth;
          score = Math.max(0, 100 - centerDist * 220) * (sizeRatio > 0.1 ? 1 : 0.55);
        }
      } catch {
        // skip frame
      }
    } else {
      score = this.heuristicScore(video);
      hasFace = score > 25;
    }

    if (hasFace) this.faceFrames++;
    const clamped = Math.min(100, Math.max(0, score));
    this.scores.push(clamped);
    this.onLiveUpdate?.(clamped);
  }

  private heuristicScore(video: HTMLVideoElement): number {
    const canvas = this.canvas;
    if (!canvas) return 0;
    const w = 80;
    const h = 60;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return 0;
    ctx.drawImage(video, 0, 0, w, h);
    const { data } = ctx.getImageData(0, 0, w, h);
    let center = 0;
    let edges = 0;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        const lum = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        const inCenter = x > w * 0.25 && x < w * 0.75 && y > h * 0.2 && y < h * 0.8;
        if (inCenter) center += lum;
        else edges += lum;
      }
    }
    const contrast = center / (edges + 1);
    return Math.min(85, Math.max(0, (contrast - 0.85) * 120));
  }
}
