/* ══════════════════════════════════════════════════════════════════════════
   model.js — the reusable-model contract for every Bonk motion piece.

   A piece declares ONE block: what it is called, what frame it is composed for,
   the copy it draws, the colours it exposes, and the numeric dials it has.
   This file turns that block into a uniform, overridable, measurable surface.

   WHAT YOU GET, IDENTICALLY, FROM EVERY PIECE (the capture contract):

     window.__model        the resolved model + the full param schema (JSON)
     window.__params()     [{name,group,type,default,value,doc}] — the dials
     window.__set(patch)   {label:'…','--mark':'…',markW:0.8} → apply + repaint
     window.__duration     seconds
     window.__frame        {w,h,fps}
     window.__seek(sec)    drive to an exact time (cancels the rAF loop first)
     window.__rebuild()    re-read CSS + config, then repaint the last frame
     window.__theme()      current value of every colour token
     window.__warnings[]   everything that looked wrong, in writing
     window.__ready        Promise — resolves once fonts are in and frame 0 is up

   OVERRIDE FROM OUTSIDE — a URL, no code edit, no rebuild:

     ?label=…&sub=…            every key under `text`    (copy)
     ?mark=%2300ff85           every token in `colours`  (colour)
     ?markW=0.80               every key under `dials`   (numbers)
     ?scale=1.15&tracking=0.14 keys under `type`         (type size)
     ?w=1080&h=1080            the frame                 (size)
     ?dur=6&fps=30             timing
     ?ground=light             the light register
     ?chrome=0                 strip the on-page chrome (GOTCHAS §6.3)

   Rules this file exists to enforce, each one paid for in GOTCHAS:
     §8.5  a theme hook that re-reads without repainting renders stale
           → every mutation path ends in a repaint, never just a read
     §8.16 flip EVERY token, or the theme test lies
           → `colours` is the complete surface; __theme() enumerates all of it
     §2.5  pick one time unit and stick to it
           → __seek is SECONDS, __duration is SECONDS. Nothing else, ever.
     §2.4  cancel the rAF loop before seeking
           → __seek does it for you
     §2.1  a capture can exit 0 and write a blank GIF
           → every failure here lands in __warnings, and render.py fails on it

   USAGE, at the top of a piece:

     const MODEL = MotionModel.define({
       id:'glow', title:'bonk — glow', family:'motion-assets',
       purpose:'the logo as a window — a soft light drifts through the mark',
       frame:{w:1920,h:1080}, duration:10, fps:30,
       colours:['--ground','--mark','--light','--label','--label-dim','--accent'],
       text:{ label:'bonk', sub:'music library', kicker:'in order' },
       type:{ size:0.0175, scale:1, tracking:0.10 },
       dials:{ markW:0.735, markDim:0.115, lightPeak:0.98 },
     });

     MODEL.onApply(() => { readTheme(); });   // re-read the theme …
     MODEL.renderAt(t => draw(t));            // … and the kit repaints for you

   Name the binding MODEL, not M. Several pieces already use `M` for the brand
   MARK (`const {M,s,gw,gh} = markGeo()`), so an M for the model is shadowed
   inside draw() and reads as the mark. That collision cost one debug pass.
   ══════════════════════════════════════════════════════════════════════════ */
