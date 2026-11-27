// 홈 히어로 모션 시안 3종이 함께 쓰는 작은 도구 모음.
// 외부 라이브러리 없이(GSAP·Three.js 없음) Canvas 2D만 쓴다 — 번들이 가볍고 의존성이 없다.
// 원칙: 화면은 "시간 t의 순수 함수"로 그린다(같은 t면 항상 같은 그림) → 되감기·정지 화면·캡처가 쉽다.

export const TAU = Math.PI * 2;

export const BRAND = {
  black: '#000000',
  gold: '#f39c12',
  white: '#ffffff',
  gray: '#8c8c8c',
  muted: '#4e4e4e',
};

export const FONT_DISPLAY =
  "'Outfit', 'Inter', 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif";
export const FONT_BODY =
  "'Inter', 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', sans-serif";
export const FONT_MONO =
  "ui-monospace, 'SFMono-Regular', 'Cascadia Mono', 'Consolas', 'Menlo', monospace";

export const font = (weight, size, family = FONT_DISPLAY) => `${weight} ${size}px ${family}`;

export const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const lerp = (a, b, t) => a + (b - a) * t;
/** t가 a→b 구간을 지나는 동안 0→1 */
export const seg = (t, a, b) => clamp((t - a) / (b - a));
export const fract = (x) => x - Math.floor(x);
/** 정수 n에 대해 항상 같은 0~1 값 (난수 대신 쓰는 고정 해시) */
export const hash = (n) => fract(Math.sin(n * 127.1 + 311.7) * 43758.5453123);

export const ease = {
  linear: (x) => x,
  inCubic: (x) => x * x * x,
  outCubic: (x) => 1 - (1 - x) ** 3,
  inOutCubic: (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2),
  outQuart: (x) => 1 - (1 - x) ** 4,
  inQuart: (x) => x ** 4,
  inOutQuart: (x) => (x < 0.5 ? 8 * x ** 4 : 1 - (-2 * x + 2) ** 4 / 2),
  outExpo: (x) => (x >= 1 ? 1 : 1 - 2 ** (-10 * x)),
  inOutSine: (x) => -(Math.cos(Math.PI * x) - 1) / 2,
};

/**
 * 스프링의 계단 응답(0 → 1)을 식으로 바로 계산한다. t = 출발 후 지난 시간(초).
 * 프레임마다 상태를 쌓지 않으므로 어느 시점으로 건너뛰어도 같은 값이 나온다.
 * damp 1 이상이면 넘침(overshoot) 없이 붙는다.
 */
export function spring(t, freq = 2.6, damp = 0.86) {
  if (t <= 0) return 0;
  const w = TAU * freq;
  if (damp >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - damp * damp);
  return 1 - Math.exp(-damp * w * t) * (Math.cos(wd * t) + ((damp * w) / wd) * Math.sin(wd * t));
}

/**
 * 목표값이 여러 번 바뀌는 값 = 변화 하나마다 스프링 하나를 더한 합.
 * keys: [[시각, 값], ...] (시각 오름차순). 첫 값에서 출발한다.
 */
export function springTrack(keys, freq = 2.6, damp = 0.86) {
  return (t) => {
    let v = keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const dt = t - keys[i][0];
      if (dt <= 0) break;
      v += (keys[i][1] - keys[i - 1][1]) * spring(dt, freq, damp);
    }
    return v;
  };
}

/** 고정 씨앗 난수 (매번 같은 순서) */
export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** 0..n-1을 고정 씨앗으로 섞은 배열 */
export function shuffled(n, seed) {
  const rnd = mulberry32(seed);
  const arr = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    const tmp = arr[i];
    arr[i] = arr[j];
    arr[j] = tmp;
  }
  return arr;
}

/** 둥근 사각형 경로 (구형 브라우저에도 되도록 직접 그림) */
export function roundRectPath(ctx, x, y, w, h, r) {
  const rr = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.lineTo(x + w - rr, y);
  ctx.arcTo(x + w, y, x + w, y + rr, rr);
  ctx.lineTo(x + w, y + h - rr);
  ctx.arcTo(x + w, y + h, x + w - rr, y + h, rr);
  ctx.lineTo(x + rr, y + h);
  ctx.arcTo(x, y + h, x, y + h - rr, rr);
  ctx.lineTo(x, y + rr);
  ctx.arcTo(x, y, x + rr, y, rr);
  ctx.closePath();
}

