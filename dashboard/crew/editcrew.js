// 편집팀 대시보드 가운데 화면: 로봇 편집 스튜디오(단계별 8초 반복 모션 그래픽).
// mountEditCrew(canvas, { stage, image, onCaption }) -> { player, setStage(id, label), setImage(img), setCount(name, value), pushLog(text, kind), showCard(o), clearLog(), destroy }
// 같은 t면 같은 그림(되감기·캡처·영상 렌더 가능). 단계가 바뀌면 0.45초 동안 어둡게 넘긴다.
import { createPlayer, clamp, FONT_BODY, FONT_DISPLAY } from './core.js';
import { GOLD, GOLD_RGB, PAPER, GRAY, plate, label } from './crew.js';
import { VW, VH, F, drawBackdrop, drawSign, drawBoard, drawMonitor, drawChair, drawFilmStrip } from './editcrew_set.js';
import { L, captionAt, SYNC, ASR, STUMBLE, TIGHTEN } from './editcrew_scenes1.js';
import { CONTENT, ZOOM, RENDER, RESTRUCTURE } from './editcrew_scenes2.js';
import { CHECKPOINT, FINAL, META, REPORT, UPLOAD, IDLE, DONE } from './editcrew_scenes3.js';
import { drawLog, drawCard } from './editcrew_live.js';

const ZOOM_FLOOR = 1.25;
export const SCENES = [SYNC, ASR, STUMBLE, TIGHTEN, CONTENT, ZOOM, RENDER, RESTRUCTURE, CHECKPOINT, FINAL, META, REPORT, UPLOAD, IDLE, DONE];
const BY = Object.fromEntries(SCENES.map((s) => [s.id, s]));
// 대시보드 단계 이름 -> 장면(쇼츠·썸네일 파트는 비슷한 일을 하는 장면을 빌려 쓴다)
export const STAGE_SCENE = {
  sync: 'sync', asr: 'asr', stumble: 'stumble', tighten: 'tighten', content: 'content', zoom_pip_blur: 'zoom',
  rough_render: 'render', restructure: 'restructure', checkpoint: 'checkpoint', final: 'final', meta: 'meta', report: 'report', upload: 'upload',
  sh_source: 'asr', sh_plan: 'content', sh_pick: 'checkpoint', sh_crop: 'zoom', sh_render: 'render', sh_verify: 'report', sh_report: 'report',
  th_source: 'stumble', th_copy: 'meta', th_render: 'final', th_check: 'report',
};

function drawFrame(ctx, t, sc, st) {
  const S = { lap: st.lap, img: st.img };
  drawBackdrop(ctx);
  const [bn, bv] = st.count || sc.board(t, S);
  drawBoard(ctx, t, bn, bv);
  drawSign(ctx, t, st.no || sc.no, st.tag || sc.tag, st.ko || sc.ko);
  drawMonitor(ctx, t, (c, r) => sc.screen(c, r, t, S), sc.photo === false ? null : st.img, sc.onAir === undefined ? 1 : sc.onAir);
  // 바닥 무대(로봇·소품)는 바닥선을 기준으로 1.25배 — 로봇 표정이 읽히게
  ctx.save();
  ctx.translate(480, F);
  ctx.scale(ZOOM_FLOOR, ZOOM_FLOOR);
  ctx.translate(-480, -F);
  if (!sc.noChair) drawChair(ctx);
  sc.draw(ctx, t, S);
  ctx.restore();
  // 아래 문구(바닥과 필름 띠 사이)
  const c = captionAt(sc.caps, t);
  ctx.font = `800 10px ui-monospace, monospace`;
  const tw = ctx.measureText(c.tag).width + 16;
  plate(ctx, 40, 462, tw, 22, 4, `rgba(${GOLD_RGB},0.14)`, `rgba(${GOLD_RGB},0.6)`, 1);
  label(ctx, c.tag, 48, 473.5, { size: 10, weight: 800, color: GOLD, tracking: 0.16 });
  label(ctx, c.text, 40 + tw + 12, 473.5, { size: 14, weight: 600, family: FONT_BODY, color: PAPER });
  drawFilmStrip(ctx, t, sc.film || 18);
  return c;
}

export function mountEditCrew(canvas, { stage = 'idle', image = null, onCaption, autoplay = true } = {}) {
  const st = { id: BY[stage] ? stage : 'idle', prev: null, switchAt: -9, t0: 0, img: image, lap: 0, count: null, tag: null, ko: null, no: null, logs: [], card: null };
  let lastCap = null;
  const player = createPlayer(canvas, {
    autoplay,
    draw(ctx, tRaw, view) {
      const k = Math.min(view.w / VW, view.h / VH);
      ctx.fillStyle = '#050505';
      ctx.fillRect(0, 0, view.w, view.h);
      ctx.save();
      ctx.translate((view.w - VW * k) / 2, (view.h - VH * k) / 2);
      ctx.scale(k, k);
      ctx.beginPath();
      ctx.rect(0, 0, VW, VH);
      ctx.clip();
      const tr = Math.max(0, tRaw - st.t0);
      st.lap = Math.floor(tr / L);
      const t = tr - st.lap * L;
      const sc = BY[st.id];
      const c = drawFrame(ctx, t, sc, st);
      drawCard(ctx, tRaw, st.card);
      drawLog(ctx, tRaw, st.logs);
      // 단계가 바뀐 직후: 검게 덮였다가 열린다
      const since = tRaw - st.switchAt;
      if (since >= 0 && since < 0.45) {
        ctx.fillStyle = `rgba(5,5,5,${1 - clamp(since / 0.45)})`;
        ctx.fillRect(0, 0, VW, VH);
      }
      ctx.restore();
      if (onCaption && c !== lastCap) {
        lastCap = c;
        onCaption(c, sc);
      }
    },
  });
  return {
    player,
    setStage(id, o = {}) {
      const sid = STAGE_SCENE[id] || (BY[id] ? id : null);
      if (!sid) return;
      st.tag = o.tag || null;
      st.ko = o.ko || null;
      st.no = o.no || null;
      if (sid === st.id) return;
      st.id = sid;
      st.switchAt = player.time;
      st.t0 = player.time;
      st.count = null;
    },
    setImage(img) {
      st.img = img;
    },
    /** 실행기 기록 한 줄(코드처럼 타자로 올라온다). kind: info|warn|cut|ok */
    pushLog(text, kind = 'info', instant = false) {
      if (!text) return;
      const last = st.logs[st.logs.length - 1];
      // 앞 줄이 다 쳐진 뒤에(단, 밀린 줄이 3초 넘게 쌓이면 바로) · instant = 지난 기록 다시 읽기(이미 쳐진 상태)
      let t0 = instant ? player.time - 30 : Math.max(player.time, last ? last.t0 + Math.min(1.2, last.text.length / 48 + 0.15) : 0);
      if (t0 > player.time + 3) t0 = player.time;
      st.logs.push({ text: String(text), kind, t0 });
      if (st.logs.length > 40) st.logs.splice(0, st.logs.length - 40);
    },
    clearLog() {
      st.logs = [];
      st.card = null;
    },
    /** 이벤트 카드 { k, title, meta, img(Image), cut } */
    showCard(o) {
      st.card = Object.assign({ t0: player.time }, o);
    },
    setCount(name, value) {
      st.count = name ? [name, value] : null;
    },
    get stage() {
      return st.id;
    },
    destroy() {
      player.destroy();
    },
  };
}