(function (global) {
'use strict';

var RESERVED = ['w','h','dur','duration','fps','ground','chrome','scene','text'];

/* URL params are flat and lowercase-tolerant: ?--mark= and ?mark= are the same
   dial. Strip the prefix so one name works in a URL, in a shell and in JSON. */
function bare(name){ return String(name).replace(/^--/, ''); }

function isNumeric(v){ return typeof v === 'number' && isFinite(v); }

/* A colour is anything we can hand to CSS. Normalise so `?accent=ff6b1a`,
   `?accent=%23ff6b1a` and `?accent=#ff6b1a` all mean the same thing. */
function normalizeColour(v){
  var s = String(v).trim();
  if (!s) return s;
  if (/^(#|rgb|hsl|oklch|color\(|[a-z]+$)/i.test(s)) return s;
  if (/^[0-9a-f]{3,8}$/i.test(s)) return '#' + s;
  return s;
}

/* Chrome does substitute var() inside custom properties, but that is an
   implementation detail of a browser I do not control. Resolve it myself so
   tokens.css can compose (--ground: var(--brand-black)) without the value
   silently arriving as the literal string "var(--brand-black)". */
function resolveVar(value, seen){
  seen = seen || {};
  var m = /^var\(\s*(--[\w-]+)\s*(?:,\s*(.*))?\)$/.exec(String(value).trim());
  if (!m) return value;
  var name = m[1], fallback = m[2];
  if (seen[name]) return fallback || '';
  seen[name] = 1;
  var raw = global.getComputedStyle(document.documentElement)
                  .getPropertyValue(name).trim();
  if (!raw) return fallback !== undefined ? resolveVar(fallback, seen) : '';
  return resolveVar(raw, seen);
}

/* ── schema construction ───────────────────────────────────────────────────
   The spec IS the schema. Every declared key becomes an addressable param, so
   the registry, the CLI and the Obsidian KB are all generated from the same
   list the piece actually uses — there is no second place to drift. */
function buildSchema(spec){
  var out = [];

  (spec.colours || []).forEach(function (tok){
    out.push({ name:tok, group:'colour', type:'colour', token:tok,
               doc:'CSS custom property ' + tok + ' — ?' + tok + '= or ?' +
                   bare(tok) + '= (the bare form unless a copy key claims it)' });
  });

  Object.keys(spec.text || {}).forEach(function (k){
    if (RESERVED.indexOf(k) >= 0) soft('text key "'+k+'" is reserved and was ignored');
    out.push({ name:k, group:'copy', type:'text', default:spec.text[k],
               doc:'copy drawn by the piece' });
  });

  out.push({ name:'w', group:'frame', type:'number', default:(spec.frame||{}).w || 1920,
             doc:'frame width in px' });
  out.push({ name:'h', group:'frame', type:'number', default:(spec.frame||{}).h || 1080,
             doc:'frame height in px' });
  out.push({ name:'dur', group:'timing', type:'number', default:spec.duration || 8,
             doc:'seconds the piece runs. __seek is SECONDS, always' });
  out.push({ name:'fps', group:'timing', type:'number', default:spec.fps || 30,
             doc:'frames per second the piece is composed for' });

  Object.keys(spec.type || {}).forEach(function (k){
    if (k === 'family') return;
    out.push({ name:k, group:'type', type:'number', default:spec.type[k],
               doc:k === 'scale' ? 'ONE multiplier over every type size the piece draws'
                 : k === 'tracking' ? 'inter-letter gap as an em fraction'
                 : k === 'size' ? 'base type size as a fraction of the frame'
                 : 'type dial' });
  });

  Object.keys(spec.dials || {}).forEach(function (k){
    out.push({ name:k, group:'dial', type:'number', default:spec.dials[k],
               doc:spec.dialDocs && spec.dialDocs[k] || 'tuning dial' });
  });

  return out;
}

var warnings = [];
function soft(msg){ warnings.push(String(msg)); }
global.__warnings = warnings;

/* ── the model ───────────────────────────────────────────────────────────── */
function define(spec){
  spec = spec || {};
  if (!spec.id) throw new Error('MotionModel.define: `id` is required');

  var Q = new URLSearchParams(location.search);
  var els = document.documentElement;

  /* ground first: it changes every other colour token, so it has to be set
     before anything is read (motion-assets convention, kept) */
  if (Q.get('ground') === 'light') els.dataset.ground = 'light';
  if (Q.get('chrome') === '0')     els.dataset.chrome = 'off';

  var schema = buildSchema(spec);
  var byName = {};
  schema.forEach(function (p){ byName[p.name] = p; });

  /* ── one namespace, two kinds of thing ───────────────────────────────────
     A colour token and a copy key can want the same short name: `label` is
     both a very common CSS token and a very common thing to write on screen.
     One flat namespace silently overwrites one with the other, which is a bug
     you find three files later in a render, not here. So they are separated:

       --mark    the colour token, ALWAYS addressable with its dashes
       mark      the same token as a shorthand, but ONLY while no copy key
                 claims the bare name
       label     the copy key, when a piece has one

     Copy wins the bare name; the colour keeps its dashes. Deterministic, and
     ?mark=%2300ff85 still works for every piece without a clash. */
  var colourAlias = {};
  schema.forEach(function (p){
    if (p.group !== 'colour') return;
    var b = bare(p.name);
    if (byName[b]) { p.alias = null; }            // taken — the dashes are required
    else { colourAlias[b] = p.name; p.alias = b; }
  });

  function lookup(rawName){
    if (rawName.slice(0, 2) === '--') return byName[rawName] || null;
    return byName[rawName] || byName[colourAlias[rawName]] || null;
  }

  var params = {};                    // resolved, keyed by CANONICAL name
  schema.forEach(function (p){ params[p.name] = p.default; });
  var currentTheme = {};              // the live palette, kept in step by readColours

  var subscribers = [];                  // onApply
  var renderer    = null;                // renderAt
  var lastT       = 0;
  var sceneList   = null;

  /* colour defaults come from CSS, not from the spec — the stylesheet is the
     source of truth and the spec only says WHICH tokens are part of the surface */
  function readColours(){
    var cs = global.getComputedStyle(els);
    var theme = {};
    (spec.colours || []).forEach(function (tok){
      var v = resolveVar(cs.getPropertyValue(tok).trim());
      if (!v){
        soft('colour token ' + tok + ' resolves to nothing — is it defined in CSS?');
        v = 'transparent';
      }
      theme[tok] = v;
      if (!overridden[tok]){
        params[tok] = v;
        var a = bare(tok);
        /* the shorthand only mirrors the token while no copy key owns the
           bare name — otherwise it would overwrite the piece's copy */
        if (!byName[a] || byName[a].group === 'colour') params[a] = v;
      }
    });
    currentTheme = theme;             // __theme() must never report a stale palette
    return theme;
  }

  var overridden = {};

  /* ── apply a patch ───────────────────────────────────────────────────────
     One door for every mutation — URL, __set(), or the CLI — so an override
     can never partially apply, and every path ends in the same repaint. */
  function apply(patch, opts){
    patch = patch || {};
    var repaint = !opts || opts.repaint !== false;

    Object.keys(patch).forEach(function (rawName){
      var name = bare(rawName);
      var p = lookup(rawName);
      /* reserved names are read by the piece itself (?ground, ?scene, …) and
         must pass through without an "unknown param" warning */
      if (!p){ if (RESERVED.indexOf(name) < 0) soft('unknown param "' + rawName + '" was ignored'); return; }
      var val = patch[rawName];

      if (p.type === 'colour'){
        val = normalizeColour(val);
        els.style.setProperty(p.token, val);      // inline beats both stylesheets
      } else if (p.type === 'number'){
        var n = parseFloat(val);
        if (!isFinite(n)){ soft('param "' + name + '" got a non-number: ' + val); return; }
        val = n;
      } else {
        val = String(val);
      }

      params[p.name] = val;
      overridden[p.name] = 1;
      if (p.group === 'colour' && p.alias) params[p.alias] = val;

      /* the numbers a piece draws with must ALSO land back in CSS, or the piece
         reads its old :root value and the dial silently does nothing. Same for
         timing — every piece reads --duration through its own cssv(). */
      if (p.type === 'number'){
        var cssName = name === 'dur' ? '--duration' : '--' + name;
        els.style.setProperty(cssName, String(val));
      }
    });

    readColours();

    /* frame: drive the stage if the piece is inside an .mf-stage and the
       caller asked for a specific size — otherwise the viewport IS the frame */
    var fw = params.w, fh = params.h;
    if (isNumeric(fw) && isNumeric(fh)){
      els.style.setProperty('--frame-w', String(fw));
      els.style.setProperty('--frame-h', String(fh));
    }

    if (repaint) repaintNow();
  }

  function repaintNow(){
    var cfg = resolved();
    subscribers.forEach(function (fn){
      try { fn(cfg); } catch (e){ soft('onApply threw: ' + (e && e.message)); }
    });
    if (renderer){
      try { renderer(cfg.t, cfg); }
      catch (e){ soft('renderAt threw at t=' + cfg.t + ': ' + (e && e.message)); }
    }
  }

  function resolved(){
    return {
      t:         lastT,
      params:    params,
      theme:     currentTheme,
      duration:  params.dur,
      fps:       params.fps,
      frame:     { w: params.w, h: params.h },
      text:      textMap(),
      type:      typeMap(),
      dials:     dialsMap()
    };
  }

  function textMap(){
    var o = {}; Object.keys(spec.text || {}).forEach(function (k){ o[k] = params[k]; }); return o;
  }
  function typeMap(){
    var o = {}; Object.keys(spec.type || {}).forEach(function (k){ o[k] = params[k]; }); return o;
  }
  function dialsMap(){
    var o = {}; Object.keys(spec.dials || {}).forEach(function (k){ o[k] = params[k]; }); return o;
  }

  /* ── 1. URL overrides ────────────────────────────────────────────────────
     Applied before anything else so frame 0 is already the asked-for frame.
     No second render pass, no flash of the default composition. */
  var urlPatch = {};
  Q.forEach(function (value, key){
    var name = bare(key);
    if (lookup(name)) urlPatch[name] = value;    // alias-aware, not byName-only
  });
  apply(urlPatch, { repaint:false });

  /* ── 2. the public surface ───────────────────────────────────────────────── */
  var currentTheme = {};
  (function syncTheme(){ currentTheme = {}; (spec.colours||[]).forEach(function(t){
    /* CANONICAL name — params[t], never params[bare(t)]. `label` is a copy key
       in several pieces, and reading the bare name reported the on-screen word
       as the value of a colour token. */
    currentTheme[t] = params[t];
  }); })();

  global.__model = {
    id:       spec.id,
    title:    spec.title || spec.id,
    family:   spec.family || '',
    purpose:  spec.purpose || '',
    notes:    spec.notes || '',
    frame:    { w: params.w, h: params.h },
    duration: params.dur,
    fps:      params.fps,
    colours:  (spec.colours || []).slice(),
    text:     textMap(),
    type:     typeMap(),
    dials:    dialsMap(),
    params:   schema,
    overrides: function(){ return Object.keys(overridden); }
  };

  global.__params  = function(){ return schema.map(function (p){
    var c = {}; for (var k in p) c[k] = p[k]; c.value = params[p.name]; return c;
  }); };
  global.__theme   = function(){ return currentTheme; };
  global.__duration = params.dur;
  global.__frame   = { w: params.w, h: params.h, fps: params.fps };

  global.__set = function (patch){
    apply(patch, { repaint:true });
    global.__duration = params.dur;              // a duration change must land too
    global.__frame = { w: params.w, h: params.h, fps: params.fps };
    global.__model.duration = params.dur;
    global.__model.frame = { w: params.w, h: params.h };
    return resolved();
  };

  /* §8.5 — re-read AND repaint, in the same call. A hook that only re-reads
     reports the new value while rendering the old one; that is the exact bug
     this line prevents. */
  global.__rebuild     = function(){ apply({}, { repaint:true }); return currentTheme; };
  global.__applyTheme  = global.__rebuild;

  /* §2.4 — cancel the rAF loop, THEN seek. A live loop draws its own clock
     between the seek and the screenshot and the capture becomes a mix. */
  global.__seek = function (seconds){
    seconds = parseFloat(seconds);
    if (!isFinite(seconds)){ soft('__seek got a non-number: ' + seconds); return; }
    lastT = Math.max(0, Math.min(seconds, params.dur));
    if (global.__stopLoop) try { global.__stopLoop(); } catch (e){}
    repaintNow();
  };

  global.__scenes = function (){ return sceneList || []; };

  /* ── 3. ready ────────────────────────────────────────────────────────────
     A canvas ctx.font reference does NOT trigger an @font-face download
     (GOTCHAS §3.10). Wait for the faces the piece actually declares, then
     prove one of them painted a different number of pixels than the fallback —
     a font that 404s looks completely plausible otherwise. */
  global.__ready = (async function (){
    var faces = spec.fonts || [];
    if (!faces.length && document.fonts && document.fonts.size)
      document.fonts.forEach(function (f){ faces.push(f.family + ' ' + f.weight + ' 40px'); });
    try {
      await Promise.all(faces.map(function (f){
        return document.fonts.load(f).catch(function(){ soft('font failed to load: ' + f); });
      }));
      await document.fonts.ready;
    } catch (e){ soft('fonts.ready rejected: ' + (e && e.message)); }

    apply({}, { repaint:true });
    lastT = 0;
    repaintNow();

    if (!renderer) soft('no renderer registered — call MotionModel.renderAt(fn)');
    if (warnings.length) console.warn('__warnings', warnings);
    return true;
  })();

  /* ── 4. the piece's hooks ───────────────────────────────────────────────── */
  return {
    spec:   spec,
    params: params,

    onApply:  function (fn){ subscribers.push(fn); return this; },
    renderAt: function (fn){
      renderer = fn;
      /* rewire the public surface: the piece's own draw() is now the renderer,
         so __seek and every repaint go through exactly one function */
      global.__seek = function (seconds){
        seconds = parseFloat(seconds);
        if (!isFinite(seconds)){ soft('__seek got a non-number: ' + seconds); return; }
        lastT = Math.max(0, Math.min(seconds, params.dur));
        if (global.__stopLoop) try { global.__stopLoop(); } catch (e){}
        repaintNow();
      };
      return this;
    },
    /* the timings a reel actually resolved — export them so a verifier reads
       the real layout instead of re-deriving the same formula in a second
       place and testing nothing (GOTCHAS §8.8) */
    scenes:   function (list){ sceneList = list; return this; },
    warn:     soft,
    get cfg(){ return resolved(); }
  };
}

global.MotionModel = {
  define: define,
  version: '1.0.0',
  tokens: {
    number:   function (v, min, max, dflt){
      var n = parseFloat(v);
      if (!isFinite(n)) return dflt;
      if (min !== undefined && n < min) return min;
      if (max !== undefined && n > max) return max;
      return n;
    }
  }
};

})(window);