/** 글자 폭 측정 캐시 (글꼴이 늦게 도착하면 비운다) */
export function createTextMeasurer(ctx) {
  const cache = new Map();
  return {
    width(text, fontSpec) {
      const key = fontSpec + '|' + text;
      let v = cache.get(key);
      if (v === undefined) {
        ctx.font = fontSpec;
        v = ctx.measureText(text).width;
        cache.set(key, v);
      }
      return v;
    },
    /** 글자마다의 시작 x (커닝 반영) — 100px 기준으로 재서 비율로 쓴다 */
    advances(text, weight, family) {
      const key = 'adv|' + weight + '|' + family + '|' + text;
      let v = cache.get(key);
      if (v === undefined) {
        ctx.font = font(weight, 100, family);
        const chars = Array.from(text);
        const xs = [];
        let prefix = '';
        for (let i = 0; i < chars.length; i++) {
          xs.push(ctx.measureText(prefix).width / 100);
          prefix += chars[i];
        }
        v = { chars, xs, total: ctx.measureText(prefix).width / 100 };
        cache.set(key, v);
      }
      return v;
    },
    clear() {
      cache.clear();
    },
  };
}

/**
 * 재생기: 캔버스 크기(레티나 포함)·재생/정지·화면 밖/탭 숨김 시 멈춤을 맡는다.
 * draw(ctx, t, view)는 시간 t의 화면을 그리는 함수.
 */
export function createPlayer(canvas, { draw, onTime, autoplay = true, maxDpr = 2, loopAt = 0, startAt = 0 } = {}) {
  const ctx = canvas.getContext('2d');
  const view = { w: 0, h: 0, dpr: 1 };
  // 기기에서 '동작 줄이기'를 켰는가. 자동 재생은 이 설정과 상관없이 한다
  // (2026-10-05: 접속하면 처음엔 자동으로 재생되어야 한다 — 이 설정이 켜진 휴대폰이 적지 않다).
  // 이 값은 "필름이 끝난 뒤에는 멈춘다", "멈춤 버튼을 보여 준다" 같은 배려 동작에만 쓴다.
  const reduced =
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false;
  let time = startAt;
  let playing = false;
  let raf = 0;
  let last = 0;
  let inView = true;
  let destroyed = false;
  let rate = 1;
  let loop = loopAt;

  function measure() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    if (w !== view.w || h !== view.h || dpr !== view.dpr) {
      view.w = w;
      view.h = h;
      view.dpr = dpr;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
    }
  }

  function render() {
    if (destroyed) return;
    if (!view.w) measure();
    ctx.setTransform(view.dpr, 0, 0, view.dpr, 0, 0);
    draw(ctx, time, view);
    if (onTime) onTime(time);
  }

  const running = () => playing && inView && !document.hidden && !destroyed;

  function tick(now) {
    raf = 0;
    if (!running()) return;
    // 느린 기기에서도 실제 시간대로 흐르게 하되, 오래 멈췄다 돌아올 때 한꺼번에 건너뛰지는 않게 0.25초로 제한
    const dt = Math.min(0.25, Math.max(0, (now - last) / 1000));
    last = now;
    time += dt * rate;
    if (loop > 0 && time >= loop) time %= loop;
    render();
    raf = requestAnimationFrame(tick);
  }

  function kick() {
    if (raf || !running()) return;
    last = performance.now();
    raf = requestAnimationFrame(tick);
  }

  const onVis = () => kick();
  document.addEventListener('visibilitychange', onVis);

  let ro = null;
  if (typeof ResizeObserver !== 'undefined') {
    ro = new ResizeObserver(() => {
      measure();
      render();
    });
    ro.observe(canvas);
  }
  let io = null;
  if (typeof IntersectionObserver !== 'undefined') {
    io = new IntersectionObserver(
      (entries) => {
        inView = entries[0].isIntersecting;
        kick();
      },
      { threshold: 0.01 }
    );
    io.observe(canvas);
  }

  measure();
  render();
  if (autoplay) {
    playing = true;
    kick();
  }

  return {
    ctx,
    view,
    reduced,
    render,
    play() {
      playing = true;
      kick();
    },
    pause() {
      playing = false;
    },
    seek(t) {
      time = t;
      render();
    },
    get time() {
      return time;
    },
    get playing() {
      return playing;
    },
    setRate(v) {
      rate = v;
    },
    setLoop(v) {
      loop = v;
    },
    destroy() {
      destroyed = true;
      playing = false;
      if (raf) cancelAnimationFrame(raf);
      document.removeEventListener('visibilitychange', onVis);
      if (ro) ro.disconnect();
      if (io) io.disconnect();
    },
  };
}

/** 캔버스 글자에 쓸 웹폰트가 도착하면 알려준다(도착 전에는 시스템 글꼴로 그려진다) */
export function whenFontsReady(specs, cb) {
  if (typeof document === 'undefined' || !document.fonts || !document.fonts.load) return;
  let cancelled = false;
  Promise.all(specs.map((s) => document.fonts.load(s).catch(() => null))).then(() => {
    if (!cancelled) cb();
  });
  return () => {
    cancelled = true;
  };
}
